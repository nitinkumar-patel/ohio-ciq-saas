"""Unit tests for the lambda_handler contract surface (AC-17, AC-20)."""
import json

import app
from app import lambda_handler


class _FakeContext:
    aws_request_id = "test-request-id"


def _invoke(body):
    event = {"body": json.dumps(body) if not isinstance(body, str) else body}
    return lambda_handler(event, _FakeContext())


def test_valid_message_returns_200_with_reply():
    response = _invoke({"message": "hello"})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "reply" in body
    assert isinstance(body["reply"], str)


def test_missing_message_returns_400():
    response = _invoke({})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "message" in body


def test_empty_message_returns_400():
    response = _invoke({"message": ""})
    assert response["statusCode"] == 400


def test_over_max_length_message_returns_400():
    response = _invoke({"message": "a" * (app._MAX_MESSAGE_LENGTH + 1)})
    assert response["statusCode"] == 400


def test_unexpected_property_returns_400():
    response = _invoke({"message": "hello", "extra": "nope"})
    assert response["statusCode"] == 400


def test_unparseable_body_returns_400():
    response = _invoke("not-json")
    assert response["statusCode"] == 400


def test_non_object_body_returns_400():
    response = _invoke("[1, 2]")
    assert response["statusCode"] == 400


def test_message_at_minimum_length_returns_200():
    response = _invoke({"message": "a"})
    assert response["statusCode"] == 200


def test_message_at_maximum_length_returns_200():
    response = _invoke({"message": "a" * app._MAX_MESSAGE_LENGTH})
    assert response["statusCode"] == 200
