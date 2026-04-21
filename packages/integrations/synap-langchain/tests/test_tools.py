"""Tests for SynapSearchTool and SynapStoreTool."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_langchain.tools import SynapSearchTool, SynapStoreTool, _SearchInput, _StoreInput


@pytest.fixture
def mock_sdk():
    from maximem_synap import MaximemSynapSDK
    sdk = MagicMock(spec=MaximemSynapSDK)
    sdk.fetch = AsyncMock()
    sdk.memories = MagicMock()
    sdk.memories.create = AsyncMock()
    return sdk


@pytest.mark.asyncio
async def test_search_tool(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="User likes coffee")
    tool = SynapSearchTool.model_construct(
        sdk=mock_sdk, user_id="u1", customer_id=None,
        conversation_id=None, mode="accurate", max_results=10,
        name="search_memory", description="Search memory",
        args_schema=_SearchInput,
    )

    result = await tool._arun("coffee preferences")

    assert result == "User likes coffee"
    mock_sdk.fetch.assert_awaited_once()
    call_kwargs = mock_sdk.fetch.call_args.kwargs
    assert call_kwargs["search_query"] == ["coffee preferences"]
    assert call_kwargs["user_id"] == "u1"


@pytest.mark.asyncio
async def test_search_tool_no_results(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context=None)
    tool = SynapSearchTool.model_construct(
        sdk=mock_sdk, user_id="u1", customer_id=None,
        conversation_id=None, mode="accurate", max_results=10,
        name="search_memory", description="Search memory",
        args_schema=_SearchInput,
    )

    result = await tool._arun("unknown topic")
    assert result == "No relevant memories found."


@pytest.mark.asyncio
async def test_store_tool(mock_sdk):
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-123")
    tool = SynapStoreTool.model_construct(
        sdk=mock_sdk, user_id="u1", customer_id="c1",
        name="store_memory", description="Store memory",
        args_schema=_StoreInput,
    )

    result = await tool._arun("User prefers dark mode")

    assert "ing-123" in result
    mock_sdk.memories.create.assert_awaited_once_with(
        document="User prefers dark mode",
        user_id="u1",
        customer_id="c1",
    )
