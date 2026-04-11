"""Synap tools for AutoGen agents.

Provides BaseTool implementations for memory search and storage
that work with AutoGen's tool calling interface.
"""

import logging
from typing import Optional

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


class SearchMemoryArgs(BaseModel):
    query: str = Field(description="Natural language search query for user memory")


class SearchMemoryResult(BaseModel):
    context: str = Field(description="Formatted memory context")


class StoreMemoryArgs(BaseModel):
    content: str = Field(description="Information to remember about the user")


class StoreMemoryResult(BaseModel):
    ingestion_id: str = Field(description="ID of the ingestion job")
    message: str = Field(description="Confirmation message")


class SynapSearchTool(BaseTool[SearchMemoryArgs, SearchMemoryResult]):
    """AutoGen tool for searching Synap memory."""

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        user_id: str,
        customer_id: str = "",
        conversation_id: Optional[str] = None,
        mode: str = "accurate",
    ):
        super().__init__(
            args_type=SearchMemoryArgs,
            return_type=SearchMemoryResult,
            name="search_memory",
            description=(
                "Search the user's memory for relevant context. Use when you need "
                "to recall past conversations, preferences, or facts about the user."
            ),
        )
        self._sdk = sdk
        self._user_id = user_id
        self._customer_id = customer_id
        self._conversation_id = conversation_id
        self._mode = mode

    async def run(
        self, args: SearchMemoryArgs, cancellation_token: CancellationToken
    ) -> SearchMemoryResult:
        response = await self._sdk.fetch(
            conversation_id=self._conversation_id,
            user_id=self._user_id,
            customer_id=self._customer_id or None,
            search_query=[args.query],
            mode=self._mode,
            include_conversation_context=False,
        )
        return SearchMemoryResult(
            context=response.formatted_context or "No relevant memories found."
        )


class SynapStoreTool(BaseTool[StoreMemoryArgs, StoreMemoryResult]):
    """AutoGen tool for storing information in Synap memory."""

    def __init__(
        self,
        sdk: MaximemSynapSDK,
        user_id: str,
        customer_id: str = "",
    ):
        super().__init__(
            args_type=StoreMemoryArgs,
            return_type=StoreMemoryResult,
            name="store_memory",
            description=(
                "Store an important fact, preference, or event about the user "
                "for future reference."
            ),
        )
        self._sdk = sdk
        self._user_id = user_id
        self._customer_id = customer_id

    async def run(
        self, args: StoreMemoryArgs, cancellation_token: CancellationToken
    ) -> StoreMemoryResult:
        result = await self._sdk.memories.create(
            document=args.content,
            user_id=self._user_id,
            customer_id=self._customer_id,
        )
        return StoreMemoryResult(
            ingestion_id=result.ingestion_id,
            message=f"Memory stored (ingestion_id: {result.ingestion_id})",
        )
