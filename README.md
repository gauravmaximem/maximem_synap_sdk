<p align="center">
  <a href="https://www.maximem.ai">
    <img src="https://www.maximem.ai/logo-fullmark.svg" alt="Synap by Maximem AI" width="360" />
  </a>
</p>

<p align="center">
  <strong>The memory layer for production AI applications.</strong>
</p>

<p align="center">
  <a href="https://www.maximem.ai/docs">Docs</a> ·
  <a href="https://www.maximem.ai/docs/quickstart">Quickstart</a> ·
  <a href="https://dashboard.maximem.ai">Dashboard</a> ·
  <a href="https://www.maximem.ai/blog/synap-benchmark-results">Benchmarks</a> ·
  <a href="https://www.maximem.ai">maximem.ai</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/maximem-synap"><img src="https://img.shields.io/pypi/v/maximem-synap?style=flat-square&color=blue" alt="PyPI" /></a>
  <a href="https://pypi.org/project/maximem-synap"><img src="https://img.shields.io/pypi/dm/maximem-synap?style=flat-square" alt="PyPI Downloads" /></a>
  <a href="https://www.npmjs.com/package/@maximem/synap-js-sdk"><img src="https://img.shields.io/npm/v/@maximem/synap-js-sdk?style=flat-square&color=blue" alt="npm" /></a>
  <a href="https://pypi.org/project/maximem-synap"><img src="https://img.shields.io/pypi/pyversions/maximem-synap?style=flat-square" alt="Python versions" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License" /></a>
</p>

---

## #1 on LongMemEval

Synap leads every major AI memory benchmark — tested across all systems on identical hardware with reproducible, open-source evaluation.

