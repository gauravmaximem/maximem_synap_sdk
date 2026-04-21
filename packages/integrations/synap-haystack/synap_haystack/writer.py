"""Synap memory writer component for Haystack pipelines.

Records conversation messages to Synap for server-side extraction.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from haystack import Document, component

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import nest_asyncio
    nest_asyncio.apply()
    return loop.run_until_complete(coro)


@component
class SynapMemoryWriter:
    """Haystack component that writes conversation turns to Synap.

    Accepts Documents where content is the message text and
    meta["role"] is "user" or "assistant".

    Example:
        writer = SynapMemoryWriter(sdk=sdk, conversation_id="c1", user_id="u1")
        pipeline.add_component("memory_writer", writer)
    """

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        conversation_id: str,
        user_id: str,
        customer_id: str = "",
    ):
        self.sdk = sdk
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.customer_id = customer_id

    @component.output_types(written_count=int)
    def run(self, documents: List[Document]) -> Dict[str, int]:
        return _run_async(self._arun(documents))

    async def _arun(self, documents: List[Document]) -> Dict[str, int]:
        count = 0
        for doc in documents:
            role = doc.meta.get("role", "user")
            if role not in ("user", "assistant"):
                continue
            try:
                await self.sdk.conversation.record_message(
                    conversation_id=self.conversation_id,
                    role=role,
                    content=doc.content,
                    user_id=self.user_id,
                    customer_id=self.customer_id,
                )
                count += 1
            except Exception as e:
                logger.warning("SynapMemoryWriter: failed to record message: %s", e)
        return {"written_count": count}
