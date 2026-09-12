from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from typing import Any, cast

from pydantic import ValidationError

from .models import ClassificationRequest
from .service import ClassificationService, RequestInProgressError


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, separators=(",", ":")),
    }


def _header(event: dict[str, Any], name: str) -> str:
    wanted = name.lower()
    raw_headers = event.get("headers")
    if not isinstance(raw_headers, Mapping):
        return ""

    headers = cast(Mapping[object, object], raw_headers)
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return ""


def handle_http_event(
    event: dict[str, Any],
    expected_api_key: str,
    service: ClassificationService,
) -> dict[str, Any]:
    supplied_key = _header(event, "x-eai-key")
    if not supplied_key or not hmac.compare_digest(supplied_key, expected_api_key):
        return _response(401, {"error": "unauthorized"})

    try:
        raw_body = event.get("body") or "{}"
        parsed = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        request = ClassificationRequest.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return _response(422, {"error": "invalid_request"})

    try:
        result = service.classify(request)
    except RequestInProgressError:
        return _response(409, {"error": "request_in_progress", "request_id": request.request_id})

    return _response(200, result.model_dump())
