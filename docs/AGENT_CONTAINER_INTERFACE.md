# Agent Container Interface Specification v1.0

## Purpose

This specification defines the **standard interface** that all agent containers must implement to integrate with the Agion platform. This contract ensures:

- Consistent discovery and registration
- Uniform governance integration
- Predictable health monitoring
- Standard deployment patterns

All agent containers (LangGraph, CrewAI, AutoGen, custom frameworks) must conform to this specification.

---

## Required Endpoints

### 1. Health Check

**Endpoint**: `GET /health`

**Purpose**: Kubernetes liveness/readiness probes, platform monitoring

**Response**:
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "agents_registered": 6,
  "last_governance_check": "2025-09-30T12:34:56Z",
  "dependencies": {
    "redis": "connected",
    "registry": "connected",
    "governance": "connected"
  }
}
```

**Status Codes**:
- `200 OK`: Container is healthy
- `503 Service Unavailable`: Container is unhealthy (Kubernetes will restart)

### 2. Agent Metadata Discovery

**Endpoint**: `GET /agents`

**Purpose**: Platform discovers available agents on startup/restart

**Response**:
```json
{
  "container_id": "langgraph-v2",
  "container_version": "2.0.0",
  "framework": "langgraph",
  "framework_version": "0.6.8",
  "agents": [
    {
      "agent_id": "langgraph-v2:supervisor",
      "name": "Supervisor Agent",
      "type": "routing",
      "version": "2.0.0",
      "capabilities": ["agent_routing", "query_analysis", "task_delegation"],
      "input_schema": {
        "type": "object",
        "required": ["query", "session_id"],
        "properties": {
          "query": {"type": "string"},
          "session_id": {"type": "string"}
        }
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "selected_agent": {"type": "string"},
          "confidence": {"type": "number"}
        }
      },
      "trust_score": {
        "current": 0.4,
        "graduation_threshold": 0.6
      },
      "performance": {
        "avg_response_time_ms": 1500,
        "success_rate": 0.0,
        "total_executions": 0
      }
    },
    {
      "agent_id": "langgraph-v2:chart_generator",
      "name": "Chart Generator Agent",
      "type": "visualization",
      "version": "2.0.0",
      "capabilities": [
        "plotly_charts",
        "png_export",
        "time_series_plotting",
        "categorical_analysis"
      ],
      "trust_score": {
        "current": 0.4,
        "graduation_threshold": 0.6
      }
    }
    // ... other agents
  ]
}
```

### 3. Agent Invocation (Optional - Can Use Redis Streams)

**Endpoint**: `POST /agents/{agent_id}/invoke`

**Purpose**: Direct HTTP invocation (alternative to Redis Streams for missions)

**Request**:
```json
{
  "query": "Create a sales chart for Q4",
  "context": {
    "session_id": "session-123",
    "user_id": "user-456",
    "file_ids": ["file-789"],
    "mission_id": "mission-abc"
  }
}
```

**Response**:
```json
{
  "execution_id": "exec-def",
  "status": "success" | "failure" | "error",
  "response": "I've created a chart showing Q4 sales...",
  "data": {
    "chart_url": "https://storage.blob.core.windows.net/...",
    "chart_type": "plotly"
  },
  "metadata": {
    "duration_ms": 2500,
    "governance": {
      "permission": "ALLOW",
      "validation": "ACCEPT",
      "latency_ms": 5.2
    },
    "trust_score_updated": 0.42
  }
}
```

**Status Codes**:
- `200 OK`: Agent executed successfully
- `403 Forbidden`: Governance denied execution
- `400 Bad Request`: Invalid input
- `500 Internal Server Error`: Agent execution failed

### 4. Metrics (Optional - Prometheus Integration)

**Endpoint**: `GET /metrics`

**Purpose**: Prometheus scraping for monitoring

**Response**: Prometheus text format
```
# HELP agent_executions_total Total agent executions
# TYPE agent_executions_total counter
agent_executions_total{agent_id="langgraph-v2:chart_generator",status="success"} 42
agent_executions_total{agent_id="langgraph-v2:chart_generator",status="failure"} 3

# HELP agent_response_time_seconds Agent response time
# TYPE agent_response_time_seconds histogram
agent_response_time_seconds_bucket{agent_id="langgraph-v2:chart_generator",le="1"} 10
agent_response_time_seconds_bucket{agent_id="langgraph-v2:chart_generator",le="2.5"} 35
agent_response_time_seconds_bucket{agent_id="langgraph-v2:chart_generator",le="5"} 42

# HELP agent_trust_score Current agent trust score
# TYPE agent_trust_score gauge
agent_trust_score{agent_id="langgraph-v2:chart_generator"} 0.42
```

---

## Required Environment Variables

All agent containers must accept and respect these environment variables:

### Core Configuration

```bash
# Container Identity
AGION_AGENT_CONTAINER_ID=langgraph-v2        # Unique container identifier

