# Architecture Decision: Microservices vs Monorepo for Agent Containers

## Context

The Agion platform will eventually support **dozens of agent frameworks**:
- LangGraph (this repository)
- CrewAI
- AutoGen
- Custom frameworks
- Industry-specific frameworks (medical, legal, financial agents)
- Partner/customer frameworks

Each framework needs:
- Fast governance communication (sub-100ms)
- Agent registration
- Trust score management
- Mission execution
- Independent deployment/scaling

## Decision: **Keep Agent Containers as Separate Microservices**

### Rationale

#### 1. **Polyglot Framework Support**

Different agent frameworks have different technology stacks:

```
LangGraph Container:
  - Python 3.13
  - LangGraph 0.6.8
  - FastAPI
  - AsyncIO

CrewAI Container:
  - Python 3.11
  - CrewAI 0.30+
  - Different dependencies

AutoGen Container:
  - Python 3.10
  - AutoGen 0.2+
  - Different async patterns

Custom Node.js Container:
  - TypeScript
  - Node.js 20+
  - Express

Rust Agent Container:
  - Rust 1.75+
  - Tokio async runtime
  - Actix-web
```

**In a monorepo**: Managing these different stacks, build systems, and dependency conflicts would be a nightmare.

**As microservices**: Each container uses its optimal stack independently.

#### 2. **Independent Deployment & Versioning**

With dozens of agent containers:

```
agion-langgraph:v2.0.0    → Deploy independently
agion-crewai:v1.5.2       → Different release cycle
agion-autogen:v3.1.0      → No impact on others
customer-acme:v1.0.0      → Customer-owned deployment
```

**In a monorepo**: Deploying one framework risks affecting others, requires coordinated releases.

**As microservices**: Deploy and rollback independently. Customer frameworks deploy on their own schedules.

#### 3. **Scaling Characteristics**

Different frameworks have different resource needs:

```
LangGraph Container:
  - CPU: 2 cores
  - Memory: 4GB
  - Replicas: 3

Heavy ML Container (Hugging Face):
  - CPU: 8 cores
  - Memory: 32GB
  - GPU: 1x NVIDIA A100
  - Replicas: 1

Lightweight Rule Engine:
  - CPU: 0.5 cores
  - Memory: 512MB
  - Replicas: 10
```

**As microservices**: Scale each container independently based on its workload and cost profile.

#### 4. **Team Ownership & Development Velocity**

With dozens of frameworks:

```
Team Structure:
  - Platform Team → owns core services (registry, governance, coordination)
  - LangGraph Team → owns langgraph container
  - CrewAI Team → owns crewai container
  - Partner Teams → own their custom containers
  - Customer Teams → own their internal containers
```

**In a monorepo**: Cross-team merge conflicts, shared CI/CD, coordination overhead.

**As microservices**: Each team owns their repo end-to-end. Fast iteration. No coordination needed.

#### 5. **Security & Isolation**

Agent containers execute user code (charts, forecasts, custom logic):

```
Risk Scenario: Malicious agent code in CrewAI container
  - Exploits vulnerability
  - Attempts to access other agent containers
  - Tries to compromise governance service
```

**As microservices**:
- Network isolation (Kubernetes NetworkPolicies)
- Separate namespaces
- Resource quotas per container
- Blast radius contained

#### 6. **Customer & Partner Containers**

Customers may want to bring their own frameworks:

```
Customer ACME:
  - Proprietary agent framework
  - Cannot share code with Agion
  - Needs to deploy in their own namespace
  - Wants to use Agion governance/registry
```

**As microservices**: Customer deploys their container in their namespace, connects to platform services via standard interface.

---

## Recommended Repository Structure

### Core Platform (Monorepo)

