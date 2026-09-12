from __future__ import annotations

import json
import os
from typing import Any

import boto3

from .aws_adapters import BedrockModelGateway, DynamoRequestStore, SSMApiKeyProvider
from .http_adapter import handle_http_event
from .service import ClassificationService

_runtime_cache: tuple[str, ClassificationService] | None = None


def _build_runtime() -> tuple[str, ClassificationService]:
    model_id = os.environ["MODEL_ID"]
    table_name = os.environ["TABLE_NAME"]
    auth_parameter_name = os.environ["AUTH_PARAM_NAME"]

    bedrock = boto3.client("bedrock-runtime")
    dynamodb = boto3.resource("dynamodb")
    ssm = boto3.client("ssm")

    api_key = SSMApiKeyProvider(ssm, auth_parameter_name).get()
    store = DynamoRequestStore(dynamodb.Table(table_name))
    gateway = BedrockModelGateway(bedrock, model_id)
    return api_key, ClassificationService(store=store, gateway=gateway)


def _runtime() -> tuple[str, ClassificationService]:
    global _runtime_cache
    if _runtime_cache is None:
        _runtime_cache = _build_runtime()
    return _runtime_cache


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    api_key, service = _runtime()
    request_context = event.get("requestContext") or {}
    request_id = request_context.get("requestId") or getattr(context, "aws_request_id", None)
    print(json.dumps({"event": "classification_request_received", "aws_request_id": request_id}))
    response = handle_http_event(event, api_key, service)
    print(
        json.dumps(
            {
                "event": "classification_request_finished",
                "status_code": response["statusCode"],
                "aws_request_id": request_id,
            }
        )
    )
    return response
