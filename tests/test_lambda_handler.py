import json

import src.app as app
from src.models import ClassificationResponse, LeadClassification


class Service:
    def classify(self, request):
        return ClassificationResponse(
            request_id=request.request_id,
            cached=False,
            result=LeadClassification(
                intent="other",
                urgency="low",
                needs_human=False,
                rationale="test",
            ),
        )


def test_lambda_handler_delegates_to_http_adapter_with_cached_runtime(monkeypatch):
    monkeypatch.setattr(app, "_runtime_cache", ("secret", Service()))
    event = {
        "headers": {"x-eai-key": "secret"},
        "body": json.dumps({"request_id": "req-lambda", "message": "hola"}),
    }
    response = app.lambda_handler(event, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["request_id"] == "req-lambda"

class FakeSSM:
    def get_parameter(self, **kwargs):
        return {"Parameter": {"Value": "built-secret"}}


class FakeDynamoResource:
    def __init__(self):
        self.table_name = None
    def Table(self, name):
        self.table_name = name
        return object()


def test_build_runtime_composes_aws_adapters_from_environment(monkeypatch):
    monkeypatch.setenv("MODEL_ID", "model-1")
    monkeypatch.setenv("TABLE_NAME", "table-1")
    monkeypatch.setenv("AUTH_PARAM_NAME", "/secret/path")
    fake_ddb = FakeDynamoResource()
    clients = {"bedrock-runtime": object(), "ssm": FakeSSM()}
    monkeypatch.setattr(app.boto3, "client", lambda name: clients[name])
    monkeypatch.setattr(app.boto3, "resource", lambda name: fake_ddb)

    key, service = app._build_runtime()

    assert key == "built-secret"
    assert fake_ddb.table_name == "table-1"
    assert service.gateway.model_id == "model-1"


def test_runtime_builds_once_and_reuses_cache(monkeypatch):
    monkeypatch.setattr(app, "_runtime_cache", None)
    calls = []
    sentinel = ("k", Service())
    monkeypatch.setattr(app, "_build_runtime", lambda: calls.append(True) or sentinel)
    assert app._runtime() is sentinel
    assert app._runtime() is sentinel
    assert calls == [True]
