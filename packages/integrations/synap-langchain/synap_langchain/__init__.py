"""Synap memory integration for LangChain and LangGraph.

Provides five integration surfaces:
- SynapChatMessageHistory: BaseChatMessageHistory for use with RunnableWithMessageHistory
- SynapRetriever: BaseRetriever for RAG pipelines with typed memory items
- SynapSearchTool / SynapStoreTool: Agent tools for explicit memory access
- SynapCallbackHandler: Zero-config auto-recording of conversation turns
- create_synap_node: LangGraph node for state injection
"""

from synap_langchain.memory import SynapChatMessageHistory, SynapMemory
from synap_langchain.retriever import SynapRetriever
from synap_langchain.tools import SynapSearchTool, SynapStoreTool
from synap_langchain.callbacks import SynapCallbackHandler
from synap_langchain.graph import create_synap_node

__all__ = [
    "SynapChatMessageHistory",
    "SynapMemory",  # backward-compatible alias
    "SynapRetriever",
    "SynapSearchTool",
    "SynapStoreTool",
    "SynapCallbackHandler",
    "create_synap_node",
]
