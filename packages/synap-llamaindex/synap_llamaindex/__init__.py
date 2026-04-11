"""Synap memory integration for LlamaIndex.

Provides:
- SynapRetriever: Memory-augmented retriever returning NodeWithScore
- SynapChatMemory: Chat memory backed by Synap conversation context
"""

from synap_llamaindex.retriever import SynapRetriever
from synap_llamaindex.memory import SynapChatMemory

__all__ = ["SynapRetriever", "SynapChatMemory"]
