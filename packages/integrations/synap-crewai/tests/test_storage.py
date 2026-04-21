"""Tests for SynapStorageBackend."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture
def mock_sdk():
    sdk = MagicMock()
    sdk.fetch = AsyncMock()
    sdk.memories.create = AsyncMock()
    return sdk


@pytest.fixture
def backend(mock_sdk):
    from synap_crewai.storage import SynapStorageBackend
    return SynapStorageBackend(
        sdk=mock_sdk, user_id="u1", customer_id="c1",
    )


def test_import():
    from synap_crewai import SynapStorageBackend
    assert SynapStorageBackend is not None


@pytest.mark.asyncio
async def test_asave_calls_memories_create(backend, mock_sdk):
    from crewai.memory.types import MemoryRecord
    record = MemoryRecord(
        id="r1", content="User likes coffee",
        scope="/user/u1", category="preference",
        metadata={}, created_at=datetime.now(timezone.utc),
    )
    mock_sdk.memories.create.return_value = MagicMock(ingestion_id="ing-1")

    await backend.asave([record])

    mock_sdk.memories.create.assert_awaited_once()
    call_kwargs = mock_sdk.memories.create.call_args.kwargs
    assert call_kwargs["document"] == "User likes coffee"
    assert call_kwargs["user_id"] == "u1"


@pytest.mark.asyncio
async def test_asearch_calls_fetch(backend, mock_sdk):
    mock_sdk.fetch.return_value = MagicMock(
        facts=[], preferences=[], episodes=[],
        emotions=[], temporal_events=[],
        scope_map={},
    )

    results = await backend.asearch(
        query_embedding=[0.1, 0.2], limit=5,
    )

    mock_sdk.fetch.assert_awaited_once()
    assert isinstance(results, list)


def test_count_empty(backend):
    assert backend.count() == 0


def test_get_record_missing(backend):
    assert backend.get_record("nonexistent") is None


def test_reset_clears_records(backend):
    backend._records["r1"] = MagicMock()
    backend.reset()
    assert len(backend._records) == 0
