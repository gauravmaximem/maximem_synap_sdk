"""Synap storage backend for CrewAI Memory.

Implements CrewAI's StorageBackend protocol so that CrewAI's unified
Memory class stores and retrieves memories via Synap's cloud platform.

CrewAI handles LLM analysis, categorization, and importance scoring.
This backend handles persistence and retrieval by delegating to the
Synap SDK.
"""

import asyncio
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from crewai.memory.types import MemoryRecord, ScopeInfo

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import nest_asyncio
    nest_asyncio.apply()
    return loop.run_until_complete(coro)


class SynapStorageBackend:
    """CrewAI StorageBackend backed by Synap.

    Delegates memory persistence to Synap's ingestion system
    and retrieval to Synap's search system.

    Example:
        from crewai.memory import Memory
        from synap_crewai import SynapStorageBackend

        backend = SynapStorageBackend(
            sdk=sdk, user_id="user-456", customer_id="cust-789",
        )
        memory = Memory(storage=backend)
        crew = Crew(agents=agents, tasks=tasks, memory=memory)
    """

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        user_id: str,
        customer_id: str = "",
        conversation_id: Optional[str] = None,
        mode: str = "fast",
    ):
        self.sdk = sdk
        self.user_id = user_id
        self.customer_id = customer_id
        self.conversation_id = conversation_id
        self.mode = mode
        # Local record cache for get_record/list_records
        # (CrewAI calls these for metadata ops, not core flow)
        self._records: Dict[str, MemoryRecord] = {}

    # ------------------------------------------------------------------
    # Core methods (used by CrewAI's Memory.remember / Memory.recall)
    # ------------------------------------------------------------------

    def save(self, records: List[MemoryRecord]) -> None:
        """Persist memory records via Synap ingestion."""
        _run_async(self.asave(records))

    async def asave(self, records: List[MemoryRecord]) -> None:
        for record in records:
            try:
                await self.sdk.memories.create(
                    document=record.content,
                    user_id=self.user_id,
                    customer_id=self.customer_id,
                    metadata={
                        "crewai_record_id": record.id,
                        "scope": record.scope,
                        "categories": record.categories,
                        "importance": record.importance,
                        "source": record.source or "",
                    },
                )
                self._records[record.id] = record
            except Exception as e:
                logger.warning("SynapStorageBackend: save failed for record %s: %s", record.id, e)

    def search(
        self,
        query_embedding: List[float],
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[MemoryRecord, float]]:
        """Search via Synap's hybrid retrieval.

        Note: CrewAI passes query_embedding but Synap handles embeddings
        server-side. We use the recall query text stored in metadata_filter
        or fall back to a generic search.
        """
        return _run_async(self.asearch(
            query_embedding, scope_prefix, categories,
            metadata_filter, limit, min_score,
        ))

    async def asearch(
        self,
        query_embedding: List[float],
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[MemoryRecord, float]]:
        # CrewAI's Memory.recall passes the query text in metadata_filter
        # under "_query_text" key, or we fall back to generic fetch
        query_text = None
        if metadata_filter and "_query_text" in metadata_filter:
            query_text = metadata_filter.pop("_query_text")

        search_query = [query_text] if query_text else None

        # Map categories to Synap context types if possible
        types = None
        if categories:
            type_map = {
                "fact": "facts", "facts": "facts",
                "preference": "preferences", "preferences": "preferences",
                "episode": "episodes", "episodes": "episodes",
                "emotion": "emotions", "emotions": "emotions",
            }
            types = [type_map.get(c, c) for c in categories if c in type_map]
            types = types or None

        response = await self.sdk.fetch(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            customer_id=self.customer_id or None,
            search_query=search_query,
            max_results=limit,
            types=types,
            mode=self.mode,
            include_conversation_context=False,
        )

        results: List[Tuple[MemoryRecord, float]] = []
        now = datetime.now(timezone.utc)

        for fact in response.facts:
            record = MemoryRecord(
                id=fact.id,
                content=fact.content,
                scope=scope_prefix or f"/{self.user_id}",
                categories=["fact"],
                importance=fact.confidence,
                created_at=fact.extracted_at,
                last_accessed=now,
                metadata={"source": fact.source, "scope_origin": response.scope_map.get(fact.id, "")},
            )
            results.append((record, fact.confidence))

        for pref in response.preferences:
            record = MemoryRecord(
                id=pref.id,
                content=pref.content,
                scope=scope_prefix or f"/{self.user_id}",
                categories=["preference"],
                importance=pref.strength,
                created_at=pref.extracted_at,
                last_accessed=now,
                metadata={"category": pref.category, "scope_origin": response.scope_map.get(pref.id, "")},
            )
            results.append((record, pref.strength))

        for ep in response.episodes:
            record = MemoryRecord(
                id=ep.id,
                content=ep.summary,
                scope=scope_prefix or f"/{self.user_id}",
                categories=["episode"],
                importance=ep.significance,
                created_at=ep.occurred_at,
                last_accessed=now,
                metadata={"scope_origin": response.scope_map.get(ep.id, "")},
            )
            results.append((record, ep.significance))

        for em in response.emotions:
            record = MemoryRecord(
                id=em.id,
                content=f"{em.emotion_type}: {em.context}",
                scope=scope_prefix or f"/{self.user_id}",
                categories=["emotion"],
                importance=em.intensity,
                created_at=em.detected_at,
                last_accessed=now,
                metadata={"emotion_type": em.emotion_type, "scope_origin": response.scope_map.get(em.id, "")},
            )
            results.append((record, em.intensity))

        for te in response.temporal_events:
            record = MemoryRecord(
                id=te.id,
                content=te.content,
                scope=scope_prefix or f"/{self.user_id}",
                categories=["temporal_event"],
                importance=te.temporal_confidence,
                created_at=te.event_date,
                last_accessed=now,
                metadata={"valid_until": str(te.valid_until) if te.valid_until else None,
                          "scope_origin": response.scope_map.get(te.id, "")},
            )
            results.append((record, te.temporal_confidence))

        # Sort by score descending, apply min_score filter
        results = [(r, s) for r, s in results if s >= min_score]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Secondary methods (protocol compliance)
    # ------------------------------------------------------------------

    def delete(
        self,
        scope_prefix: Optional[str] = None,
        categories: Optional[List[str]] = None,
        record_ids: Optional[List[str]] = None,
        older_than: Optional[datetime] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> int:
        count = 0
        if record_ids:
            for rid in record_ids:
                self._records.pop(rid, None)
                count += 1
        elif scope_prefix:
            to_remove = [k for k, v in self._records.items() if v.scope.startswith(scope_prefix)]
            for k in to_remove:
                del self._records[k]
                count += 1
        return count

    async def adelete(self, **kwargs) -> int:
        return self.delete(**kwargs)

    def update(self, record: MemoryRecord) -> None:
        self._records[record.id] = record

    def get_record(self, record_id: str) -> Optional[MemoryRecord]:
        return self._records.get(record_id)

    def list_records(
        self,
        scope_prefix: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[MemoryRecord]:
        records = list(self._records.values())
        if scope_prefix:
            records = [r for r in records if r.scope.startswith(scope_prefix)]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[offset:offset + limit]

    def get_scope_info(self, scope: str) -> ScopeInfo:
        records = [r for r in self._records.values() if r.scope.startswith(scope)]
        cats = set()
        for r in records:
            cats.update(r.categories)
        return ScopeInfo(
            path=scope,
            record_count=len(records),
            categories=sorted(cats),
            oldest_record=min((r.created_at for r in records), default=None),
            newest_record=max((r.created_at for r in records), default=None),
            child_scopes=[],
        )

    def list_scopes(self, parent: str = "/") -> List[str]:
        scopes = set()
        for r in self._records.values():
            if r.scope.startswith(parent) and r.scope != parent:
                # Get the next level
                rest = r.scope[len(parent):]
                next_part = rest.split("/")[0]
                if next_part:
                    scopes.add(parent + next_part)
        return sorted(scopes)

    def list_categories(self, scope_prefix: Optional[str] = None) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self._records.values():
            if scope_prefix and not r.scope.startswith(scope_prefix):
                continue
            for cat in r.categories:
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    def count(self, scope_prefix: Optional[str] = None) -> int:
        if not scope_prefix:
            return len(self._records)
        return sum(1 for r in self._records.values() if r.scope.startswith(scope_prefix))

    def reset(self, scope_prefix: Optional[str] = None) -> None:
        if scope_prefix:
            to_remove = [k for k, v in self._records.items() if v.scope.startswith(scope_prefix)]
            for k in to_remove:
                del self._records[k]
        else:
            self._records.clear()
