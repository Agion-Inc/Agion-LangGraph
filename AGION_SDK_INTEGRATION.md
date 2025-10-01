# Agion SDK Integration - Complete

## Overview

The Agion LangGraph container has been fully integrated with the Agion SDK for platform governance, trust management, and metrics reporting.

## Integration Components

### 1. SDK Installation
- **Location**: `agion-sdk-python/` directory
- **Dependency**: Added to `backend/requirements.txt`
  - `redis==5.2.2` (required by SDK)
  - `agion-sdk @ file:///app/agion-sdk-python` (local installation)

### 2. Configuration (`backend/core/config.py`)
Added Agion platform settings:
- `agion_gateway_url`: Gateway Service URL (default: `http://gateway-service.agion-core.svc.cluster.local:8080`)
- `agion_redis_url`: Redis URL for events/policies (default: `redis://redis-service.agion-core.svc.cluster.local:6379`)
- `agion_agent_id`: Agent container ID (default: `langgraph-v2`)
- `agion_agent_version`: Container version (default: `2.0.0`)
- `agion_policy_sync_enabled`: Enable policy sync (default: `True`)

### 3. SDK Client Wrapper (`backend/core/agion.py`)
Singleton wrapper for SDK lifecycle:
- `AgionClient.initialize()`: Initialize SDK on startup
- `AgionClient.shutdown()`: Cleanup on shutdown
- `AgionClient.get_sdk()`: Get SDK instance
- `get_agion_sdk()`: Convenience function

### 4. Application Lifecycle (`backend/main.py`)
Integrated into FastAPI lifespan:
```python
# Startup
await AgionClient.initialize()
await register_all_agents()

# Shutdown
await AgionClient.shutdown()
```

### 5. Agent Registry (`backend/langgraph_agents/agent_registry.py`)
Registers all 6 agents with platform:
- `langgraph-v2:supervisor` - Query routing
- `langgraph-v2:chart_agent` - Chart generation
- `langgraph-v2:brand_performance_agent` - KPI analysis
- `langgraph-v2:forecasting_agent` - Time series forecasting
- `langgraph-v2:anomaly_detection_agent` - Anomaly detection
- `langgraph-v2:general_agent` - Conversational AI

Each agent includes:
- Metadata and capabilities
- Input/output schemas
- Initial performance metrics
- Trust score initialization (starts at 0.4)

### 6. Metrics Reporter (`backend/langgraph_agents/metrics_reporter.py`)
Reports execution metrics to platform:
- `report_execution_start()`: Track execution start
- `report_execution_success()`: +2% trust impact
- `report_execution_failure()`: -2% trust impact
- `report_execution_error()`: -3% trust impact
- `report_governance_violation()`: -5% trust impact
- `report_user_feedback()`: +0.5% trust for ratings ≥4

**Trust Score Philosophy:**
- Start: 0.4 (40% baseline competence)
- Graduate: 0.6 (60% proven reliability after 10 successes)
- Strategy: Moderate (+2% success, -2% failure, -3% error)

### 7. Governance Wrapper (`backend/langgraph_agents/governance_wrapper.py`)
Decorator for agent nodes:
```python
@governed_node("agent_name", "action_name")
async def agent_node(state: AgentState) -> AgentState:
    # Agent logic
    return state
```

Provides:
- Policy enforcement (pre-execution)
- Execution tracking
- Metrics reporting (post-execution)
- Trust score updates
- Error handling

### 8. Agent Node Updates
All 6 agent nodes wrapped with governance:
- `backend/langgraph_agents/nodes/supervisor.py`: `@governed_node("supervisor", "route_query")`
- `backend/langgraph_agents/nodes/chart_agent.py`: `@governed_node("chart_agent", "generate_chart")`
- `backend/langgraph_agents/nodes/brand_performance_agent.py`: `@governed_node("brand_performance_agent", "analyze_performance")`
- `backend/langgraph_agents/nodes/forecasting_agent.py`: `@governed_node("forecasting_agent", "forecast")`
- `backend/langgraph_agents/nodes/anomaly_detection_agent.py`: `@governed_node("anomaly_detection_agent", "detect_anomalies")`
- `backend/langgraph_agents/nodes/general_agent.py`: `@governed_node("general_agent", "chat")`

