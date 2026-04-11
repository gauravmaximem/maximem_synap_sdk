"""Synap retriever for LlamaIndex RAG pipelines.

Maps Synap's typed memory items to LlamaIndex NodeWithScore objects,
enabling memory-augmented retrieval in any LlamaIndex pipeline.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


class SynapRetriever(BaseRetriever):
    """LlamaIndex retriever backed by Synap memory.

    Each memory item (fact, preference, episode, etc.) becomes a
    TextNode with metadata preserving type, confidence, and scope.

    Example:
        retriever = SynapRetriever(sdk=sdk, user_id="user-456")
        nodes = retriever.retrieve("What does the user prefer?")
    """

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        user_id: str,
        customer_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        mode: str = "accurate",
        max_results: int = 20,
        types: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._sdk = sdk
        self._user_id = user_id
        self._customer_id = customer_id
        self._conversation_id = conversation_id
        self._mode = mode
        self._max_results = max_results
        self._types = types

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._aretrieve(query_bundle))
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(self._aretrieve(query_bundle))

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        response = await self._sdk.fetch(
            conversation_id=self._conversation_id,
            user_id=self._user_id,
            customer_id=self._customer_id,
            search_query=[query_bundle.query_str],
            max_results=self._max_results,
            types=self._types,
            mode=self._mode,
            include_conversation_context=False,
        )

        nodes: List[NodeWithScore] = []

        for fact in response.facts:
            node = TextNode(
                text=fact.content,
                id_=fact.id,
                metadata={
                    "type": "fact",
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "scope": response.scope_map.get(fact.id, ""),
                    "temporal_category": fact.temporal_category,
                },
            )
            nodes.append(NodeWithScore(node=node, score=fact.confidence))

        for pref in response.preferences:
            node = TextNode(
                text=pref.content,
                id_=pref.id,
                metadata={
                    "type": "preference",
                    "strength": pref.strength,
                    "category": pref.category,
                    "scope": response.scope_map.get(pref.id, ""),
                },
            )
            nodes.append(NodeWithScore(node=node, score=pref.strength))

        for ep in response.episodes:
            node = TextNode(
                text=ep.summary,
                id_=ep.id,
                metadata={
                    "type": "episode",
                    "significance": ep.significance,
                    "occurred_at": str(ep.occurred_at),
                    "scope": response.scope_map.get(ep.id, ""),
                },
            )
            nodes.append(NodeWithScore(node=node, score=ep.significance))

        for em in response.emotions:
            node = TextNode(
                text=f"{em.emotion_type}: {em.context}",
                id_=em.id,
                metadata={
                    "type": "emotion",
                    "emotion_type": em.emotion_type,
                    "intensity": em.intensity,
                    "scope": response.scope_map.get(em.id, ""),
                },
            )
            nodes.append(NodeWithScore(node=node, score=em.intensity))

        for te in response.temporal_events:
            node = TextNode(
                text=te.content,
                id_=te.id,
                metadata={
                    "type": "temporal_event",
                    "event_date": str(te.event_date),
                    "valid_until": str(te.valid_until) if te.valid_until else None,
                    "scope": response.scope_map.get(te.id, ""),
                },
            )
            nodes.append(NodeWithScore(node=node, score=te.temporal_confidence))

        # Sort by score descending
        nodes.sort(key=lambda n: n.score or 0, reverse=True)
        return nodes
