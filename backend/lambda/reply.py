"""Rule-based chat reply logic for the cognito-auth-chatbot Lambda."""

_PATTERNS: dict[str, str] = {
    "hello": "Hello! How can I help you today?",
    "hi": "Hi there!",
    "bye": "Goodbye! Have a great day.",
    "goodbye": "Goodbye! Have a great day.",
    "thanks": "You're welcome!",
    "thank you": "You're welcome!",
}


def generate_reply(message: str) -> str:
    """Return a deterministic, rule-based reply for the given message.

    Matches on a lowercased, stripped copy of the message against a small
    set of known patterns; anything unmatched is echoed back.
    """
    normalized = message.strip().lower()
    if normalized in _PATTERNS:
        return _PATTERNS[normalized]
    return f"You said: {message}"