### 9. Docker Integration (`Dockerfile.backend.prod`)
Updated to include SDK:
```dockerfile
# Copy SDK and requirements
COPY agion-sdk-python/ /app/agion-sdk-python/
COPY backend/requirements.txt .

# ... install dependencies ...

# Copy SDK to runtime
COPY --from=builder /app/agion-sdk-python /app/agion-sdk-python
```

### 10. Kubernetes Deployment (`k8s/deployment.yaml`)
Added environment variables:
```yaml
- name: AGION_GATEWAY_URL
  value: "http://gateway-service.agion-core.svc.cluster.local:8080"
- name: AGION_REDIS_URL
  value: "redis://redis-service.agion-core.svc.cluster.local:6379"
- name: AGION_AGENT_ID
  value: "langgraph-v2"
- name: AGION_AGENT_VERSION
  value: "2.0.0"
- name: AGION_POLICY_SYNC_ENABLED
  value: "true"
```

## Platform Communication

### Events Published to Redis Streams

**Trust Events** (`agion:events:trust`):
- `task_started`: Execution begins
- `task_completed`: Success (+2% trust)
- `task_failed`: Failure (-2% trust)
- `error`: Exception (-3% trust)
- `governance_violation`: Policy breach (-5% trust)
- `positive_feedback`: User rating ≥4 (+0.5% trust)

**User Feedback** (`agion:events:feedback`):
- execution_id, user_id, feedback_type, rating, comment

**Mission Events** (`agion:events:missions`):
- Mission coordination for multi-agent tasks

### Policies Synced from Platform

**Automatic Background Sync**:
- Redis Pub/Sub for real-time updates
- HTTP fallback polling (30s interval)
- Local policy engine (<1ms evaluation)

**Policy Types**:
- RBAC enforcement
- User permissions
- Resource access control
- Rate limiting
- Compliance rules

## Execution Flow

1. **Startup**:
   ```
   Initialize Database → Initialize Agion SDK → Register 6 Agents
   ```

2. **User Query**:
   ```
   Query → @governed_node decorator:
     1. Generate execution_id
     2. Check governance policies
     3. Report execution start
     4. Execute agent node
     5. Report success/failure/error
     6. Update trust score
     7. Return result
   ```

3. **Trust Score Update**:
   ```
   Event → Redis Stream → Governance Service → Trust Score Calculation → Database
   ```

4. **Shutdown**:
   ```
   Stop Azure Sync → Shutdown Agion SDK → Close Database
   ```

## Trust Score Milestones

- **0.40**: Starting (baseline trust)
- **0.40-0.50**: Learning (1-5 successes)
- **0.50-0.60**: Developing (5-10 successes)
- **0.60**: **Graduated** (10 successes - proven reliability)
- **0.60-0.80**: Trusted (most tasks)
- **0.80-1.00**: Expert (critical tasks)

## Testing

### Local Testing
```bash
# Set environment variables
export AGION_GATEWAY_URL="http://localhost:8080"
export AGION_REDIS_URL="redis://localhost:6379"

# Run backend
cd backend
python start_server.py
```

### Check SDK Metrics
```python
from core.agion import AgionClient

# Get metrics
metrics = await AgionClient.get_metrics()
print(metrics)
```

### Monitor Redis Events
```bash
# Watch trust events
redis-cli XREAD COUNT 10 STREAMS agion:events:trust 0-0

# Watch user feedback
redis-cli XREAD COUNT 10 STREAMS agion:events:feedback 0-0
```

## Deployment

### Build Docker Images
```bash
docker build -f Dockerfile.backend.prod -t langgraph-backend:latest .
docker push agionacr62703.azurecr.io/langgraph-backend:latest
```

### Deploy to Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
kubectl get pods -n agion-langgraph
kubectl logs -f <pod-name> -n agion-langgraph
```

### Verify Integration
```bash
# Check agent registration
kubectl logs -f langgraph-backend-<pod-id> -n agion-langgraph | grep "Agents registered"

# Check SDK initialization
kubectl logs -f langgraph-backend-<pod-id> -n agion-langgraph | grep "Agion SDK initialized"