# Platform Services
REDIS_URL=redis://redis-simple.agion-data.svc.cluster.local:6379
AGION_REGISTRY_URL=http://registry-service.agion-core.svc.cluster.local:8085
AGION_GOVERNANCE_URL=http://governance-service.agion-core.svc.cluster.local:8080
AGION_COORDINATION_URL=http://coordination-service.agion-core.svc.cluster.local:8082

# Governance Configuration
GOVERNANCE_TIMEOUT_MS=5000                   # Max time to wait for governance decision
GOVERNANCE_FAIL_SAFE=DENY                    # What to do if governance unavailable

# Performance Tuning
MAX_CONCURRENT_EXECUTIONS=10                 # Max parallel agent executions
EXECUTION_TIMEOUT_MS=30000                   # Max time for agent execution
```

### Optional Configuration

```bash
# Logging
LOG_LEVEL=info                               # debug, info, warning, error
STRUCTURED_LOGGING=true                      # JSON structured logs

# Tracing (OpenTelemetry)
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo.agion-monitoring:4317
OTEL_SERVICE_NAME=langgraph-v2

# Feature Flags
ENABLE_DIRECT_INVOCATION=false               # Allow HTTP invocation or Redis-only
ENABLE_METRICS_ENDPOINT=true                 # Expose /metrics
```

---

## Required Kubernetes Labels

All deployments must have these labels for platform discovery and management:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph-backend
  namespace: agion-langgraph
  labels:
    # Required labels
    platform.agion.com/component: agent-container
    platform.agion.com/framework: langgraph
    platform.agion.com/version: v2.0.0

    # Optional labels
    platform.agion.com/team: ai-agents
    platform.agion.com/environment: production
```

### Label Semantics

- **`platform.agion.com/component`**: Always set to `agent-container`
- **`platform.agion.com/framework`**: Framework name (langgraph, crewai, autogen, custom)
- **`platform.agion.com/version`**: Container version (semantic versioning)

---

## Required Service Annotations

For Prometheus scraping:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: langgraph-backend-service
  namespace: agion-langgraph
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/path: /metrics
    prometheus.io/port: "8000"
```

---

## Startup Behavior

All agent containers must follow this startup sequence:

### 1. Initialize Dependencies (0-5 seconds)

```
1. Load configuration from environment
2. Connect to Redis
3. Validate connection to registry service
4. Validate connection to governance service
```

**Failure handling**: Exit with code 1 if critical services unavailable

### 2. Register Agents (5-10 seconds)

```
1. Fetch agent metadata from internal registry
2. For each agent:
   - POST to registry service /api/v1/agents/register
   - Cache trust score from Redis
3. Set container status to "ready"
```

**Failure handling**: Retry up to 3 times, then exit with code 1

### 3. Start Listening for Work (10+ seconds)

```
1. Subscribe to Redis Streams:
   - missions:{container_id}
   - governance:responses:{container_id}
2. Start HTTP server for health/metadata endpoints
3. Report "healthy" status to Kubernetes
```

**Failure handling**: Kubernetes will restart if health check fails

### 4. Log Startup Complete

```
✅ LangGraph Agent Container v2.0.0 ready
   - 6 agents registered
   - Redis: connected
   - Registry: connected
   - Governance: connected
   - Listening for missions
