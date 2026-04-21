"""Tests for SynapRetriever (LlamaIndex)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_llamaindex.retriever import SynapRetriever


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    return sdk


@pytest.fixture
def retriever(mock_sdk):
    return SynapRetriever(
        sdk=mock_sdk, user_id="u1", mode="accurate",
    )


@pytest.mark.asyncio
async def test_aretrieve_returns_nodes(retriever, mock_sdk):
    from llama_index.core.schema import QueryBundle

    mock_fact = MagicMock(
        content="likes tea", id="f1", confidence=0.85,
        source="chat", valid_until=None, temporal_category=None,
    )
    mock_sdk.fetch.return_value = MagicMock(
        facts=[mock_fact], preferences=[], episodes=[],
        emotions=[], temporal_events=[], scope_map={"f1": "user"},
    )

    nodes = await retriever._aretrieve(QueryBundle(query_str="tea"))

    assert len(nodes) == 1
    assert nodes[0].node.text == "likes tea"
    assert nodes[0].score == 0.85
    mock_sdk.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_aretrieve_empty(retriever, mock_sdk):
    from llama_index.core.schema import QueryBundle

    mock_sdk.fetch.return_value = MagicMock(
        facts=[], preferences=[], episodes=[],
        emotions=[], temporal_events=[], scope_map={},
    )

    nodes = await retriever._aretrieve(QueryBundle(query_str="nothing"))
    assert nodes == []
