"""Tests for SynapRetriever."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_langchain.retriever import SynapRetriever


@pytest.fixture
def mock_sdk():
    from maximem_synap import MaximemSynapSDK
    sdk = MagicMock(spec=MaximemSynapSDK)
    sdk.fetch = AsyncMock()
    return sdk


@pytest.fixture
def retriever(mock_sdk):
    return SynapRetriever.model_construct(
        sdk=mock_sdk,
        user_id="user-1",
        customer_id="cust-1",
        mode="accurate",
        max_results=20,
        types=None,
        conversation_id=None,
    )


@pytest.mark.asyncio
async def test_retriever_returns_documents(retriever, mock_sdk):
    mock_fact = MagicMock(
        content="likes coffee", id="f1", confidence=0.9,
        source="chat", valid_until=None, temporal_category=None,
    )
    mock_pref = MagicMock(
        content="dark mode", id="p1", strength=0.8, category="ui",
    )
    mock_response = MagicMock(
        facts=[mock_fact],
        preferences=[mock_pref],
        episodes=[],
        emotions=[],
        temporal_events=[],
        scope_map={"f1": "user", "p1": "user"},
    )
    mock_sdk.fetch.return_value = mock_response

    run_manager = MagicMock()
    docs = await retriever._aget_relevant_documents("coffee", run_manager=run_manager)

    assert len(docs) == 2
    assert docs[0].page_content == "likes coffee"
    assert docs[0].metadata["type"] == "fact"
    assert docs[0].metadata["confidence"] == 0.9
    assert docs[1].page_content == "dark mode"
    assert docs[1].metadata["type"] == "preference"

    mock_sdk.fetch.assert_awaited_once_with(
        conversation_id=None,
        user_id="user-1",
        customer_id="cust-1",
        search_query=["coffee"],
        max_results=20,
        types=None,
        mode="accurate",
        include_conversation_context=False,
    )


@pytest.mark.asyncio
async def test_retriever_empty_response(retriever, mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(
        facts=[], preferences=[], episodes=[], emotions=[], temporal_events=[],
        scope_map={},
    )
    run_manager = MagicMock()
    docs = await retriever._aget_relevant_documents("nothing", run_manager=run_manager)
    assert docs == []
