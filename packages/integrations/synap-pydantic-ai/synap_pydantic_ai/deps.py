"""Synap dependency and tool helpers for Pydantic AI.

Provides SynapDeps (a dependency class) and helper functions for
registering Synap memory tools on a Pydantic AI Agent.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


@dataclass
class SynapDeps:
    """Pydantic AI dependency holding Synap SDK and scope identifiers.

    Pass as deps_type to your Agent, then access in tools and system prompts.

    Example:
        from pydantic_ai import Agent, RunContext
        from synap_pydantic_ai import SynapDeps, register_synap_tools

        agent = Agent('openai:gpt-4o', deps_type=SynapDeps)
        register_synap_tools(agent)

        result = agent.run_sync(
            "What do you know about me?",
            deps=SynapDeps(sdk=sdk, user_id="u1", customer_id="c1"),
        )
    """

    sdk: MaximemSynapSDK
    user_id: str
    customer_id: str = ""
    conversation_id: Optional[str] = None


def register_synap_tools(agent) -> None:
    """Register search_memory and store_memory tools on a Pydantic AI Agent.

    Also registers a system prompt that auto-injects memory context.

    Args:
        agent: A pydantic_ai.Agent instance with deps_type=SynapDeps.
    """
    from pydantic_ai import RunContext

    @agent.tool
    async def search_memory(ctx: RunContext[SynapDeps], query: str) -> str:
        """Search the user's memory for relevant context.

        Args:
            ctx: Run context with SynapDeps.
            query: Natural language search query.

        Returns:
            Formatted context from memory.
        """
        deps = ctx.deps
        response = await deps.sdk.fetch(
            conversation_id=deps.conversation_id,
            user_id=deps.user_id,
            customer_id=deps.customer_id or None,
            search_query=[query],
            mode="accurate",
            include_conversation_context=False,
        )
        return response.formatted_context or "No relevant memories found."

    @agent.tool
    async def store_memory(ctx: RunContext[SynapDeps], content: str) -> str:
        """Store important information about the user for future reference.

        Args:
            ctx: Run context with SynapDeps.
            content: Information to remember.

        Returns:
            Confirmation message.
        """
        deps = ctx.deps
        result = await deps.sdk.memories.create(
            document=content,
            user_id=deps.user_id,
            customer_id=deps.customer_id,
        )
        return f"Memory stored (ingestion_id: {result.ingestion_id})"

    @agent.system_prompt
    async def inject_memory_context(ctx: RunContext[SynapDeps]) -> str:
        """Auto-inject memory context into the system prompt."""
        deps = ctx.deps
        try:
            response = await deps.sdk.fetch(
                conversation_id=deps.conversation_id,
                user_id=deps.user_id,
                customer_id=deps.customer_id or None,
            )
            if response.formatted_context:
                return f"Relevant user context:\n{response.formatted_context}"
        except Exception as e:
            logger.debug("Synap system prompt injection failed: %s", e)
        return ""
