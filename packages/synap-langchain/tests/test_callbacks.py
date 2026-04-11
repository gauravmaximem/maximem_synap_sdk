"""Tests for SynapCallbackHandler."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from synap_langchain.callbacks import SynapCallbackHandler


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.conversation.record_message = AsyncMock()
    return sdk


@pytest.fixture
def handler(mock_sdk):
    return SynapCallbackHandler(
        sdk=mock_sdk,
        conversation_id="conv-1",
        user_id="user-1",
        customer_id="cust-1",
    )


@pytest.mark.asyncio
async def test_on_chat_model_start_records_user_message(handler, mock_sdk):
    human_msg = MagicMock(type="human", content="hello world")
    system_msg = MagicMock(type="system", content="you are helpful")

    await handler.on_chat_model_start(
        serialized={},
        messages=[[system_msg, human_msg]],
        run_id=uuid4(),
    )

    mock_sdk.conversation.record_message.assert_awaited_once_with(
        conversation_id="conv-1",
        role="user",
        content="hello world",
        user_id="user-1",
        customer_id="cust-1",
    )


@pytest.mark.asyncio
async def test_on_chat_model_start_empty_messages(handler, mock_sdk):
    await handler.on_chat_model_start(
        serialized={}, messages=[], run_id=uuid4(),
    )
    mock_sdk.conversation.record_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_llm_end_records_assistant(handler, mock_sdk):
    gen = MagicMock(text="I can help with that")
    response = MagicMock(generations=[[gen]])

    await handler.on_llm_end(response=response, run_id=uuid4())

    mock_sdk.conversation.record_message.assert_awaited_once_with(
        conversation_id="conv-1",
        role="assistant",
        content="I can help with that",
        user_id="user-1",
        customer_id="cust-1",
    )


@pytest.mark.asyncio
async def test_on_llm_end_handles_error(handler, mock_sdk):
    mock_sdk.conversation.record_message.side_effect = Exception("fail")
    gen = MagicMock(text="response")
    response = MagicMock(generations=[[gen]])
    # Should not raise
    await handler.on_llm_end(response=response, run_id=uuid4())
