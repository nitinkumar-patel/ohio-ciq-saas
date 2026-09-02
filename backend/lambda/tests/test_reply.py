"""Unit tests for generate_reply's contract surface (AC-6, AC-7)."""
import pytest

from reply import generate_reply


def test_generate_reply_is_deterministic_for_same_input():
    first = generate_reply("hello")
    second = generate_reply("hello")
    assert first == second


def test_generate_reply_varies_by_input():
    reply_a = generate_reply("hello")
    reply_b = generate_reply("goodbye")
    assert reply_a != reply_b


@pytest.mark.parametrize(
    "message",
    ["HELLO", "  hi  ", "Thank You"],
)
def test_generate_reply_normalizes_case_and_whitespace(message):
    assert generate_reply(message) == generate_reply(message.strip().lower())


def test_generate_reply_echoes_unrecognized_input():
    assert generate_reply("xyzzy") == "You said: xyzzy"
