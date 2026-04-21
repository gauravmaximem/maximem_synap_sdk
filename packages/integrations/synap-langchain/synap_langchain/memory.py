"""Synap chat message history for LangChain.

Implements LangChain's BaseChatMessageHistory interface backed by Synap.
Use with RunnableWithMessageHistory to add memory to any chain or agent.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from sync context, handling event loop edge cases."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import nest_asyncio
    nest_asyncio.apply()
    return loop.run_until_complete(coro)


class SynapChatMessageHistory(BaseChatMessageHistory):
    """LangChain chat message history backed by Synap.

    Records conversation messages via the SDK and retrieves them
    using get_context_for_prompt(). Use with RunnableWithMessageHistory
    for automatic memory on every turn.

    Example:
        from synap_langchain import SynapChatMessageHistory
        from langchain_core.runnables.history import RunnableWithMessageHistory

        def get_session_history(session_id: str) -> SynapChatMessageHistory:
            return SynapChatMessageHistory(
                sdk=sdk,
                conversation_id=session_id,
                user_id="user-456",
                customer_id="cust-789",
            )

        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
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

    @classmethod
    def from_instance(
        cls,
        instance_id: str,
        conversation_id: str,
        user_id: str,
        customer_id: str = "",
    ) -> "SynapChatMessageHistory":
        """Create from an instance ID. Initializes the SDK automatically."""
        sdk = MaximemSynapSDK(instance_id=instance_id)
        return cls(
            sdk=sdk,
            conversation_id=conversation_id,
            user_id=user_id,
            customer_id=customer_id,
        )

    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from Synap."""
        return _run_async(self.aget_messages())

    async def aget_messages(self) -> List[BaseMessage]:
        """Async retrieve messages from Synap."""
        msgs: List[BaseMessage] = []
        try:
            prompt_ctx = await self.sdk.conversation.context.get_context_for_prompt(
                conversation_id=self.conversation_id,
            )
            if prompt_ctx and prompt_ctx.recent_messages:
                for rm in prompt_ctx.recent_messages:
                    role = getattr(rm, "role", None) or "user"
                    content = getattr(rm, "content", "") or ""
                    if role == "assistant":
                        msgs.append(AIMessage(content=str(content)))
                    else:
                        msgs.append(HumanMessage(content=str(content)))
        except Exception as e:
            logger.debug("SynapChatMessageHistory: failed to get messages: %s", e)
        return msgs

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Add messages to Synap."""
        _run_async(self.aadd_messages(messages))

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Async add messages to Synap."""
        for msg in messages:
            role = "assistant" if isinstance(msg, AIMessage) else "user"
            try:
                await self.sdk.conversation.record_message(
                    conversation_id=self.conversation_id,
                    role=role,
                    content=str(msg.content),
                    user_id=self.user_id,
                    customer_id=self.customer_id,
                )
            except Exception as e:
                logger.warning("Failed to record %s message: %s", role, e)

    def clear(self) -> None:
        """Clear local cache."""
        self.sdk.cache.clear()

    async def aclear(self) -> None:
        """Async clear local cache."""
        self.sdk.cache.clear()


# Backward-compatible alias
SynapMemory = SynapChatMessageHistory
