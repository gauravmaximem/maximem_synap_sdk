"""Tests for create_synap_node."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_langchain.graph import create_synap_node


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    return sdk


@pytest.mark.asyncio
async def test_node_extracts_query_from_messages(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="context here")

    node = create_synap_node(mock_sdk, user_id="u1", conversation_id="conv-1")
    human_msg = MagicMock(type="human", content="what is my budget?")
    state = {"messages": [human_msg]}

    result = await node(state)

    assert result == {"synap_context": "context here"}
    call_kwargs = mock_sdk.fetch.call_args.kwargs
    assert call_kwargs["search_query"] == ["what is my budget?"]
    assert call_kwargs["conversation_id"] == "conv-1"
    assert call_kwargs["user_id"] == "u1"


@pytest.mark.asyncio
async def test_node_no_messages(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="")

    node = create_synap_node(mock_sdk, user_id="u1")
    result = await node({"messages": []})

    assert result == {"synap_context": ""}
    assert mock_sdk.fetch.call_args.kwargs["search_query"] is None


@pytest.mark.asyncio
async def test_node_custom_state_key(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="ctx")

    node = create_synap_node(mock_sdk, user_id="u1", state_key="memory")
    result = await node({"messages": []})

    assert "memory" in result


@pytest.mark.asyncio
async def test_node_dict_messages(mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(formatted_context="ctx")

    node = create_synap_node(mock_sdk, user_id="u1")
    state = {"messages": [{"role": "user", "content": "hello"}]}

    await node(state)
    assert mock_sdk.fetch.call_args.kwargs["search_query"] == ["hello"]