```

---

## Shutdown Behavior

All agent containers must implement graceful shutdown:

### 1. Receive SIGTERM from Kubernetes (30 second grace period)

```
1. Stop accepting new missions
2. Wait for in-flight agent executions to complete (max 10 seconds)
3. Deregister all agents from registry
4. Close Redis connections
5. Exit with code 0
```

### 2. Forced Shutdown (After 30 seconds)

If graceful shutdown doesn't complete in 30 seconds, Kubernetes sends SIGKILL.

**Best practice**: Design agents to complete quickly (<5 seconds) or checkpoint progress.

---

## Governance Integration Requirements

All agent containers **must** use governance for:

### 1. Pre-Execution Permission

**When**: Before every agent execution

**How**: Call `governance.check_permission()` via Redis Streams or HTTP

**Required fields**:
- `agent_id`
- `action` (what the agent will do)
- `context` (query, user_id, file_ids, etc.)

**Fail-safe**: If governance unavailable, **DENY** by default (configurable via `GOVERNANCE_FAIL_SAFE`)

### 2. Post-Execution Validation

**When**: After agent produces result

**How**: Call `governance.validate_result()` via Redis Streams or HTTP

**Required fields**:
- `agent_id`
- `action` (what the agent did)
- `result` (agent output)
- `context` (execution details)

**Fail-safe**: If validation unavailable, **FLAG_FOR_REVIEW**

### 3. Execution Reporting

**When**: After every execution (success or failure)

**How**: Fire-and-forget call to `governance.report_execution()`

**Required fields**:
- `agent_id`
- `execution_id`
- `status` (success, failure, error, timeout)
- `duration_ms`
- `governance_permission`
- `governance_validation`

---

## Performance Requirements

All agent containers should meet these performance targets:

| Metric | Target | Maximum |
|--------|--------|---------|
| Health check response | <50ms | 200ms |
| Metadata endpoint response | <100ms | 500ms |
| Agent execution (simple) | <2s | 10s |
| Agent execution (complex) | <10s | 30s |
| Governance check latency | <5ms | 100ms |
| Startup time | <10s | 30s |
| Shutdown time | <5s | 30s |

---

## Security Requirements

### 1. Network Policies

Containers should only communicate with:
- Redis (agion-data namespace)
- Registry service (agion-core namespace)
- Governance service (agion-core namespace)
- Coordination service (agion-core namespace)

Block all other traffic via Kubernetes NetworkPolicy.

### 2. Resource Limits

All deployments must have resource limits:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### 3. Non-Root User

Containers must run as non-root user:

```dockerfile
USER 1000:1000
```

### 4. Read-Only Filesystem

Use read-only root filesystem where possible:

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

---

## Testing and Compliance

### Compliance Checker

The platform provides a compliance checker to validate containers:

```bash
# Run compliance check
agion-platform validate-container \
  --namespace agion-langgraph \
  --deployment langgraph-backend

# Output
✅ Health endpoint: PASS
✅ Agents endpoint: PASS
✅ Required labels: PASS
✅ Environment variables: PASS
✅ Governance integration: PASS
✅ Performance: PASS (avg health check: 12ms)
⚠️  Metrics endpoint: MISSING (optional)

Overall: COMPLIANT
```

### Integration Tests

Containers should include integration tests:

```python
# tests/integration/test_platform_integration.py

import pytest
from agion_sdk import RegistryClient, GovernanceClient

@pytest.mark.asyncio
async def test_agent_registration():
    """Test that agents can register with platform"""
    registry = RegistryClient()
    result = await registry.register_agent({
        "agent_id": "test:agent",
        "name": "Test Agent",
        "type": "test"
    })
    assert result["status"] == "registered"

@pytest.mark.asyncio
async def test_governance_permission():
    """Test governance permission check"""
    governance = GovernanceClient()
    permission = await governance.check_permission(
        agent_id="test:agent",
        action="test_action",
        context={}
    )
    assert permission["decision"] in ["ALLOW", "DENY", "REQUIRE_APPROVAL"]

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint responds correctly"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]
```

---

## Reference Implementation

**Repository**: `Agion-Inc/Agent-Container-Template`

Provides boilerplate code for:
- Python (FastAPI)
- TypeScript (Express)
- Rust (Actix-web)

Each template includes:
- ✅ Health and metadata endpoints
- ✅ Agion SDK integration
- ✅ Governance middleware
- ✅ Agent registration on startup
- ✅ Graceful shutdown
- ✅ Kubernetes manifests
- ✅ Integration tests

---

## Versioning and Changes

This specification uses semantic versioning:

- **v1.0**: Initial specification
- **v1.1**: Add optional features (backwards-compatible)
- **v2.0**: Breaking changes (require container updates)

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2025-09-30 | Initial specification |

### Deprecation Policy

When breaking changes are introduced:
1. **6 months notice** via platform announcements
2. **Dual support** for old and new interfaces during transition
3. **Migration guide** provided
4. **Automated migration tools** where possible

---

## Support and Resources

- **Documentation**: https://docs.agion.dev/agent-containers
- **SDK**: `pip install agion-sdk` or `npm install @agion/sdk`
- **Template**: https://github.com/Agion-Inc/Agent-Container-Template
- **Compliance Checker**: `agion-platform validate-container`
- **Support**: #agent-containers on Slack

---

## Summary: Compliance Checklist

- [ ] Health endpoint (`GET /health`) returns 200 with required fields
- [ ] Agents endpoint (`GET /agents`) returns all agent metadata
- [ ] All required environment variables are accepted
- [ ] Kubernetes labels are set correctly
- [ ] Agents register on startup
- [ ] Agents deregister on shutdown
- [ ] Governance integration: permission check before execution
- [ ] Governance integration: result validation after execution
- [ ] Governance integration: execution reporting
- [ ] Graceful shutdown within 30 seconds
- [ ] Resource limits defined
- [ ] Non-root user
- [ ] Integration tests pass

---

**This specification ensures all agent containers integrate seamlessly with the Agion platform, regardless of underlying framework or language.**
