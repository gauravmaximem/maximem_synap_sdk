"""Tests for SynapPlugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_semantic_kernel.plugin import SynapPlugin


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories.create = AsyncMock()
    return sdk


@pytest.fixture
def plugin(mock_sdk):
    return SynapPlugin(sdk=mock_sdk, user_id="u1")


def test_import():
    from synap_semantic_kernel import SynapPlugin
    assert SynapPlugin is not None


@pytest.mark.asyncio
async def test_search_memory(plugin, mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="likes coffee")

    result = await plugin.search_memory(query="coffee")

    assert result == "likes coffee"
    mock_sdk.fetch.assert_awaited_once()
    assert mock_sdk.fetch.call_args.kwargs["search_query"] == ["coffee"]


@pytest.mark.asyncio
async def test_search_memory_no_results(plugin, mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context=None)

    result = await plugin.search_memory(query="nothing")
    assert result == "No relevant memories found."


@pytest.mark.asyncio
async def test_store_memory(plugin, mock_sdk):
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-1")

    result = await plugin.store_memory(content="prefers dark mode")

    assert "ing-1" in result
    mock_sdk.memories.create.assert_awaited_once()
