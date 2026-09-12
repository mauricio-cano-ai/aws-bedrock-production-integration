import pytest

from src.models import ClassificationRequest, LeadClassification
from src.service import ClassificationService, RequestInProgressError


class FakeStore:
    def __init__(self):
        self.items = {}
        self.failed = []

    def get_completed(self, request_id: str):
        item = self.items.get(request_id)
        if item and item["status"] == "COMPLETED":
            return item["result"]
        return None

    def claim(self, request_id: str) -> bool:
        if request_id in self.items:
            return False
        self.items[request_id] = {"status": "PENDING"}
        return True

    def mark_completed(self, request_id: str, result: LeadClassification) -> None:
        self.items[request_id] = {"status": "COMPLETED", "result": result}

    def mark_failed(self, request_id: str, error_code: str) -> None:
        self.failed.append((request_id, error_code))
        self.items.pop(request_id, None)


class FakeGateway:
    def __init__(self, result=None, error=None):
        self.result = result or LeadClassification(
            intent="buy",
            urgency="medium",
            needs_human=False,
            rationale="clear purchase intent",
        )
        self.error = error
        self.calls = 0

    def classify(self, message: str) -> LeadClassification:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


class RaceStore(FakeStore):
    def __init__(self, completed):
        super().__init__()
        self.completed = completed
        self.reads = 0

    def get_completed(self, request_id: str):
        self.reads += 1
        if self.reads >= 2:
            return self.completed
        return None

    def claim(self, request_id: str) -> bool:
        return False


def test_first_request_calls_model_and_persists_result():
    store = FakeStore()
    gateway = FakeGateway()
    service = ClassificationService(store=store, gateway=gateway)

    response = service.classify(
        ClassificationRequest(request_id="r-1", message="Quiero comprar casa")
    )

    assert response.cached is False
    assert response.result.intent == "buy"
    assert gateway.calls == 1
    assert store.items["r-1"]["status"] == "COMPLETED"


def test_completed_request_returns_cache_without_model_call():
    store = FakeStore()
    cached = LeadClassification(
        intent="rent",
        urgency="low",
        needs_human=False,
        rationale="rental search",
    )
    store.items["r-2"] = {"status": "COMPLETED", "result": cached}
    gateway = FakeGateway()
    service = ClassificationService(store=store, gateway=gateway)

    response = service.classify(
        ClassificationRequest(request_id="r-2", message="Busco renta")
    )

    assert response.cached is True
    assert response.result.intent == "rent"
    assert gateway.calls == 0


def test_inflight_duplicate_is_rejected_without_second_model_call():
    store = FakeStore()
    store.items["r-3"] = {"status": "PENDING"}
    gateway = FakeGateway()
    service = ClassificationService(store=store, gateway=gateway)

    with pytest.raises(RequestInProgressError):
        service.classify(ClassificationRequest(request_id="r-3", message="hola"))

    assert gateway.calls == 0


def test_gateway_failure_releases_claim_for_safe_retry():
    store = FakeStore()
    gateway = FakeGateway(error=TimeoutError("bedrock timeout"))
    service = ClassificationService(store=store, gateway=gateway)

    with pytest.raises(TimeoutError):
        service.classify(ClassificationRequest(request_id="r-4", message="hola"))

    assert "r-4" not in store.items
    assert store.failed == [("r-4", "TimeoutError")]


def test_losing_claim_can_observe_winner_result_and_return_cache():
    completed = LeadClassification(
        intent="information",
        urgency="low",
        needs_human=False,
        rationale="winner completed while this invocation raced",
    )
    store = RaceStore(completed)
    gateway = FakeGateway()
    service = ClassificationService(store=store, gateway=gateway)

    response = service.classify(
        ClassificationRequest(request_id="r-race", message="status?")
    )

    assert response.cached is True
    assert response.result.intent == "information"
    assert store.reads == 2
    assert gateway.calls == 0
