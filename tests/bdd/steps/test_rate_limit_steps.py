import hashlib
import re
import time
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from starlette.testclient import TestClient

from document_processor.adapters.web.main import create_app
from document_processor.adapters.web.middleware.rate_limit import RateLimitMiddleware
from document_processor.domain.services.document_service import DocumentService

_SHARED_WINDOWS: dict[str, list[float]] = defaultdict(list)


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


@pytest.fixture
def rate_limit_client(bdd_mock_repo, bdd_mock_storage, bdd_mock_ocr):
    global _SHARED_WINDOWS
    _SHARED_WINDOWS.clear()

    orig_init = RateLimitMiddleware.__init__

    def patched_init(self, app):
        orig_init(self, app)
        self._windows = _SHARED_WINDOWS

    RateLimitMiddleware.__init__ = patched_init

    service = DocumentService(
        repository=bdd_mock_repo,
        storage=bdd_mock_storage,
        ocr=bdd_mock_ocr,
        validator_registry={},
    )
    api_key_repo = MagicMock()
    api_key_repo.validate_key = AsyncMock(return_value=True)
    app = create_app(
        document_service=service,
        api_key_repository=api_key_repo,
        validator_registry={},
    )
    client = TestClient(app)

    yield client

    RateLimitMiddleware.__init__ = orig_init


def _fill_window(rate_limit_client: TestClient, key: str, count: int, offset_seconds: float = 0):
    key_hash = _hash_key(key)
    now = time.time()
    _SHARED_WINDOWS[key_hash] = [now - offset_seconds - i * 0.5 for i in range(count)]


@given(
    parsers.parse("client {client} has submitted {count:d} documents in the current minute"),
    target_fixture="rate_limit_setup",
)
def step_client_submitted(rate_limit_client, client: str, count: int):
    _fill_window(rate_limit_client, client, count)
    return {"client": client, "count": count}


@when(
    parsers.parse("client {client} POSTs to /documents"),
    target_fixture="rate_limit_response",
)
def step_client_posts(rate_limit_client, client: str):
    response = rate_limit_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": client},
        files={"file": ("test.jpg", b"test-data", "image/jpeg")},
        data={"type": "invoice", "region": "AR"},
    )
    return {"response": response, "client": client}


@then(parsers.parse("the response status is {status:d}"))
def step_response_status_rl(rate_limit_response, status: int):
    assert rate_limit_response["response"].status_code == status


@then(parsers.parse('the body contains "{text}"'))
def step_body_contains_rl(rate_limit_response, text: str):
    response_text = str(rate_limit_response["response"].content)
    assert text in response_text, f"Expected '{text}' in '{response_text}'"


@then(parsers.parse('the header "{header}" is present'))
def step_header_present(rate_limit_response, header: str):
    assert header in rate_limit_response["response"].headers


@given(
    parsers.parse("client {client} exceeded the rate limit at minute N"),
    target_fixture="rate_limit_setup",
)
def step_client_exceeded(rate_limit_client, client: str):
    _fill_window(rate_limit_client, client, 60, offset_seconds=65)
    return {"client": client, "count": 60, "exceeded": True}


@when(
    parsers.parse("client {client} POSTs at minute N+1"),
    target_fixture="rate_limit_response",
)
def step_client_posts_next(rate_limit_client, client: str):
    response = rate_limit_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": client},
        files={"file": ("test.jpg", b"x" * 100, "image/jpeg")},
        data={"type": "invoice", "region": "AR"},
    )
    return {"response": response, "client": client}


@then("a new request is accepted")
def step_request_accepted(rate_limit_response):
    assert rate_limit_response["response"].status_code == 202


@given(
    parsers.parse("client {limited_client} is at its limit"),
    target_fixture="rate_limit_setup",
)
def step_client_at_limit(rate_limit_client, limited_client: str):
    _fill_window(rate_limit_client, limited_client, 60)
    return {"limited_client": limited_client, "at_limit": True}


@then(re.compile(r"client (?P<client>\w+)'s request is accepted"))
def step_client_request_accepted_re(rate_limit_response, client: str):
    assert rate_limit_response["response"].status_code == 202


@then("client XYZ's request is accepted")
def step_xyz_request_accepted(rate_limit_response):
    assert rate_limit_response["response"].status_code == 202


scenarios("../features/rate_limiting.feature")