```
agion-platform/  (GitHub: Agion-Inc/Agion-Platform)
├── services/
│   ├── registry-service/        # Agent registry
│   ├── governance-service/      # Governance engine
│   ├── coordination-service/    # Multi-agent coordination
│   ├── execution-service/       # Mission execution
│   └── gateway/                 # Unified API gateway
├── shared-libraries/
│   ├── python/
│   │   └── agion-sdk/          # Python SDK for agent containers
│   ├── typescript/
│   │   └── agion-sdk/          # TypeScript SDK
│   └── rust/
│       └── agion-sdk/          # Rust SDK
├── infrastructure/
│   ├── k8s/                     # Platform Kubernetes manifests
│   ├── terraform/               # Infrastructure as code
│   └── helm/                    # Helm charts
└── docs/
    └── agent-container-spec/    # Contract for agent containers
```

### Agent Containers (Separate Repositories)

```
Agion-Inc/Agion-LangGraph      # LangGraph container (this repo)
Agion-Inc/Agion-CrewAI         # CrewAI container
Agion-Inc/Agion-AutoGen        # AutoGen container
Agion-Inc/Agion-HuggingFace    # Hugging Face agents
Partner-Corp/Custom-Agents     # Partner-owned container
Customer-ACME/Internal-Agents  # Customer-owned container
```

### Benefits of Separation

1. ✅ **Clear ownership**: Each container has its own team/owner
2. ✅ **Independent CI/CD**: Deploy on different schedules
3. ✅ **Technology freedom**: Use optimal stack per framework
4. ✅ **Security isolation**: Containers cannot access each other
5. ✅ **Scalability**: Scale each independently
6. ✅ **Customer/partner friendly**: Easy to bring custom containers

---

## Communication Architecture: Redis Streams

### Why Redis Streams for Governance?

#### Performance Requirements

```
Governance Decision Latency Target: <50ms
  - HTTP REST call: ~10-20ms (network + serialization)
  - gRPC call: ~5-10ms (faster serialization)
  - Redis Streams: ~1-5ms (in-memory, persistent)
```

For sub-100ms end-to-end latency with 3 governance checkpoints (permission, validation, feedback), Redis Streams is optimal.

#### Redis Streams Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Agent Container (LangGraph)                     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Governance Client (Redis Streams)                         │ │
│  │                                                             │ │
│  │  - XADD to request stream                                  │ │
│  │  - XREAD from response stream (blocking, 5s timeout)       │ │
│  │  - Correlation ID for request/response matching            │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ↓ Redis (in-memory, <5ms)
┌─────────────────────────────────────────────────────────────────┐
│            Redis (agion-data namespace)                          │
│                                                                   │
│  Streams:                                                         │
│  - governance:requests     (agent → platform)                    │
│  - governance:responses    (platform → agent)                    │
│  - executions:reports      (agent → platform, non-blocking)      │
│  - feedback:submissions    (frontend → platform)                 │
│                                                                   │
│  Caches:                                                          │
│  - agent:{agent_id}:trust_score                                  │
│  - agent:{agent_id}:policies                                     │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ↓ Redis consumer groups
┌─────────────────────────────────────────────────────────────────┐
│              Governance Service (Platform)                       │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Redis Streams Consumer                                     │ │
│  │                                                             │ │
│  │  - XREADGROUP from governance:requests                     │ │
│  │  - Process with policy engine                              │ │
│  │  - XADD response to governance:responses                   │ │
│  │  - Update trust scores in Redis cache                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Redis Streams vs HTTP/gRPC

| Aspect | Redis Streams | HTTP REST | gRPC |
|--------|---------------|-----------|------|
| **Latency** | 1-5ms | 10-20ms | 5-10ms |
| **Throughput** | 100k+ req/s | 10k req/s | 20k req/s |
| **Reliability** | Persistent, ACK | Stateless | Stateless |
| **Backpressure** | Consumer groups | Load balancer | Client-side |
| **Async Support** | Native | Polling/WebSocket | Streaming |
| **Learning Curve** | Medium | Low | Medium-High |

