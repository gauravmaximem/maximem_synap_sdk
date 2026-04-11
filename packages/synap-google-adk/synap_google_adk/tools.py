"""Synap tools for Google ADK agents.

Provides search_memory and store_memory as ADK FunctionTools.
"""

import asyncio
import logging
from typing import Optional

from google.adk.tools import FunctionTool

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


def create_synap_tools(
    sdk: MaximemSynapSDK,
    user_id: str,
    customer_id: str = "",
    conversation_id: Optional[str] = None,
) -> list:
    """Create ADK FunctionTools for Synap memory operations.

    Returns:
        List of [search_memory, store_memory] FunctionTool instances.

    Example:
        tools = create_synap_tools(sdk, user_id="u1")
        agent = Agent(model=model, tools=tools)
    """

    async def search_memory(query: str) -> str:
        """Search the user's memory for relevant context.

        Args:
            query: Natural language search query.

        Returns:
            Formatted context from memory.
        """
        response = await sdk.fetch(
            conversation_id=conversation_id,
            user_id=user_id,
            customer_id=customer_id or None,
            search_query=[query],
            mode="accurate",
            include_conversation_context=False,
        )
        return response.formatted_context or "No relevant memories found."

    async def store_memory(content: str) -> str:
        """Store important information about the user.

        Args:
            content: Information to remember.

        Returns:
            Confirmation message.
        """
        result = await sdk.memories.create(
            document=content,
            user_id=user_id,
            customer_id=customer_id,
        )
        return f"Memory stored (ingestion_id: {result.ingestion_id})"

    return [
        FunctionTool(search_memory),
        FunctionTool(store_memory),
    ]
