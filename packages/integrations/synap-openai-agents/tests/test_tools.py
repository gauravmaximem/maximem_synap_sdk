"""Tests for OpenAI Agents tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_openai_agents.tools import create_search_tool, create_store_tool


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories.create = AsyncMock()
    return sdk


def test_import():
    from synap_openai_agents import create_search_tool, create_store_tool
    assert create_search_tool is not None
    assert create_store_tool is not None


@pytest.mark.asyncio
async def test_search_tool(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="User likes tea")
    search = create_search_tool(mock_sdk, user_id="u1")

    result = await search(query="tea")

    assert "tea" in result.lower()
    mock_sdk.fetch.assert_awaited_once()
    assert mock_sdk.fetch.call_args.kwargs["search_query"] == ["tea"]


@pytest.mark.asyncio
async def test_search_tool_no_results(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context=None)
    search = create_search_tool(mock_sdk, user_id="u1")

    result = await search(query="unknown")
    assert result == "No relevant memories found."


@pytest.mark.asyncio
async def test_store_tool(mock_sdk):
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-1")
    store = create_store_tool(mock_sdk, user_id="u1")

    result = await store(content="prefers dark mode")

    assert "ing-1" in result
    mock_sdk.memories.create.assert_awaited_once()
