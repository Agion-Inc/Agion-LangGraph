# Agion SDK Specification

## Overview

The **Agion SDK** is a shared library that provides common functionality for all agent containers in the Agion platform. It eliminates code duplication across dozens of agent frameworks and ensures consistent governance, registration, and communication patterns.

## Languages Supported

- **Python** (`agion-sdk`) - For LangGraph, CrewAI, AutoGen, etc.
- **TypeScript** (`@agion/sdk`) - For Node.js agent frameworks
- **Rust** (`agion-sdk`) - For high-performance agent frameworks

## Publishing Strategy

### Python SDK

**Repository**: `Agion-Platform/shared-libraries/python/agion-sdk/`

**Distribution**: Private PyPI or GitHub Packages

```bash
# Install from private PyPI
pip install agion-sdk --index-url https://pypi.agion.dev/simple

# Or from GitHub Packages
pip install agion-sdk --extra-index-url https://github.com/Agion-Inc/Agion-Platform
```

**Versioning**: Semantic versioning (e.g., `0.1.0`, `0.2.0`, `1.0.0`)

```python
# pyproject.toml
[project]
name = "agion-sdk"
version = "0.1.0"
description = "Agion Platform SDK for agent containers"
requires-python = ">=3.10"
dependencies = [
    "redis>=5.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0"
]
```

### TypeScript SDK

**Repository**: `Agion-Platform/shared-libraries/typescript/agion-sdk/`

**Distribution**: npm (private registry or GitHub Packages)

```bash
# Install from npm
npm install @agion/sdk

# Or from GitHub Packages
npm install @agion/sdk --registry=https://npm.pkg.github.com
```

**Versioning**: Semantic versioning

```json
{
  "name": "@agion/sdk",
  "version": "0.1.0",
  "description": "Agion Platform SDK for agent containers",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "dependencies": {
    "ioredis": "^5.3.0",
    "axios": "^1.6.0"
  }
}
```

## Python SDK API

### Installation

```bash
pip install agion-sdk
```

### Core Modules

#### 1. Governance Client

```python
from agion_sdk import GovernanceClient

# Initialize (reads from environment variables)
governance = GovernanceClient()

# Permission check
permission = await governance.check_permission(
    agent_id="langgraph-v2:chart_generator",
    action="generate_chart",
    context={"query": "Create sales chart", "user_id": "user123"}
)
# Returns: {"decision": "ALLOW", "reason": "...", "latency_ms": 3.2}

# Result validation
validation = await governance.validate_result(
    agent_id="langgraph-v2:chart_generator",
    action="generate_chart",
    result={"chart_url": "https://..."},
    context={"duration_ms": 2500}
)
# Returns: {"decision": "ACCEPT", "reason": "...", "latency_ms": 2.8}

# Execution reporting (fire-and-forget)
await governance.report_execution(
    agent_id="langgraph-v2:chart_generator",
    execution_data={
        "execution_id": "exec-123",
        "status": "success",
        "duration_ms": 2500,
        "action": "generate_chart"
    }
)

# User feedback submission (fire-and-forget)
await governance.submit_user_feedback(
    agent_id="langgraph-v2:chart_generator",
    execution_id="exec-123",
    feedback={"rating": 5, "sentiment": "positive", "action": "like"}
)

# Get trust score (cached, <1ms)
trust_score = await governance.get_agent_trust_score("langgraph-v2:chart_generator")
# Returns: 0.48

# Context manager for clean shutdown
async with GovernanceClient() as gov:
    permission = await gov.check_permission(...)
```

#### 2. Governance Middleware (Decorator)

```python
from agion_sdk import with_governance
from langgraph_agents.state import AgentState

@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    """
    Agent node with automatic governance enforcement.

    The decorator handles:
    - Permission check before execution
    - Result validation after execution
    - Execution reporting
    - Error handling and governance failures
    """
    # Clean agent logic (no governance code!)
    query = state["query"]
    file_data = state.get("file_data")

    chart_url = generate_plotly_chart(file_data, query)

    return {
        **state,
        "agent_response": f"Chart generated: {chart_url}",
        "agent_data": {"chart_url": chart_url}
    }
```

#### 3. Registry Client

```python
from agion_sdk import RegistryClient

registry = RegistryClient()

# Register agent
await registry.register_agent({
    "agent_id": "langgraph-v2:chart_generator",
    "container_id": "langgraph-v2",
    "name": "Chart Generator Agent",
    "type": "visualization",
    "capabilities": ["plotly_charts", "png_export"],
    "trust_score": {"initial": 0.4, "current": 0.4},
    "endpoints": {"invoke": "http://..."}
})

# Update agent metadata
await registry.update_agent("langgraph-v2:chart_generator", {
    "version": "2.1.0",
    "capabilities": ["plotly_charts", "png_export", "interactive_charts"]
})

# Deregister agent
await registry.deregister_agent("langgraph-v2:chart_generator")

# Get agent info
agent = await registry.get_agent("langgraph-v2:chart_generator")
```

