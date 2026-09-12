from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ClassificationRequest(BaseModel):
    request_id: str = Field(min_length=3, max_length=160, pattern=r"^[A-Za-z0-9:._-]+$")
    message: str = Field(min_length=1, max_length=6000)

    @field_validator("message")
    @classmethod
    def message_must_have_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value


class LeadClassification(BaseModel):
    intent: Literal["buy", "rent", "sell", "information", "other"]
    urgency: Literal["low", "medium", "high"]
    needs_human: bool
    rationale: str = Field(min_length=1, max_length=300)


class ClassificationResponse(BaseModel):
    request_id: str
    cached: bool
    result: LeadClassification
