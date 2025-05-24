import json
import pytest
import requests
from unittest.mock import patch, MagicMock
from app.agent import Agent

@pytest.fixture
def agent():
    return Agent()

def make_response(content_lines, done=True):
    """Helper to simulate streaming lines from requests."""
    class FakeResp:
        def __init__(self, lines):
            self._lines = lines
            self.status_code = 200
        def raise_for_status(self):
            pass
        def iter_lines(self, decode_unicode):
            return self._lines
        @property
        def text(self):
            return "\n".join(self._lines)

    return FakeResp(content_lines)

@patch("app.agent.requests.post")
def test_ask_llm_streaming(mock_post, agent):
    # Simulate two JSON chunks then a final done chunk
    lines = [
        json.dumps({"message": {"content": "Hello"}, "done": False}),
        json.dumps({"message": {"content": " world!"}, "done": True})
    ]
    mock_post.return_value = make_response(lines)
    reply = agent.ask_llm("hi")
    assert reply == "Hello world!"

@patch("app.agent.requests.post")
def test_ask_llm_fallback_raw(mock_post, agent):
    # Simulate a non-JSON response
    fake = MagicMock()
    fake.raise_for_status = lambda: None
    fake.iter_lines = lambda decode: []
    fake.text = "not-json"
    mock_post.return_value = fake

    reply = agent.ask_llm("hi")
    assert reply == "not-json"
