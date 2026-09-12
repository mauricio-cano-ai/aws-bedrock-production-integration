import json

import pytest
from botocore.exceptions import ClientError

from src.aws_adapters import BedrockModelGateway, DynamoRequestStore, SSMApiKeyProvider
from src.models import LeadClassification


class BedrockClient:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self.text}]}}}


class SSMClient:
    def __init__(self):
        self.calls = 0

    def get_parameter(self, **kwargs):
        self.calls += 1
        return {"Parameter": {"Value": "secret"}}


class Table:
    def __init__(self):
        self.item = None
        self.updated = None

    def get_item(self, **kwargs):
        return {"Item": self.item} if self.item else {}

    def put_item(self, **kwargs):
        if self.item is not None:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "exists",
                    }
                },
                "PutItem",
            )
        self.item = kwargs["Item"]

    def update_item(self, **kwargs):
        self.updated = kwargs

    def delete_item(self, **kwargs):
        self.item = None


class RecordingTable(Table):
    def __init__(self, item=None):
        super().__init__()
        self.item = item
        self.deleted = None

    def delete_item(self, **kwargs):
        self.deleted = kwargs
        self.item = None


class ExplodingTable(Table):
    def put_item(self, **kwargs):
        raise ClientError(
            {
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "busy",
                }
            },
            "PutItem",
        )


def _classification(intent="buy"):
    return LeadClassification(
        intent=intent,
        urgency="medium",
        needs_human=False,
        rationale="test result",
    )


def test_bedrock_gateway_validates_json_contract():
    client = BedrockClient(
        json.dumps(
            {
                "intent": "buy",
                "urgency": "high",
                "needs_human": True,
                "rationale": "ready to visit",
            }
        )
    )
    gateway = BedrockModelGateway(client=client, model_id="amazon.nova-lite-v1:0")
    result = gateway.classify("quiero comprar")
    assert result.intent == "buy"
    assert result.needs_human is True
    assert client.calls[0]["modelId"] == "amazon.nova-lite-v1:0"


def test_bedrock_gateway_rejects_non_json_model_output():
    gateway = BedrockModelGateway(client=BedrockClient("not json"), model_id="m")
    with pytest.raises(ValueError, match="valid JSON"):
        gateway.classify("hola")


def test_ssm_key_provider_caches_decrypted_secret():
    client = SSMClient()
    provider = SSMApiKeyProvider(client=client, parameter_name="/path/key")
    assert provider.get() == "secret"
    assert provider.get() == "secret"
    assert client.calls == 1


def test_dynamo_claim_is_atomic_and_reports_conflict():
    table = Table()
    store = DynamoRequestStore(table=table, ttl_seconds=60)
    assert store.claim("request-1") is True
    assert store.claim("request-1") is False


def test_dynamo_get_completed_returns_typed_result_only_for_completed_records():
    store = DynamoRequestStore(
        table=RecordingTable(
            {
                "request_id": "r",
                "status": "COMPLETED",
                "result": _classification("rent").model_dump(),
            }
        )
    )
    result = store.get_completed("r")
    assert result is not None
    assert result.intent == "rent"

    pending = DynamoRequestStore(
        table=RecordingTable({"request_id": "r", "status": "PENDING"})
    )
    assert pending.get_completed("r") is None


def test_dynamo_mark_completed_requires_pending_owner_and_serializes_contract():
    table = RecordingTable({"request_id": "r", "status": "PENDING"})
    store = DynamoRequestStore(table=table)
    result = _classification()
    store.mark_completed("r", result)
    assert table.updated["Key"] == {"request_id": "r"}
    assert table.updated["ConditionExpression"] == "#s = :pending"
    assert table.updated["ExpressionAttributeValues"][":pending"] == "PENDING"
    assert table.updated["ExpressionAttributeValues"][":result"] == result.model_dump()


def test_dynamo_mark_failed_releases_claim():
    table = RecordingTable({"request_id": "r", "status": "PENDING"})
    store = DynamoRequestStore(table=table)
    store.mark_failed("r", "TimeoutError")
    assert table.deleted == {"Key": {"request_id": "r"}}


def test_dynamo_claim_reraises_non_conflict_client_errors():
    store = DynamoRequestStore(table=ExplodingTable())
    with pytest.raises(ClientError) as exc_info:
        store.claim("request-err")
    assert exc_info.value.response["Error"]["Code"] == "ProvisionedThroughputExceededException"


def test_bedrock_gateway_rejects_missing_expected_envelope():
    class MissingEnvelopeClient:
        def converse(self, **kwargs):
            return {"output": {}}

    gateway = BedrockModelGateway(client=MissingEnvelopeClient(), model_id="m")
    with pytest.raises(ValueError, match="valid JSON"):
        gateway.classify("hola")
