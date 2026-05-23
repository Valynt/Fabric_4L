"""Shared API fixtures for Layer 1 tests."""

import uuid

import pytest
from fastapi.testclient import TestClient

from value_fabric.layer1.api.main import app


@pytest.fixture
def engine():
    return None


@pytest.fixture
def db():
    return None


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def other_org_id():
    return uuid.uuid4()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def make_target():
    return lambda *_args, **_kwargs: uuid.uuid4()
