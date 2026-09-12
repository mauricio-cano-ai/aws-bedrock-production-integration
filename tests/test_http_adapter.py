import json

from src.http_adapter import handle_http_event
from src.models import ClassificationResponse, LeadClassification
from src.service import RequestInProgressError


class StubService:
    def __init__(self):
        self.calls = 0

    def classify(self, request):
        self.calls += 1
        return ClassificationResponse(
            request_id=request.request_id,
            cached=False,
            result=LeadClassification(
                intent="information",
                urgency="low",
                needs_human=False,
                rationale="general information request",
            ),
        )


class InProgressService:
    def classify(self, request):
        raise RequestInProgressError(request.request_id)


def _event(body, key=None):
    headers = {}
    if key is not None:
        headers["X-EAI-Key"] = key
    return {"headers": headers, "body": json.dumps(body)}


def test_missing_key_returns_401_before_service_execution():
    service = StubService()
    response = handle_http_event(
        _event({"request_id": "req-1", "message": "hola"}),
        "secret",
        service,
    )
    assert response["statusCode"] == 401
    assert service.calls == 0


def test_valid_request_returns_typed_json_without_echoing_input_message():
    service = StubService()
    response = handle_http_event(
        _event({"request_id": "req-2", "message": "informacion"}, key="secret"),
        "secret",
        service,
    )
    payload = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert payload["request_id"] == "req-2"
    assert payload["result"]["intent"] == "information"
    assert "message" not in payload
    assert service.calls == 1


def test_invalid_payload_returns_422_and_does_not_call_service():
    service = StubService()
    response = handle_http_event(
        _event({"request_id": "x", "message": ""}, key="secret"),
        "secret",
        service,
    )
    assert response["statusCode"] == 422
    assert service.calls == 0


def test_inflight_request_maps_to_409_without_leaking_request_body():
    response = handle_http_event(
        _event({"request_id": "req-busy", "message": "private lead text"}, key="secret"),
        "secret",
        InProgressService(),
    )
    payload = json.loads(response["body"])
    assert response["statusCode"] == 409
    assert payload == {"error": "request_in_progress", "request_id": "req-busy"}
    assert "private lead text" not in response["body"]


def test_malformed_json_returns_422():
    service = StubService()
    event = {"headers": {"x-eai-key": "secret"}, "body": "{"}
    response = handle_http_event(event, "secret", service)
    assert response["statusCode"] == 422
    assert service.calls == 0


def test_non_mapping_headers_are_treated_as_missing_key():
    service = StubService()
    event = {
        "headers": ["x-eai-key", "secret"],
        "body": json.dumps({"request_id": "req-headers", "message": "hola"}),
    }

    response = handle_http_event(event, "secret", service)

    assert response["statusCode"] == 401
    assert service.calls == 0
