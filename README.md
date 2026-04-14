# Synap SDK & Integrations

Persistent memory for AI agents and applications. This repo contains the official [Synap](https://synap.ai) SDKs for Python and JavaScript, plus thin framework integrations for the most popular AI frameworks.

## Packages

### SDKs

| Package | Language | Install |
|---|---|---|
| [maximem-synap](packages/maximem-synap/) | Python | `pip install maximem-synap` |
| [@maximem/synap-js-sdk](packages/maximem-synap-js/) | JavaScript / TypeScript | `npm install @maximem/synap-js-sdk` |

### Framework integrations (Python)

| Package | Framework | Surfaces |
|---|---|---|
| [synap-langchain](packages/synap-langchain/) | LangChain / LangGraph | Chat history, retriever, tools, callback handler, graph node |
| [synap-crewai](packages/synap-crewai/) | CrewAI | Storage backend |
| [synap-llamaindex](packages/synap-llamaindex/) | LlamaIndex | Chat memory, retriever |
| [synap-haystack](packages/synap-haystack/) | Haystack | Retriever component, memory writer component |
| [synap-google-adk](packages/synap-google-adk/) | Google ADK | Function tools |
| [synap-autogen](packages/synap-autogen/) | AutoGen | Search/store tools |
| [synap-semantic-kernel](packages/synap-semantic-kernel/) | Semantic Kernel | Plugin with kernel functions |
| [synap-openai-agents](packages/synap-openai-agents/) | OpenAI Agents SDK | Tool factories |
| [synap-pydantic-ai](packages/synap-pydantic-ai/) | Pydantic AI | Deps + tool registration |

## Quick start (Python)

```bash
pip install maximem-synap
```

```python
from maximem_synap import MaximemSynapSDK

sdk = MaximemSynapSDK(instance_id="your-instance-id")
await sdk.initialize(bootstrap_token="your-bootstrap-token")

# Unified cross-scope fetch
response = await sdk.fetch(
    conversation_id="conv-123",
    user_id="user-456",
    search_query=["what the user is asking"],
)

print(response.formatted_context)
```

## Quick start (JavaScript)

```bash
npm install @maximem/synap-js-sdk
npx synap-js-sdk setup
```

```javascript
const { createClient } = require('@maximem/synap-js-sdk');

const client = createClient({
    instanceId: 'your-instance-id',
    bootstrapToken: 'your-bootstrap-token',
});

await client.init();

const response = await client.fetchUserContext({
    userId: 'user-456',
    query: 'what the user is asking',
});

console.log(response.formattedContext);
```

## Quick start with LangChain

```bash
pip install maximem-synap synap-langchain
```

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

chain = RunnableWithMessageHistory(ChatOpenAI(), get_session_history)

response = chain.invoke(
    "What did we discuss last time?",
    config={"configurable": {"session_id": "conv-456"}},
)
```

## Features

- **Unified cross-scope fetch** — one call merges context from conversation, user, customer, and client scopes.
- **Typed memory items** — facts, preferences, episodes, emotions, temporal events.
- **Automatic conversation recording** — `record_message()` handles ingestion server-side.
- **In-memory anticipation cache** — sub-10ms cache hits when the server has pre-fetched relevant context.
- **Multiple retrieval modes** — `FAST` for interactive flows, `ACCURATE` for RAG pipelines.
- **9 framework integrations** — thin wrappers so your existing code just works.

## Repository structure

```
maximem_synap_sdk/
├── packages/
│   ├── maximem-synap/          # Python SDK
│   ├── maximem-synap-js/       # JavaScript SDK
│   ├── synap-langchain/        # LangChain integration
│   ├── synap-crewai/           # CrewAI integration
│   ├── synap-llamaindex/       # LlamaIndex integration
│   ├── synap-haystack/         # Haystack integration
│   ├── synap-google-adk/       # Google ADK integration
│   ├── synap-autogen/          # AutoGen integration
│   ├── synap-semantic-kernel/  # Semantic Kernel integration
│   ├── synap-openai-agents/    # OpenAI Agents integration
│   └── synap-pydantic-ai/      # Pydantic AI integration
├── .github/workflows/          # CI and publishing workflows
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Requirements

- **Python SDK**: Python 3.9+
- **JavaScript SDK**: Node 18+ (plus Python 3.9+ for the Python bridge)
- A Synap account and instance ID ([sign up](https://synap.ai))

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for the fork-first workflow, branch naming conventions, and how to add a new framework integration.

## License

Apache 2.0 — see [LICENSE](LICENSE).
