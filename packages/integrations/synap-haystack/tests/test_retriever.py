"""Tests for SynapRetriever (Haystack)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_haystack.retriever import SynapRetriever


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    return sdk


@pytest.fixture
def retriever(mock_sdk):
    return SynapRetriever(sdk=mock_sdk, user_id="u1")


def test_import():
    from synap_haystack import SynapRetriever, SynapMemoryWriter
    assert SynapRetriever is not None
    assert SynapMemoryWriter is not None


def test_run_calls_fetch(retriever, mock_sdk):
    mock_fact = MagicMock(
        content="likes coffee", id="f1", confidence=0.9,
        source="chat", valid_until=None, temporal_category=None,
    )
    mock_sdk.fetch.return_value = MagicMock(
        facts=[mock_fact], preferences=[], episodes=[],
        emotions=[], temporal_events=[], scope_map={"f1": "user"},
    )

    result = retriever.run(query="coffee")

    assert "documents" in result
    assert len(result["documents"]) == 1
    assert result["documents"][0].content == "likes coffee"
    mock_sdk.fetch.assert_awaited_once()
