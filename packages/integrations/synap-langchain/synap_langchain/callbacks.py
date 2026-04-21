"""Synap callback handler for zero-config auto-memory.

Add SynapCallbackHandler to any LangChain chain or agent. Every
conversation turn is automatically recorded to Synap for automatic
memory extraction.

No explicit save_context() calls needed.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


class SynapCallbackHandler(AsyncCallbackHandler):
    """Auto-records all conversation turns to Synap.

    Listens for chat model start (to capture user messages) and
    LLM end (to capture assistant responses). Messages are recorded
    asynchronously and any failures are logged but never raised,
    so the handler never interrupts the chain.

    Example:
        handler = SynapCallbackHandler(
            sdk=sdk,
            conversation_id="conv-123",
            user_id="user-456",
            customer_id="cust-789",
        )
        chain = ConversationChain(
            llm=ChatOpenAI(),
            callbacks=[handler],
        )
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

    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record the user message when a chat model starts."""
        # messages is a list of message batches; take the last batch
        if not messages:
            return
        last_batch = messages[-1]
        # Find the last human message in the batch
        for msg in reversed(last_batch):
            if msg.type == "human":
                try:
                    await self.sdk.conversation.record_message(
                        conversation_id=self.conversation_id,
                        role="user",
                        content=str(msg.content),
                        user_id=self.user_id,
                        customer_id=self.customer_id,
                    )
                except Exception as e:
                    logger.debug("SynapCallbackHandler: failed to record user message: %s", e)
                break

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Record the assistant response when the LLM finishes."""
        if not response.generations or not response.generations[0]:
            return
        text = response.generations[0][0].text
        if not text:
            # Try message content for chat models
            gen = response.generations[0][0]
            if hasattr(gen, "message") and hasattr(gen.message, "content"):
                text = str(gen.message.content)
        if text:
            try:
                await self.sdk.conversation.record_message(
                    conversation_id=self.conversation_id,
                    role="assistant",
                    content=text,
                    user_id=self.user_id,
                    customer_id=self.customer_id,
                )
            except Exception as e:
                logger.debug("SynapCallbackHandler: failed to record assistant message: %s", e)
