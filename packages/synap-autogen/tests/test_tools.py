"""Tests for AutoGen tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_autogen.tools import SynapSearchTool, SynapStoreTool, SearchMemoryArgs, StoreMemoryArgs


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories.create = AsyncMock()
    return sdk


def test_import():
    from synap_autogen import SynapSearchTool, SynapStoreTool
    assert SynapSearchTool is not None
    assert SynapStoreTool is not None


@pytest.mark.asyncio
async def test_search_tool(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="User likes coffee")
    tool = SynapSearchTool(sdk=mock_sdk, user_id="u1")
    cancel_token = MagicMock()

    result = await tool.run(SearchMemoryArgs(query="coffee"), cancel_token)

    assert result.context == "User likes coffee"
    mock_sdk.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_tool_no_results(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context=None)
    tool = SynapSearchTool(sdk=mock_sdk, user_id="u1")

    result = await tool.run(SearchMemoryArgs(query="unknown"), MagicMock())
    assert result.context == "No relevant memories found."


@pytest.mark.asyncio
async def test_store_tool(mock_sdk):
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-1")
    tool = SynapStoreTool(sdk=mock_sdk, user_id="u1")

    result = await tool.run(StoreMemoryArgs(content="likes dark mode"), MagicMock())

    assert result.ingestion_id == "ing-1"
    mock_sdk.memories.create.assert_awaited_once()