| System | LongMemEval | Notes |
|---|---|---|
| **Synap** | **90.2%** | Evaluated with [open-source harness](https://github.com/gauravmaximem/maximem_synap_eval) |
| SuperMemory | 71.3% | |
| Zep | 63.8% | Not independently verified |
| Mem0 | 57.5% | |

**"Longer conversations make Synap better, not worse"** — richer entity graphs and stronger pattern recognition at scale. Full methodology and reproducibility instructions: [maximem.ai/blog/synap-benchmark-results](https://www.maximem.ai/blog/synap-benchmark-results)

---

## What is Synap

Your AI agents forget everything between conversations. Synap fixes that — with scoped, typed, persistent memory built for applications that serve real users at scale.

Most memory systems are designed for one user talking to one agent. Synap is designed for **production multi-tenant AI applications**: each of your customers has their own users, each user has their own memory, and every fetch runs in parallel across all relevant scopes in a single call.

```
client scope        → shared knowledge across your entire platform
  └── customer scope  → per-company context (B2B use case)
        └── user scope  → per-user memory, facts, preferences, episodes
              └── conversation scope  → in-session history and context
```

Works natively with the framework your team already uses:

<p align="center">
  <strong>LangChain · LlamaIndex · CrewAI · Haystack · Google ADK · AutoGen · OpenAI Agents · Semantic Kernel · Pydantic AI</strong>
</p>

---

## Install

```bash
# Python SDK
pip install maximem-synap

# JavaScript / TypeScript SDK
npm install @maximem/synap-js-sdk
```

---

## 60-second demo

```python
import asyncio
from maximem_synap import MaximemSynapSDK

sdk = MaximemSynapSDK(api_key="your-api-key")

async def main():
    await sdk.initialize()

    # Record a conversation turn
    await sdk.conversation.record_message(
        conversation_id="conv-001",
        user_id="alice",
        role="user",
        content="I'm migrating our auth to OAuth2 this sprint.",
    )

    # Later — fetch everything relevant in one call
    # Merges conversation, user, and customer context in parallel
    context = await sdk.fetch(
        conversation_id="conv-002",
        user_id="alice",
        customer_id="acme-corp",
        search_query=["current engineering work"],
    )

    print(context.formatted_context)
    # → "Alice is migrating auth to OAuth2 this sprint.
    #    Acme Corp uses AWS and runs on Python 3.12.
    #    Previous conversation covered deployment pipeline."

asyncio.run(main())
```

```javascript
const { createClient } = require('@maximem/synap-js-sdk');

const client = createClient({ apiKey: 'your-api-key' });
await client.init();

const context = await client.fetchUserContext({
    userId: 'alice',
    query: 'current engineering work',
});

console.log(context.formattedContext);
```

---

## Framework integrations

Nine installable packages — not code snippets, actual PyPI packages with deep framework surfaces.

### LangChain

```bash
pip install maximem-synap synap-langchain
```

```python
from maximem_synap import MaximemSynapSDK
from synap_langchain import SynapChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory

sdk = MaximemSynapSDK(api_key="your-api-key")
await sdk.initialize()

chain = RunnableWithMessageHistory(
    ChatOpenAI(),
    lambda session_id: SynapChatMessageHistory(sdk=sdk, conversation_id=session_id, user_id="alice"),
)

response = chain.invoke(
    "What were we working on last time?",
    config={"configurable": {"session_id": "conv-002"}},
)
```

### CrewAI

```bash
pip install maximem-synap synap-crewai
```

```python
from synap_crewai import SynapStorageBackend

crew = Crew(agents=[...], tasks=[...], memory=True,
            storage=SynapStorageBackend(sdk=sdk, user_id="alice"))
```

### LlamaIndex

```bash
pip install maximem-synap synap-llamaindex
```

```python
from synap_llamaindex import SynapChatMemory

memory = SynapChatMemory(sdk=sdk, user_id="alice")
agent = ReActAgent.from_tools(tools, memory=memory)
```

### All integrations

| Package | Framework | Install |
|---|---|---|
| [synap-langchain](packages/integrations/synap-langchain/) | LangChain / LangGraph | `pip install synap-langchain` |
| [synap-llamaindex](packages/integrations/synap-llamaindex/) | LlamaIndex | `pip install synap-llamaindex` |
| [synap-crewai](packages/integrations/synap-crewai/) | CrewAI | `pip install synap-crewai` |
| [synap-haystack](packages/integrations/synap-haystack/) | Haystack | `pip install synap-haystack` |
| [synap-google-adk](packages/integrations/synap-google-adk/) | Google ADK | `pip install synap-google-adk` |
| [synap-autogen](packages/integrations/synap-autogen/) | AutoGen | `pip install synap-autogen` |
| [synap-openai-agents](packages/integrations/synap-openai-agents/) | OpenAI Agents SDK | `pip install synap-openai-agents` |
| [synap-semantic-kernel](packages/integrations/synap-semantic-kernel/) | Semantic Kernel | `pip install synap-semantic-kernel` |
| [synap-pydantic-ai](packages/integrations/synap-pydantic-ai/) | Pydantic AI | `pip install synap-pydantic-ai` |

---

## Why Synap

| | Naive vector store | Single-user memory (Mem0, Zep) | **Synap** |
|---|---|---|---|
| **Multi-tenant scoping** | Manual | Single `user_id` | `user → customer → client` hierarchy |
| **Memory types** | Raw chunks | Unstructured | Facts, episodes, preferences, emotions, temporal events |
| **Retrieval latency** | 100–500ms | 50–200ms | Sub-10ms on cache hit (anticipation cache) |
| **Framework depth** | DIY | Code snippets | 9 installable packages with deep surfaces |
| **Conversation scope** | Not included | Separate system | Unified fetch across all scopes in one call |
| **Production readiness** | You build it | Hosted only or self-host | Both; B2B multi-tenant by design |

### Anticipation cache

Synap pre-fetches context before users ask for it. When your agent handles a conversation turn, Synap asynchronously prepares the next context fetch in the background. Cache hits return in **under 10ms**. No waiting for vector search on the hot path.

### Typed memory

Memory isn't just text chunks. Synap extracts and stores structured types:

- **Facts** — `Alice is a senior engineer at Acme Corp`
- **Preferences** — `Prefers TypeScript over JavaScript`
- **Episodes** — `Completed OAuth2 migration on 2026-03-15`
- **Temporal events** — `Sprint ends Friday`
- **Emotions** — signals for tone and personalization

Query by type, combine types, or fetch everything — your call.

---

## Benchmarks & evaluation

Full benchmark results, methodology, and reproducibility instructions:
→ [maximem.ai/blog/synap-benchmark-results](https://www.maximem.ai/blog/synap-benchmark-results)

The complete evaluation harness is open source:
→ [github.com/gauravmaximem/maximem_synap_eval](https://github.com/gauravmaximem/maximem_synap_eval)

We're building **ACM-Bench** — ten realistic agent scenarios covering consistency, false recall rates, and context rot resistance. Targeting May 2026.

---

## Requirements

- **Python SDK**: Python 3.9+
- **JavaScript SDK**: Node 18+ (Python 3.9+ for the bridge layer)
- A Synap API key — [get one at maximem.ai](https://www.maximem.ai)

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the fork-first workflow, branch conventions, and how to add a new framework integration.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  Built by <a href="https://www.maximem.ai"><strong>Maximem AI</strong></a>
</p>
