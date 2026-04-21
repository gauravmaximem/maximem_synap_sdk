"""Tests for SynapChatMemory."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_llamaindex.memory import SynapChatMemory


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.conversation.context.get_context_for_prompt = AsyncMock()
    sdk.conversation.record_message = AsyncMock()
    return sdk


@pytest.fixture
def memory(mock_sdk):
    return SynapChatMemory(
        sdk=mock_sdk, conversation_id="conv-1",
        user_id="u1", customer_id="c1",
    )


def test_import():
    from synap_llamaindex import SynapChatMemory, SynapRetriever
    assert SynapChatMemory is not None
    assert SynapRetriever is not None


@pytest.mark.asyncio
async def test_aget_returns_chat_messages(memory, mock_sdk):
    mock_msg = MagicMock(role="user", content="hello")
    mock_ctx = MagicMock(
        recent_messages=[mock_msg],
        formatted_context="some context",
    )
    mock_sdk.conversation.context.get_context_for_prompt.return_value = mock_ctx
    mock_sdk.fetch.return_value = MagicMock(formatted_context=None)

    msgs = await memory.aget()

    assert len(msgs) >= 1
    mock_sdk.conversation.context.get_context_for_prompt.assert_awaited_once()


@pytest.mark.asyncio
async def test_aput_records_message(memory, mock_sdk):
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
    msg = ChatMessage(role=MessageRole.USER, content="hi there")

    await memory.aput(msg)

    mock_sdk.conversation.record_message.assert_awaited_once()
    call_kwargs = mock_sdk.conversation.record_message.call_args.kwargs
    assert call_kwargs["role"] == "user"
    assert call_kwargs["content"] == "hi there"


@pytest.mark.asyncio
async def test_areset(memory, mock_sdk):
    # Should not raise
    await memory.areset()
