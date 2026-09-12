from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

from .models import LeadClassification

_SYSTEM_PROMPT = """You classify real-estate lead intent for downstream workflow routing.
Return JSON only with exactly these fields:
intent: buy|rent|sell|information|other
urgency: low|medium|high
needs_human: boolean
rationale: concise reason, maximum 300 characters
Do not add markdown or extra keys."""


@dataclass(slots=True)
class BedrockModelGateway:
    client: Any
    model_id: str

    def classify(self, message: str) -> LeadClassification:
        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": _SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": message}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 300},
        )
        try:
            text = response["output"]["message"]["content"][0]["text"]
            payload = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Bedrock response was not valid JSON matching the expected envelope"
            ) from exc
        return LeadClassification.model_validate(payload)


@dataclass(slots=True)
class SSMApiKeyProvider:
    client: Any
    parameter_name: str
    _cached: str | None = field(default=None, init=False, repr=False)

    def get(self) -> str:
        if self._cached is None:
            response = self.client.get_parameter(Name=self.parameter_name, WithDecryption=True)
            self._cached = str(response["Parameter"]["Value"])
        return self._cached


@dataclass(slots=True)
class DynamoRequestStore:
    table: Any
    ttl_seconds: int = 86_400

    def get_completed(self, request_id: str) -> LeadClassification | None:
        response = self.table.get_item(Key={"request_id": request_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item or item.get("status") != "COMPLETED" or "result" not in item:
            return None
        return LeadClassification.model_validate(item["result"])

    def claim(self, request_id: str) -> bool:
        now = int(time.time())
        try:
            self.table.put_item(
                Item={
                    "request_id": request_id,
                    "status": "PENDING",
                    "created_at_epoch": now,
                    "expires_at": now + self.ttl_seconds,
                },
                ConditionExpression="attribute_not_exists(request_id)",
            )
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                return False
            raise

    def mark_completed(self, request_id: str, result: LeadClassification) -> None:
        self.table.update_item(
            Key={"request_id": request_id},
            UpdateExpression="SET #s = :completed, result = :result, completed_at_epoch = :now",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":completed": "COMPLETED",
                ":pending": "PENDING",
                ":result": result.model_dump(),
                ":now": int(time.time()),
            },
            ConditionExpression="#s = :pending",
        )

    def mark_failed(self, request_id: str, error_code: str) -> None:
        # Release the idempotency claim so a bounded upstream retry can safely re-attempt.
        # The error code is emitted in structured logs by the Lambda adapter rather than
        # persisted with lead content in this minimal public implementation.
        _ = error_code
        self.table.delete_item(Key={"request_id": request_id})
