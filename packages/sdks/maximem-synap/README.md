# maximem-synap

Python SDK for [Synap](https://synap.ai) — persistent memory for AI agents and applications.

## Install

```bash
pip install maximem-synap
```

## Quick start

```python
from maximem_synap import MaximemSynapSDK

sdk = MaximemSynapSDK(instance_id="your-instance-id")
await sdk.initialize(bootstrap_token="your-bootstrap-token")

# Fetch context across all scopes
response = await sdk.fetch(
    conversation_id="conv-123",
    user_id="user-456",
    search_query=["what the user is asking"],
)

print(response.formatted_context)

# Record a conversation turn
await sdk.conversation.record_message(
    conversation_id="conv-123",
    role="user",
    content="hello",
    user_id="user-456",
    customer_id="cust-789",
)

# Create a memory
result = await sdk.memories.create(
    document="User prefers dark mode",
    user_id="user-456",
    customer_id="cust-789",
)
```

## Features

- **Unified cross-scope fetch** — one call merges context from conversation, user, customer, and client scopes.
- **Typed memory items** — facts, preferences, episodes, emotions, temporal events. Not flat text blobs.
- **Automatic conversation recording** — `record_message()` handles ingestion; compaction runs server-side.
- **In-memory anticipation cache** — sub-10ms cache hits when the server has pre-fetched relevant context.
- **Multi-tier caching** — anticipation cache + local HTTP cache (SQLite) + cloud.
- **Multiple retrieval modes** — `FAST` for interactive flows, `ACCURATE` for RAG pipelines.
- **Compaction** — async conversation compression that serves previous context while a new one is being computed.

## Configuration

```python
from maximem_synap import MaximemSynapSDK, SDKConfig

config = SDKConfig(
    api_base_url="https://synap-cloud-prod.maximem.ai",
    cache_backend="sqlite",
    log_level="INFO",
)

sdk = MaximemSynapSDK(instance_id="your-instance-id", config=config)
```

Or via environment variables:

```bash
export SYNAP_INSTANCE_ID="your-instance-id"
export SYNAP_BOOTSTRAP_TOKEN="your-bootstrap-token"
```

## Authentication

Set your API key from the Synap dashboard:

```bash
export SYNAP_API_KEY=synap_your_key_here
```

Or pass it directly:

```python
sdk = MaximemSynapSDK(instance_id="...", api_key="synap_...")
```

For local development, the SDK stores credentials in `~/.synap/instances/{instance_id}/credentials.json` with `0600` file permissions. **Do not commit this file to version control.**

## Framework integrations

Use Synap with your favorite AI framework via the companion integration packages:

```bash
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

## License

Apache 2.0 — see [LICENSE](../../LICENSE).