#### 4. Configuration

```python
from agion_sdk import AgionConfig

# Automatic configuration from environment variables
config = AgionConfig()

# Or explicit configuration
config = AgionConfig(
    redis_url="redis://redis-simple.agion-data.svc.cluster.local:6379",
    registry_url="http://registry-service.agion-core.svc.cluster.local:8085",
    governance_url="http://governance-service.agion-core.svc.cluster.local:8080",
    container_id="langgraph-v2",
    governance_timeout_ms=5000
)

# Environment variables (auto-detected):
# - REDIS_URL
# - AGION_REGISTRY_URL
# - AGION_GOVERNANCE_URL
# - AGION_AGENT_CONTAINER_ID
# - GOVERNANCE_TIMEOUT_MS
```

#### 5. Types and Models

```python
from agion_sdk.types import (
    GovernanceDecision,
    AgentMetadata,
    TrustScore,
    ExecutionReport,
    UserFeedback
)

# Pydantic models for type safety
from pydantic import BaseModel

class PermissionResponse(BaseModel):
    decision: GovernanceDecision  # "ALLOW" | "DENY" | "REQUIRE_APPROVAL"
    reason: str
    user_message: str
    latency_ms: float

class ValidationResponse(BaseModel):
    decision: GovernanceDecision  # "ACCEPT" | "REJECT" | "FLAG_FOR_REVIEW"
    reason: str
    user_message: str
    should_retry: bool
    latency_ms: float
```

### Full Example: LangGraph Agent with SDK

```python
# backend/langgraph_agents/nodes/chart_agent.py

from agion_sdk import with_governance
from langgraph_agents.state import AgentState, set_agent_response

@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    """
    Chart generation agent with automatic governance.

    The @with_governance decorator:
    1. Checks permission before execution
    2. Validates result after execution
    3. Reports execution metrics
    4. Handles governance failures
    """

    # Clean agent logic
    query = state["query"]
    file_data = state.get("file_data")

    if not file_data:
        return set_error(state, "No file data provided for chart generation")

    # Generate chart using Plotly
    from langgraph_agents.tools.chart_tools import generate_plotly_chart

    chart_url = generate_plotly_chart(file_data, query)

    return set_agent_response(
        state,
        response=f"I've created a chart showing {query}. View it here: {chart_url}",
        agent_name="chart_generator",
        data={"chart_url": chart_url, "chart_type": "plotly"}
    )
```

### Startup Integration

```python
# backend/main.py

from agion_sdk import RegistryClient, GovernanceClient
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with SDK integration"""

    print("🚀 Starting LangGraph Agent Container...")

    # Initialize SDK clients
    registry = RegistryClient()
    governance = GovernanceClient()

    # Register all agents
    try:
        await registry.register_all_agents([
            {
                "agent_id": "langgraph-v2:supervisor",
                "name": "Supervisor Agent",
                "type": "routing",
                "capabilities": ["agent_routing", "query_analysis"],
                "trust_score": {"initial": 0.4, "current": 0.4}
            },
            {
                "agent_id": "langgraph-v2:chart_generator",
                "name": "Chart Generator Agent",
                "type": "visualization",
                "capabilities": ["plotly_charts", "png_export"],
                "trust_score": {"initial": 0.4, "current": 0.4}
            },
            # ... other agents
        ])
        print("✅ All agents registered with platform")
    except Exception as e:
        print(f"❌ Agent registration failed: {str(e)}")

    yield

    # Cleanup
    print("🛑 Shutting down...")
    await registry.deregister_all_agents()
    await governance.close()
    print("✅ Cleanup complete")
```

## TypeScript SDK API

### Installation

```bash
npm install @agion/sdk
```

### Core Modules

#### 1. Governance Client

```typescript
import { GovernanceClient } from '@agion/sdk';

const governance = new GovernanceClient();

// Permission check
const permission = await governance.checkPermission({
  agentId: 'nodejs-v1:chart_generator',
  action: 'generate_chart',
  context: { query: 'Create sales chart', userId: 'user123' }
});
// Returns: { decision: 'ALLOW', reason: '...', latencyMs: 3.2 }

// Result validation
const validation = await governance.validateResult({
  agentId: 'nodejs-v1:chart_generator',
  action: 'generate_chart',
  result: { chartUrl: 'https://...' },
  context: { durationMs: 2500 }
});

// Execution reporting
await governance.reportExecution({
  agentId: 'nodejs-v1:chart_generator',
  executionData: {
    executionId: 'exec-123',
    status: 'success',
    durationMs: 2500,
    action: 'generate_chart'
  }
});

// Get trust score
const trustScore = await governance.getAgentTrustScore('nodejs-v1:chart_generator');
// Returns: 0.48
```