# Check policy sync
kubectl logs -f langgraph-backend-<pod-id> -n agion-langgraph | grep "Loaded .* policies"
```

## Key Features

✅ **Local-First Governance**: <1ms policy checks with local engine
✅ **Background Policy Sync**: Real-time updates via Redis Pub/Sub
✅ **Fire-and-Forget Events**: Non-blocking metrics reporting
✅ **Trust Management**: Automatic trust score updates
✅ **Dynamic Configuration**: Fetch prompts/models without code changes
✅ **RBAC Integration**: User permission enforcement
✅ **Mission Coordination**: Multi-agent task support
✅ **Fail-Safe**: Agent runs without platform if SDK unavailable

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                LangGraph Agent Container                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  6 Specialized Agents (All Governed)                 │  │
│  │  • Supervisor  • Chart  • Brand Performance          │  │
│  │  • Forecasting • Anomaly Detection • General         │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Governance Wrapper (@governed_node)                 │  │
│  │  • Policy Check • Metrics Reporting • Trust Updates  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agion SDK                                           │  │
│  │  • Local Policy Engine • Event Publisher             │  │
│  │  • Background Sync • Config Fetcher                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
            HTTP (Config/Registration)
            Redis Pub/Sub (Policy Updates)
            Redis Streams (Events)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Agion Platform Backend Services                 │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  Gateway   │  │ Governance   │  │  Redis             │ │
│  │  :8080     │  │ Service      │  │  :6379             │ │
│  │            │  │ :8083        │  │                    │ │
│  │ • Agent    │  │ • Policies   │  │ • Streams          │ │
│  │   Reg      │  │ • Trust      │  │ • Pub/Sub          │ │
│  │ • Prompts  │  │   Scores     │  │ • Cache            │ │
│  │ • Models   │  │ • Evaluation │  │                    │ │
│  └────────────┘  └──────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## User Feedback System ✅

**Implemented**: Users can now provide feedback on agent responses, directly affecting trust scores!

### Feedback Flow
```
User receives response → Provides feedback (👍/👎 + rating) → SDK publishes event → Trust score updated
```

### API Endpoints
- `POST /api/v1/feedback` - Submit feedback on agent response
- `GET /api/v1/feedback/message/{message_id}` - Get feedback for message
- `GET /api/v1/feedback/stats` - Get aggregated statistics

### Trust Impact
- **Rating ≥4**: +0.5% trust score
- **Rating <4**: No trust impact (recorded for analytics)
- **Thumbs up**: Positive signal
- **Thumbs down**: Negative signal

### Database Model
```sql
CREATE TABLE user_feedback (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) REFERENCES chat_messages(id),
    user_id VARCHAR(100) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,  -- 'thumbs_up' or 'thumbs_down'
    rating INTEGER,                      -- Optional 1-5
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Frontend Integration Example
```typescript
// Submit feedback
await fetch('/api/v1/feedback', {
  method: 'POST',
  body: JSON.stringify({
    message_id: messageId,
    feedback_type: 'thumbs_up',
    rating: 5,
    comment: 'Great response!'
  })
});
```

See `SDK_TESTING_GUIDE.md` for complete testing scenarios.

## Testing

### Run SDK Integration Tests
```bash
cd backend
python test_sdk_integration.py
```

Expected output:
```
✅ PASS - SDK Initialization
✅ PASS - Agent Registration
✅ PASS - Metrics Reporting
✅ PASS - Event Publishing
✅ PASS - SDK Metrics
Results: 5/5 tests passed
```

### Manual Testing
See `SDK_TESTING_GUIDE.md` for:
- Basic chat with feedback
- Chart generation with feedback
- Monitoring trust score updates
- Feedback statistics

## Next Steps

1. **Deploy to AKS**: Push images and apply K8s manifests
2. **Verify Registration**: Check agent registration in platform admin UI
3. **Test Governance**: Create policies and verify enforcement
4. **Monitor Trust Scores**: Watch trust scores evolve over executions
5. **Test User Feedback**: Use the feedback API to rate responses ✅
6. **Frontend UI**: Add feedback buttons to chat interface
7. **Mission Coordination**: Build multi-agent workflows

## Documentation References

- SDK Specification: `docs/AGION_SDK_SPECIFICATION.md`
- Backend Integration: `agion-sdk-python/BACKEND_INTEGRATION.md`
- Agent Registry: `docs/AGENT_REGISTRY_INTEGRATION.md`
- Governance Architecture: `docs/GOVERNANCE_INJECTION_ARCHITECTURE.md`
- Architecture Decision: `docs/ARCHITECTURE_DECISION_MICROSERVICES.md`
