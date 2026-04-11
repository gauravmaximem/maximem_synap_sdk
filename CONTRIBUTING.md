# Contributing to Synap Integrations

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### 1. Fork the Repository

Click the **Fork** button at the top-right of this repo to create your own copy.

Then clone your fork locally:

```bash
git clone https://github.com/<your-username>/maximem_synap_sdk.git
cd maximem_synap_sdk
```

### 2. Set Up Your Development Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the Synap SDK
pip install maximem-synap

# Install the package you want to work on (e.g. synap-langchain)
cd packages/synap-langchain
pip install -e ".[dev]"
```

### 3. Create a Branch

Always create a feature branch from `main`:

```bash
git checkout -b feat/my-feature
```

Use a descriptive branch name:
- `feat/langchain-streaming-support`
- `fix/crewai-async-save`
- `docs/haystack-example`

## Making Changes

### Project Structure

```
packages/
  synap-langchain/        # Each framework has its own package
    pyproject.toml         # Package metadata and dependencies
    synap_langchain/       # Source code
      __init__.py
      memory.py
      retriever.py
      ...
    tests/                 # Tests for this package
      test_memory.py
      ...
```

### Guidelines

- **One package per PR.** If your change touches multiple packages, open separate PRs.
- **Keep integrations thin.** Each integration should map framework interfaces to SDK methods. Business logic belongs in the SDK, not here.
- **Don't import SDK internals.** Only use the public API:
  ```python
  # Good
  from maximem_synap import MaximemSynapSDK

  # Bad — internal module, may change without notice
  from maximem_synap.cache.anticipation_cache import AnticipationCache
  ```
- **Support both sync and async.** Most frameworks support both patterns. Provide async implementations and sync wrappers where the framework expects them.
- **Handle errors gracefully.** Integration code should log errors but never crash the user's application. Use `try/except` with logging for SDK calls.
- **Write tests.** Every new feature or bug fix should include tests. Mock the SDK — don't make real API calls in tests.

### Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.
- Line length: 88 characters.
- Type hints on all public methods.
- Docstrings on all public classes and methods (Google style).

```bash
# Check formatting
ruff check packages/synap-langchain/
ruff format --check packages/synap-langchain/

# Auto-fix
ruff check --fix packages/synap-langchain/
ruff format packages/synap-langchain/
```

## Running Tests

```bash
cd packages/synap-langchain
python -m pytest tests/ -v
```

Tests should mock the SDK and verify:
- Correct SDK methods are called with correct arguments
- Framework responses are properly mapped from SDK responses
- Errors are handled gracefully (logged, not raised)

## Submitting a Pull Request

### 1. Push Your Branch

```bash
git push origin feat/my-feature
```

### 2. Open a Pull Request

Go to the original repo and click **New Pull Request**. Select your fork and branch.

### 3. PR Requirements

Your PR should include:

- **A clear title** describing the change (e.g. "feat(langchain): add streaming support for SynapRetriever")
- **A description** explaining what changed and why
- **Tests** for any new functionality
- **Passing CI** — all existing tests must still pass

### 4. PR Title Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(package-name): add new feature
fix(package-name): fix bug description
docs(package-name): update documentation
test(package-name): add tests for feature
chore: update CI workflow
```

Examples:
- `feat(langchain): add support for RunnableWithMessageHistory`
- `fix(crewai): handle empty search results`
- `docs(haystack): add pipeline example to README`

## Adding a New Integration

Want to add support for a new framework? Great! Here's how:

### 1. Create the Package Structure

```bash
mkdir -p packages/synap-myframework/synap_myframework
mkdir -p packages/synap-myframework/tests
```

### 2. Create `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "synap-myframework"
version = "0.1.0"
description = "Synap memory integration for MyFramework"
readme = "README.md"
requires-python = ">=3.9"
license = "Apache-2.0"
authors = [{name = "Synap Team"}]
keywords = ["synap", "memory", "myframework", "ai"]

dependencies = [
    "maximem-synap>=0.2.0",
    "myframework>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[tool.setuptools.packages.find]
where = ["."]
include = ["synap_myframework*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 3. Implement the Integration

Map your framework's interfaces to SDK methods:

```python
from maximem_synap import MaximemSynapSDK

class SynapMyFrameworkMemory:
    def __init__(self, sdk: MaximemSynapSDK, user_id: str, **kwargs):
        self.sdk = sdk
        self.user_id = user_id

    async def search(self, query: str):
        response = await self.sdk.fetch(
            user_id=self.user_id,
            search_query=[query],
        )
        return response.formatted_context
```

### 4. Add Tests and Open a PR

Follow the PR process above. We'll review and help iterate.

## Reporting Issues

Found a bug? Open an [issue](https://github.com/gauravmaximem/maximem_synap_sdk/issues) with:

- Which package is affected (e.g. `synap-langchain`)
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and framework version

## Code of Conduct

Be respectful and constructive. We're building something useful together.

## Questions?

Open a [discussion](https://github.com/gauravmaximem/maximem_synap_sdk/discussions) or reach out to the Synap team.
