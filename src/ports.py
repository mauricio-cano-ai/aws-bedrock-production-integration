from __future__ import annotations

from typing import Protocol

from .models import LeadClassification


class RequestStore(Protocol):
    def get_completed(self, request_id: str) -> LeadClassification | None:
        ...

    def claim(self, request_id: str) -> bool:
        ...

    def mark_completed(self, request_id: str, result: LeadClassification) -> None:
        ...

    def mark_failed(self, request_id: str, error_code: str) -> None:
        ...


class ModelGateway(Protocol):
    def classify(self, message: str) -> LeadClassification:
        ...
