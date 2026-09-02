"""Lambda handler for POST /chat (cognito-auth-chatbot).

Conforms to contracts/openapi/chatbot.yaml: ChatRequest -> ChatResponse |
ErrorResponse. Never logs the raw event, the Authorization header, or the
chat message text -- only a request ID and the resulting status code.
"""
import json
import logging

from reply import generate_reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mirrors contracts/openapi/chatbot.yaml ChatRequest.message.maxLength --
# keep both in sync if either changes.
_MAX_MESSAGE_LENGTH = 2000


def _error_response(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message}),
    }


def lambda_handler(event: dict, context) -> dict:
    request_id = getattr(context, "aws_request_id", "unknown")

    try:
        payload = json.loads(event.get("body") or "")
    except (TypeError, json.JSONDecodeError):
        logger.info("request_id=%s status=400 reason=invalid_json", request_id)
        return _error_response(400, "Request body must be valid JSON.")

    if not isinstance(payload, dict):
        logger.info("request_id=%s status=400 reason=body_not_object", request_id)
        return _error_response(400, "Request body must be a JSON object.")

    allowed_keys = {"message"}
    if set(payload.keys()) - allowed_keys:
        logger.info("request_id=%s status=400 reason=unexpected_property", request_id)
        return _error_response(400, "Request body contains an unexpected property.")

    message = payload.get("message")
    if not isinstance(message, str) or not (1 <= len(message) <= _MAX_MESSAGE_LENGTH):
        logger.info("request_id=%s status=400 reason=message_bounds", request_id)
        return _error_response(
            400, f"'message' must be a string of length 1 to {_MAX_MESSAGE_LENGTH}."
        )

    reply = generate_reply(message)
    logger.info("request_id=%s status=200", request_id)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"reply": reply}),
    }
