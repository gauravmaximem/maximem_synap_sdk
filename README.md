# Synap Integrations

Framework integrations for [Synap](https://synap.ai) — persistent memory for AI agents and applications.

Each package is a thin wrapper that connects your favorite AI framework to Synap's memory system. Install the SDK + the integration for your framework, and you're ready to go.

## Quick Install

```bash
# Install the Synap SDK
pip install maximem-synap

# Install the integration for your framework
pip install synap-langchain    # LangChain / LangGraph
pip install synap-crewai       # CrewAI
pip install synap-llamaindex   # LlamaIndex
pip install synap-haystack     # Haystack
pip install synap-google-adk   # Google ADK
pip install synap-autogen      # AutoGen
pip install synap-semantic-kernel  # Semantic Kernel
pip install synap-openai-agents    # OpenAI Agents SDK
pip install synap-pydantic-ai     # Pydantic AI
```

## Packages

| Package | Framework | Surfaces |
|---|---|---|
| [synap-langchain](packages/synap-langchain/) | LangChain / LangGraph | Chat history, retriever, tools, callback handler, graph node |
| [synap-crewai](packages/synap-crewai/) | CrewAI | Storage backend (long-term, short-term, entity memory) |
| [synap-llamaindex](packages/synap-llamaindex/) | LlamaIndex | Chat memory, retriever |
| [synap-haystack](packages/synap-haystack/) | Haystack | Retriever component, memory writer component |
| [synap-google-adk](packages/synap-google-adk/) | Google ADK | Function tools |
| [synap-autogen](packages/synap-autogen/) | AutoGen | Search/store tools |
| [synap-semantic-kernel](packages/synap-semantic-kernel/) | Semantic Kernel | Plugin with kernel functions |
| [synap-openai-agents](packages/synap-openai-agents/) | OpenAI Agents SDK | Tool factories |
| [synap-pydantic-ai](packages/synap-pydantic-ai/) | Pydantic AI | Deps + tool registration |

## Usage Example (LangChain)

```python
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from maximem_synap import MaximemSynapSDK
from synap_langchain import SynapChatMessageHistory

sdk = MaximemSynapSDK(instance_id="your-instance-id")

def get_session_history(session_id: str):
    return SynapChatMessageHistory(
        sdk=sdk,
        conversation_id=session_id,
        user_id="user-123",
    )

chain = RunnableWithMessageHistory(
    ChatOpenAI(),
    get_session_history,
)

response = chain.invoke(
    "What did we discuss last time?",
    config={"configurable": {"session_id": "conv-456"}},
)
```

## Usage Example (CrewAI)

```python
from crewai import Agent, Crew, Task
from maximem_synap import MaximemSynapSDK
from synap_crewai import SynapStorageBackend

sdk = MaximemSynapSDK(instance_id="your-instance-id")
backend = SynapStorageBackend(sdk=sdk, user_id="user-123")

agent = Agent(
    role="Research Assistant",
    goal="Help the user with research",
    memory=True,
    memory_config={"storage": {"provider": backend}},
)
```

## Usage Example (Haystack)

```python
from haystack import Pipeline
from maximem_synap import MaximemSynapSDK
from synap_haystack import SynapRetriever

sdk = MaximemSynapSDK(instance_id="your-instance-id")

pipe = Pipeline()
pipe.add_component("memory", SynapRetriever(sdk=sdk, user_id="user-123"))
# ... add more components
```

## How It Works

1. **Install** the Synap SDK (`maximem-synap`) and the integration for your framework
2. **Initialize** the SDK with your instance ID
3. **Pass** the SDK to the integration class
4. **Use** your framework as normal — Synap handles memory behind the scenes

The SDK communicates with the Synap cloud service to store and retrieve memories. Each integration maps framework-specific interfaces (memory, retriever, tool, etc.) to SDK methods.

## Requirements

- Python >= 3.9 (some frameworks require 3.10+)
- A Synap account and instance ID ([sign up](https://synap.ai))

## License

Apache 2.0 — see [LICENSE](LICENSE).
