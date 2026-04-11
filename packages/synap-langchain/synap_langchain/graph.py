"""Synap LangGraph integration.

Provides a node factory for injecting Synap memory context into
LangGraph state before the LLM node processes it.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from maximem_synap import MaximemSynapSDK

logger = logging.getLogger(__name__)


def create_synap_node(
    sdk: MaximemSynapSDK,
    user_id: str,
    customer_id: str = "",
    conversation_id: Optional[str] = None,
    state_key: str = "synap_context",
    messages_key: str = "messages",
    mode: str = "fast",
    max_results: int = 20,
    include_scope_labels: bool = False,
) -> Callable:
    """Create a LangGraph node that injects Synap context into state.

    Place this node before the LLM node in your graph. It reads the
    latest user message from state, fetches relevant memory context
    from Synap, and writes it into state[state_key].

    Args:
        sdk: Initialized MaximemSynapSDK instance.
        user_id: User identifier.
        customer_id: Customer identifier (for B2B instances).
        conversation_id: Conversation identifier. If None, looks for
                         "conversation_id" in state.
        state_key: Key in state where context will be written.
        messages_key: Key in state where messages list is stored.
        mode: Retrieval mode ("fast" or "accurate").
        max_results: Maximum results per scope.
        include_scope_labels: Annotate items with their source scope.

    Returns:
        An async function suitable for use as a LangGraph node.

    Example:
        from langgraph.graph import StateGraph, START, END

        graph = StateGraph(MyState)
        graph.add_node("memory", create_synap_node(sdk, user_id="u1"))
        graph.add_node("llm", llm_node)
        graph.add_edge(START, "memory")
        graph.add_edge("memory", "llm")
        graph.add_edge("llm", END)
        app = graph.compile()
    """

    async def synap_memory_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # Resolve conversation_id from parameter or state
        conv_id = conversation_id or state.get("conversation_id")

        # Extract search query from the latest user message
        query = None
        messages = state.get(messages_key, [])
        for msg in reversed(messages):
            # Support both LangChain message objects and plain dicts
            if hasattr(msg, "type") and msg.type == "human":
                query = [str(msg.content)]
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                query = [str(msg.get("content", ""))]
                break

        response = await sdk.fetch(
            conversation_id=conv_id,
            user_id=user_id,
            customer_id=customer_id or None,
            search_query=query,
            max_results=max_results,
            mode=mode,
            include_scope_labels=include_scope_labels,
        )

        return {state_key: response.formatted_context or ""}

    # Set __name__ so LangGraph uses it as the default node name
    synap_memory_node.__name__ = "synap_memory"

    return synap_memory_node
