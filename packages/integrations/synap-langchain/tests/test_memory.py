"""Tests for SynapChatMessageHistory."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from synap_langchain.memory import SynapChatMessageHistory, SynapMemory


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.conversation.context.get_context_for_prompt = AsyncMock()
    sdk.conversation.record_message = AsyncMock()
    sdk.cache.clear = MagicMock()
    return sdk


@pytest.fixture
def history(mock_sdk):
    return SynapChatMessageHistory(
        sdk=mock_sdk,
        conversation_id="conv-1",
        user_id="user-1",
        customer_id="cust-1",
    )


def test_backward_compat_alias():
    assert SynapMemory is SynapChatMessageHistory


@pytest.mark.asyncio
async def test_aget_messages_returns_messages(history, mock_sdk):
    mock_msg1 = MagicMock(role="user", content="hello")
    mock_msg2 = MagicMock(role="assistant", content="hi there")
    mock_ctx = MagicMock(recent_messages=[mock_msg1, mock_msg2])
    mock_sdk.conversation.context.get_context_for_prompt.return_value = mock_ctx

    msgs = await history.aget_messages()

    assert len(msgs) == 2
    assert msgs[0].content == "hello"
    assert msgs[1].content == "hi there"
    mock_sdk.conversation.context.get_context_for_prompt.assert_awaited_once_with(
        conversation_id="conv-1",
    )


@pytest.mark.asyncio
async def test_aget_messages_empty(history, mock_sdk):
    mock_sdk.conversation.context.get_context_for_prompt.return_value = MagicMock(
        recent_messages=[]
    )
    msgs = await history.aget_messages()
    assert msgs == []


@pytest.mark.asyncio
async def test_aget_messages_handles_error(history, mock_sdk):
    mock_sdk.conversation.context.get_context_for_prompt.side_effect = Exception("fail")
    msgs = await history.aget_messages()
    assert msgs == []


@pytest.mark.asyncio
async def test_aadd_messages(history, mock_sdk):
    from langchain_core.messages import HumanMessage, AIMessage

    msgs = [HumanMessage(content="hi"), AIMessage(content="hello")]
    await history.aadd_messages(msgs)

    assert mock_sdk.conversation.record_message.await_count == 2
    calls = mock_sdk.conversation.record_message.call_args_list
    assert calls[0].kwargs["role"] == "user"
    assert calls[0].kwargs["content"] == "hi"
    assert calls[1].kwargs["role"] == "assistant"
    assert calls[1].kwargs["content"] == "hello"


@pytest.mark.asyncio
async def test_aadd_messages_handles_error(history, mock_sdk):
    from langchain_core.messages import HumanMessage

    mock_sdk.conversation.record_message.side_effect = Exception("fail")
    # Should not raise
    await history.aadd_messages([HumanMessage(content="hi")])


def test_clear(history, mock_sdk):
    history.clear()
    mock_sdk.cache.clear.assert_called_once()
