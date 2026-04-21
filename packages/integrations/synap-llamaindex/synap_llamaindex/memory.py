"""Synap chat memory for LlamaIndex.

Implements LlamaIndex's BaseMemory interface backed by Synap's
conversation context.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory.types import BaseMemory

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


class SynapChatMemory(BaseMemory):
    """LlamaIndex chat memory backed by Synap.

    Stores messages via sdk.conversation.record_message() and retrieves
    conversation history via get_context_for_prompt().

    For retrieval-augmented context (facts, preferences, etc.), use
    SynapRetriever instead.

    Example:
        memory = SynapChatMemory.from_defaults(
            sdk=sdk, conversation_id="conv-123",
            user_id="user-456", customer_id="cust-789",
        )
    """

    _sdk: MaximemSynapSDK
    _conversation_id: str
    _user_id: str
    _customer_id: str
    _messages: List[ChatMessage]

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        conversation_id: str,
        user_id: str,
        customer_id: str = "",
    ):
        self._sdk = sdk
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._customer_id = customer_id
        self._messages = []

    @classmethod
    def from_defaults(
        cls,
        sdk: Optional[MaximemSynapSDK] = None,
        conversation_id: str = "",
        user_id: str = "",
        customer_id: str = "",
        **kwargs: Any,
    ) -> "SynapChatMemory":
        if sdk is None:
            raise ValueError("sdk is required for SynapChatMemory")
        return cls(
            sdk=sdk,
            conversation_id=conversation_id,
            user_id=user_id,
            customer_id=customer_id,
        )

    def get(self, input: Optional[str] = None, **kwargs: Any) -> List[ChatMessage]:
        return _run_async(self.aget(input, **kwargs))

    async def aget(self, input: Optional[str] = None, **kwargs: Any) -> List[ChatMessage]:
        """Get conversation history from Synap.

        Fetches conversation context from Synap and converts to ChatMessage list.
        If a query input is provided, also fetches relevant cross-scope context
        and prepends it as a system message.
        """
        messages: List[ChatMessage] = []

        # Fetch cross-scope context if query provided
        if input:
            try:
                response = await self._sdk.fetch(
                    conversation_id=self._conversation_id,
                    user_id=self._user_id,
                    customer_id=self._customer_id or None,
                    search_query=[input],
                    include_conversation_context=False,
                )
                if response.formatted_context:
                    messages.append(ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=f"Relevant user context:\n{response.formatted_context}",
                    ))
            except Exception as e:
                logger.debug("SynapChatMemory: context fetch failed: %s", e)

        # Fetch conversation history
        try:
            prompt_ctx = await self._sdk.conversation.context.get_context_for_prompt(
                conversation_id=self._conversation_id,
            )
            if prompt_ctx.formatted_context:
                messages.append(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=f"Conversation history:\n{prompt_ctx.formatted_context}",
                ))
            # Add recent messages as actual chat messages
            for msg in prompt_ctx.recent_messages:
                role = MessageRole.USER if msg.role == "user" else MessageRole.ASSISTANT
                messages.append(ChatMessage(role=role, content=msg.content))
        except Exception as e:
            logger.debug("SynapChatMemory: get_context_for_prompt failed: %s", e)

        # Append any locally buffered messages not yet synced
        messages.extend(self._messages)

        return messages

    def get_all(self) -> List[ChatMessage]:
        return self.get()

    async def aget_all(self) -> List[ChatMessage]:
        return await self.aget()

    def put(self, message: ChatMessage) -> None:
        _run_async(self.aput(message))

    async def aput(self, message: ChatMessage) -> None:
        """Record a message to Synap and buffer locally."""
        self._messages.append(message)
        role = "user" if message.role == MessageRole.USER else "assistant"
        if message.role in (MessageRole.USER, MessageRole.ASSISTANT):
            try:
                await self._sdk.conversation.record_message(
                    conversation_id=self._conversation_id,
                    role=role,
                    content=str(message.content),
                    user_id=self._user_id,
                    customer_id=self._customer_id,
                )
            except Exception as e:
                logger.warning("SynapChatMemory: record_message failed: %s", e)

    def set(self, messages: List[ChatMessage]) -> None:
        self._messages = list(messages)

    async def aset(self, messages: List[ChatMessage]) -> None:
        self._messages = list(messages)

    def reset(self) -> None:
        self._messages.clear()

    async def areset(self) -> None:
        self._messages.clear()
