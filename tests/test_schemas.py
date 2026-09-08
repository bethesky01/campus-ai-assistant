import pytest
from pydantic import ValidationError

from app.models.schemas import ChatRequest


def test_empty_question_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(question="   ")


def test_question_is_trimmed():
    assert ChatRequest(question="  attendance?  ").question == "attendance?"
