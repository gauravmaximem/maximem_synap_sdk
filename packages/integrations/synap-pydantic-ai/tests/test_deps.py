"""Tests for SynapDeps and register_synap_tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_pydantic_ai.deps import SynapDeps


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories.create = AsyncMock()
    return sdk


def test_import():
    from synap_pydantic_ai import SynapDeps, register_synap_tools
    assert SynapDeps is not None
    assert register_synap_tools is not None


def test_deps_creation(mock_sdk):
    deps = SynapDeps(sdk=mock_sdk, user_id="u1", customer_id="c1")

    assert deps.sdk is mock_sdk
    assert deps.user_id == "u1"
    assert deps.customer_id == "c1"
    assert deps.conversation_id is None


def test_deps_with_conversation(mock_sdk):
    deps = SynapDeps(
        sdk=mock_sdk, user_id="u1",
        conversation_id="conv-1",
    )
    assert deps.conversation_id == "conv-1"