**Verdict**: Use **Redis Streams for governance decisions** (performance-critical, high-frequency) and **HTTP REST for management operations** (registration, health checks, low-frequency).

---

## Shared Libraries: Agion SDK

To avoid duplicating governance client code across dozens of agent containers, publish **Agion SDK** as versioned packages.

### Python SDK

**Published to**: Private PyPI or GitHub Packages

```python
# Install: pip install agion-sdk

from agion_sdk import GovernanceClient, with_governance

# Initialize client (reads from env vars)
governance = GovernanceClient()

# Use as decorator
@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    # Agent logic here
    pass

# Or use directly
permission = await governance.check_permission(
    agent_id="langgraph-v2:chart_generator",
    action="generate_chart",
    context={"query": "..."}
)
```

**Package structure**:
```
agion-sdk/
├── pyproject.toml
├── agion_sdk/
│   ├── __init__.py
│   ├── governance_client.py      # Redis Streams client
│   ├── governance_middleware.py  # Decorator pattern
│   ├── registry_client.py        # Agent registration
│   ├── types.py                  # Shared types
│   └── config.py                 # Configuration
└── tests/
```

### TypeScript SDK

**Published to**: npm (private registry)

```typescript
// Install: npm install @agion/sdk

import { GovernanceClient, withGovernance } from '@agion/sdk';

const governance = new GovernanceClient();

// Use in Express middleware
app.use(withGovernance('chart_generator'));

// Or use directly
const permission = await governance.checkPermission({
  agentId: 'nodejs-v1:chart_generator',
  action: 'generate_chart',
  context: { query: '...' }
});
```

### SDK Benefits

1. ✅ **Consistency**: All containers use same governance logic
2. ✅ **Updates**: Fix bugs once, update SDK version across all containers
3. ✅ **Versioning**: Containers can pin SDK version for stability
4. ✅ **Documentation**: Single source of truth for integration
5. ✅ **Testing**: SDK is thoroughly tested independently

---

## Agent Container Interface Contract

Define a **standard interface** that all agent containers must implement, regardless of framework.

### Contract Specification

**File: `agion-platform/docs/agent-container-spec/v1.md`**

```markdown
# Agent Container Interface v1.0

## Required Endpoints

All agent containers must expose:

### 1. Health Check
GET /health
Response: { "status": "healthy", "version": "2.0.0" }

### 2. Agent Metadata
GET /agents
Response: [
  {
    "agent_id": "langgraph-v2:chart_generator",
    "name": "Chart Generator",
    "type": "visualization",
    "capabilities": ["plotly_charts", "png_export"],
    "version": "2.0.0"
  }
]

### 3. Agent Invocation (Optional - can use Redis Streams)
POST /agents/{agent_id}/invoke
Request: { "query": "...", "context": {...} }
Response: { "result": "...", "execution_id": "..." }

## Required Environment Variables

- AGION_REGISTRY_URL
- AGION_GOVERNANCE_URL (or REDIS_URL for streams)
- AGION_AGENT_CONTAINER_ID
- REDIS_URL (for governance streams)

## Required Kubernetes Labels

metadata:
  labels:
    platform.agion.com/component: agent-container
    platform.agion.com/framework: langgraph
    platform.agion.com/version: v2.0.0

## Startup Behavior

1. Connect to Redis
2. Register all agents with registry service
3. Start listening for missions (via coordination service)
4. Report health status

## Shutdown Behavior

1. Graceful shutdown (30s)
2. Deregister agents from registry
3. Close Redis connections
```

### Container Template Repository

**Create**: `Agion-Inc/Agent-Container-Template`

