"""Tests for SynapMemoryWriter (Haystack)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from synap_haystack.writer import SynapMemoryWriter


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.conversation.record_message = AsyncMock()
    return sdk


@pytest.fixture
def writer(mock_sdk):
    return SynapMemoryWriter(
        sdk=mock_sdk, conversation_id="conv-1",
        user_id="u1", customer_id="c1",
    )


def test_run_records_messages(writer, mock_sdk):
    from haystack import Document

    docs = [
        Document(content="hello", meta={"role": "user"}),
        Document(content="hi there", meta={"role": "assistant"}),
    ]

    result = writer.run(documents=docs)

    assert result["written_count"] == 2
    assert mock_sdk.conversation.record_message.await_count == 2