#### 2. Governance Middleware (Express)

```typescript
import { withGovernance } from '@agion/sdk';
import express from 'express';

const app = express();

// Apply governance middleware to specific route
app.post(
  '/agents/chart_generator/invoke',
  withGovernance('chart_generator', 'generate_chart'),
  async (req, res) => {
    // Clean agent logic (governance handled by middleware)
    const { query, fileData } = req.body;

    const chartUrl = await generateChart(fileData, query);

    res.json({
      response: `Chart generated: ${chartUrl}`,
      chartUrl
    });
  }
);
```

## SDK Package Structure

### Python SDK

```
agion-sdk/
├── pyproject.toml
├── README.md
├── agion_sdk/
│   ├── __init__.py
│   ├── governance_client.py       # GovernanceClient (Redis Streams)
│   ├── governance_middleware.py   # @with_governance decorator
│   ├── registry_client.py         # RegistryClient (HTTP)
│   ├── config.py                  # AgionConfig
│   ├── types.py                   # Pydantic models
│   └── exceptions.py              # Custom exceptions
├── tests/
│   ├── test_governance.py
│   ├── test_registry.py
│   └── test_middleware.py
└── examples/
    ├── langgraph_example.py
    ├── crewai_example.py
    └── fastapi_example.py
```

### TypeScript SDK

```
@agion/sdk/
├── package.json
├── README.md
├── src/
│   ├── index.ts
│   ├── GovernanceClient.ts
│   ├── governanceMiddleware.ts
│   ├── RegistryClient.ts
│   ├── config.ts
│   ├── types.ts
│   └── errors.ts
├── tests/
│   ├── governance.test.ts
│   ├── registry.test.ts
│   └── middleware.test.ts
└── examples/
    ├── express-example.ts
    └── fastify-example.ts
```

## Versioning and Compatibility

### Semantic Versioning

- **Major** (1.0.0): Breaking API changes
- **Minor** (0.1.0): New features, backwards-compatible
- **Patch** (0.0.1): Bug fixes, backwards-compatible

### Version Compatibility Matrix

| SDK Version | Platform Version | Redis Version | Python Version | Notes |
|-------------|------------------|---------------|----------------|-------|
| 0.1.x | 1.0.x | 5.0+ | 3.10+ | Initial release |
| 0.2.x | 1.1.x | 5.0+ | 3.10+ | Added async middleware |
| 1.0.x | 2.0.x | 7.0+ | 3.11+ | Breaking: new governance API |

### Pinning SDK Versions

```python
# requirements.txt (conservative)
agion-sdk>=0.1.0,<0.2.0

# requirements.txt (aggressive)
agion-sdk>=0.1.0,<1.0.0

# requirements.txt (locked)
agion-sdk==0.1.5
```

## Distribution and CI/CD

### Python SDK Publishing

```yaml
# .github/workflows/publish-python-sdk.yml
name: Publish Python SDK

on:
  push:
    tags:
      - 'python-sdk-v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

### TypeScript SDK Publishing

```yaml
# .github/workflows/publish-ts-sdk.yml
name: Publish TypeScript SDK

on:
  push:
    tags:
      - 'ts-sdk-v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm run build
      - run: npm test
      - run: npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## Agent Container Integration

### Update This Repository

```python
# requirements.txt
agion-sdk>=0.1.0,<0.2.0

# backend/core/governance_client.py (deprecated, remove)
# backend/core/governance_middleware.py (deprecated, remove)

# backend/langgraph_agents/nodes/chart_agent.py
from agion_sdk import with_governance

@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    # Agent logic
    pass
```

### Benefits

1. ✅ **Zero duplication**: Governance logic written once, used everywhere
2. ✅ **Consistent behavior**: All containers use same governance implementation
3. ✅ **Easy updates**: Fix bugs once, bump SDK version across all containers
4. ✅ **Type safety**: Pydantic/TypeScript types ensure correct usage
5. ✅ **Fast onboarding**: New frameworks install SDK and start immediately

## SDK Development Workflow

1. **Develop in Platform repo**: Make changes in `Agion-Platform/shared-libraries/python/agion-sdk/`
2. **Test locally**: Use `pip install -e .` for local development
3. **Version bump**: Update version in `pyproject.toml`
4. **Tag release**: `git tag python-sdk-v0.1.5 && git push --tags`
5. **CI publishes**: GitHub Action publishes to PyPI
6. **Update containers**: Bump SDK version in agent container requirements

This ensures the SDK remains the source of truth for platform integration.