```
agent-container-template/
├── python/
│   ├── Dockerfile
│   ├── requirements.txt          # Includes agion-sdk
│   ├── main.py                   # FastAPI with health/metadata endpoints
│   └── agents/
│       └── example_agent.py      # @with_governance decorator
├── typescript/
│   ├── Dockerfile
│   ├── package.json              # Includes @agion/sdk
│   ├── src/
│   │   ├── index.ts              # Express with health/metadata
│   │   └── agents/
│   │       └── exampleAgent.ts   # Governance middleware
└── k8s/
    ├── deployment.yaml           # Standard deployment template
    ├── service.yaml
    └── namespace.yaml
```

---

## Implementation Plan

### Phase 1: Extract Agion SDK (Week 1-2)

1. Create `agion-platform/shared-libraries/python/agion-sdk/`
2. Move governance client code from this repo to SDK
3. Add Redis Streams support
4. Publish to private PyPI: `agion-sdk==0.1.0`
5. Update this repo to use SDK: `pip install agion-sdk`

### Phase 2: Update LangGraph Container (Week 2)

1. Replace local governance code with SDK import
2. Add Redis Streams configuration
3. Test end-to-end with platform governance service
4. Update documentation

### Phase 3: Create Container Template (Week 3)

1. Create `Agent-Container-Template` repository
2. Include Python and TypeScript examples
3. Document interface contract
4. Provide Kubernetes manifests

### Phase 4: Onboard Second Framework (Week 4)

1. Create `Agion-CrewAI` repository (using template)
2. Integrate CrewAI framework
3. Use Agion SDK for governance
4. Validate interface compliance
5. Deploy to `agion-crewai` namespace

---

## Repository Recommendations

### ✅ Keep Separate

**This repository** (`Agion-Inc/Agion-LangGraph`):
- Stays independent
- Uses Agion SDK as dependency
- Owned by LangGraph team
- Fast iteration, independent deployment

### ✅ Platform Core

**New repository** (`Agion-Inc/Agion-Platform`):
- Contains all core services (registry, governance, coordination, etc.)
- Contains shared libraries (Agion SDK)
- Contains infrastructure code
- Contains agent container spec
- Owned by platform team

### ✅ Container Template

**New repository** (`Agion-Inc/Agent-Container-Template`):
- Boilerplate for new agent containers
- Examples in multiple languages
- Reference implementation of contract
- Fork this to create new containers

---

## Cost-Benefit Analysis

### Microservices Approach

**Costs**:
- More repositories to manage (but clear ownership reduces overhead)
- Shared library versioning (but SDK simplifies this)
- Network latency between services (Redis Streams mitigates this)

**Benefits**:
- Independent deployment/scaling ⭐⭐⭐
- Technology freedom per framework ⭐⭐⭐
- Team autonomy and velocity ⭐⭐⭐
- Security isolation ⭐⭐
- Customer/partner friendly ⭐⭐⭐
- Supports dozens of frameworks ⭐⭐⭐

### Monorepo Approach

**Costs**:
- Single point of failure (deploy risk)
- Technology constraints (one stack)
- Team coordination overhead
- Difficult to support external frameworks
- Scaling complexity

**Benefits**:
- Simpler dependency management
- Easier refactoring across services
- Single CI/CD pipeline

---

## Final Recommendation

### Architecture

**Microservices**: Keep agent containers as separate repositories.

### Communication

**Hybrid approach**:
- **Redis Streams**: Governance decisions (performance-critical, high-frequency)
- **HTTP REST**: Management operations (registration, health checks, low-frequency)

### Code Sharing

**Agion SDK**: Publish versioned SDKs in Python, TypeScript, Rust for common governance/registry logic.

### This Repository

**Status**: **Keep separate** from platform core. Install Agion SDK as dependency.

```python
# requirements.txt
agion-sdk>=0.1.0,<0.2.0

# backend/core/governance_client.py
from agion_sdk import GovernanceClient, with_governance

# Agent nodes
from agion_sdk import with_governance

@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    # Clean agent logic
    pass
```

This approach scales to dozens of agent frameworks while maintaining velocity, security, and autonomy.
