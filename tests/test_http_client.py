import pytest
import requests
from app.http_client import fetch_url

class DummyResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(f"Status {self.status_code}")

def test_fetch_url_success(monkeypatch):
    # Simulate a 200-OK response
    monkeypatch.setattr(requests, "get", lambda url, timeout: DummyResponse("hello page", 200))
    result = fetch_url("http://example.com")
    assert result == "hello page"

def test_fetch_url_http_error(monkeypatch):
    # Simulate a 404 response -> ValueError
    monkeypatch.setattr(requests, "get", lambda url, timeout: DummyResponse("not found", 404))
    with pytest.raises(ValueError) as excinfo:
        fetch_url("http://example.com/missing")
    assert "Failed to fetch" in str(excinfo.value)

def test_fetch_url_request_exception(monkeypatch):
    # Simulate a network error
    def bad_get(url, timeout):
        raise requests.ConnectionError("no network")
    monkeypatch.setattr(requests, "get", bad_get)
    with pytest.raises(ValueError) as excinfo:
        fetch_url("http://example.com")
    assert "Failed to fetch" in str(excinfo.value)
