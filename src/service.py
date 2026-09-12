from __future__ import annotations

from dataclasses import dataclass

from .models import ClassificationRequest, ClassificationResponse
from .ports import ModelGateway, RequestStore


class RequestInProgressError(RuntimeError):
    """Another invocation already owns this request id."""


@dataclass(slots=True)
class ClassificationService:
    store: RequestStore
    gateway: ModelGateway

    def classify(self, request: ClassificationRequest) -> ClassificationResponse:
        cached = self.store.get_completed(request.request_id)
        if cached is not None:
            return ClassificationResponse(
                request_id=request.request_id,
                cached=True,
                result=cached,
            )

        if not self.store.claim(request.request_id):
            cached_after_race = self.store.get_completed(request.request_id)
            if cached_after_race is not None:
                return ClassificationResponse(
                    request_id=request.request_id,
                    cached=True,
                    result=cached_after_race,
                )
            raise RequestInProgressError(request.request_id)

        try:
            result = self.gateway.classify(request.message)
            self.store.mark_completed(request.request_id, result)
            return ClassificationResponse(
                request_id=request.request_id,
                cached=False,
                result=result,
            )
        except Exception as exc:
            self.store.mark_failed(request.request_id, type(exc).__name__)
            raise
