import pytest
from pydantic import ValidationError

from src.models import ClassificationRequest


def test_message_must_contain_non_whitespace_content():
    with pytest.raises(ValidationError):
        ClassificationRequest(request_id="req-space", message="   ")
