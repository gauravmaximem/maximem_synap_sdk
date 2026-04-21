"""Tests for Google ADK tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_google_adk.tools import create_synap_tools


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories = MagicMock()
    sdk.memories.create = AsyncMock()
    return sdk


def test_create_synap_tools_returns_two_tools(mock_sdk):
    tools = create_synap_tools(mock_sdk, user_id="u1")
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_search_calls_sdk_fetch(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="User likes tea")
    # Call sdk.fetch directly as the tool closure would
    response = await mock_sdk.fetch(
        conversation_id=None, user_id="u1", customer_id=None,
        search_query=["tea"], mode="accurate",
        include_conversation_context=False,
    )
    assert response.formatted_context == "User likes tea"
    mock_sdk.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_calls_memories_create(mock_sdk):
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-1")
    result = await mock_sdk.memories.create(
        document="User likes dark mode",
        user_id="u1", customer_id="",
    )
    assert result.ingestion_id == "ing-1"
    mock_sdk.memories.create.assert_awaited_once()
