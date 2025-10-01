# Agion SDK - Backend Connection Summary

## Overview

The Agion SDK connects to your platform backend through two main channels:

1. **HTTP/REST** - Configuration and registration (Gateway Service)
2. **Redis** - Policy updates (Pub/Sub) and Events (Streams)

## Connection Points

### 1. Gateway Service (HTTP)

**URL**: Default `http://gateway:8080`

**Used For:**
- Agent registration on initialization
- Fetching dynamic prompts (`/api/v1/prompts/by-location/{name}`)
- Fetching model configs (`/api/v1/models/by-purpose/{purpose}`)
- Fetching resource configs (`/api/v1/resources/by-name/{name}`)
- Syncing policies (`/api/v1/policies?agent_id={id}&status=active`)

**Connection Test:**
```bash
curl http://localhost:8080/health
```

### 2. Redis Server

**URL**: Default `redis://redis:6379`

**Used For:**
- **Pub/Sub Channel** `agion:policy:updates` - Instant policy update notifications
- **Stream** `agion:events:trust` - Trust score events
- **Stream** `agion:events:feedback` - User feedback events
- **Stream** `agion:events:missions` - Mission coordination events
- **Stream** `agion:missions:{id}:messages` - Mission messages

**Connection Test:**
```bash
redis-cli ping
```

## Data Flow Diagrams

### Policy Enforcement Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                             │
│                                                               │
│   SDK Initialize                                              │
│       ↓                                                       │
│   HTTP GET /api/v1/policies?agent_id=X&status=active         │
│       ↓                                                       │
│   Load policies into local engine                            │
│       ↓                                                       │
│   Subscribe to Redis agion:policy:updates                    │
│       ↓                                                       │
│   ✓ Ready for < 1ms policy checks                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 2. RUNTIME POLICY CHECK                                       │
│                                                               │
│   @sdk.governed("agent", "action")                           │
│       ↓                                                       │
│   Local Policy Engine Evaluation (< 1ms)                     │
│       ↓                                                       │
│   If ALLOW → Execute function                                │
│   If DENY → Raise PolicyViolationError                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 3. POLICY UPDATE                                              │
│                                                               │
│   Admin updates policy in UI                                 │
│       ↓                                                       │
│   Gateway publishes to agion:policy:updates                  │
│       ↓                                                       │
│   SDK receives notification                                  │
│       ↓                                                       │
│   HTTP GET /api/v1/policies (fetch latest)                   │
│       ↓                                                       │
│   Update local policy engine                                 │
│       ↓                                                       │
│   ✓ New policies active in < 1 second                        │
└──────────────────────────────────────────────────────────────┘
```

### Event Publishing Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. AGENT EXECUTION                                            │
│                                                               │
│   Agent completes task successfully                          │
│       ↓                                                       │
│   sdk.event_client.publish_trust_event(                      │
│       event_type="task_completed",                           │
│       severity="positive",                                   │
│       impact=0.05                                            │
│   )                                                           │
│       ↓                                                       │
│   Event added to buffer (non-blocking)                       │
│       ↓                                                       │
│   Continue agent execution immediately                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 2. BACKGROUND FLUSH (every 5 seconds)                         │
│                                                               │
│   Flush worker wakes up                                      │
│       ↓                                                       │
│   Batch all buffered events                                  │
│       ↓                                                       │
│   Redis XADD agion:events:trust {event_data}                │
│       ↓                                                       │
│   ✓ Events published to stream                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 3. BACKEND PROCESSING                                         │
│                                                               │
│   Governance Service reads stream                            │
│       ↓                                                       │
│   Process trust events                                       │
│       ↓                                                       │
│   Update trust scores in database                            │
│       ↓                                                       │
│   ✓ Trust scores updated                                     │
└──────────────────────────────────────────────────────────────┘
```

### Configuration Fetching Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. FETCH PROMPT                                               │
│                                                               │
│   prompt = await sdk.get_prompt(location="data_analysis")    │
│       ↓                                                       │
│   Check cache (60s TTL)                                      │
│       ↓                                                       │
│   If cached → Return immediately                             │
│   If not cached → HTTP GET /api/v1/prompts/by-location/...  │
│       ↓                                                       │
│   Cache result for 60 seconds                                │
│       ↓                                                       │
│   Return PromptConfig                                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 2. USE IN AGENT                                               │
│                                                               │
│   Use prompt content in LLM call                             │
│       ↓                                                       │
│   Admin updates prompt in UI                                 │
│       ↓                                                       │
│   After 60 seconds, next fetch gets new version              │
│       ↓                                                       │
│   ✓ Agent automatically uses updated prompt                  │
└──────────────────────────────────────────────────────────────┘
```

## Backend Service Mapping

### Endpoint → Service Mapping

| Endpoint                                  | Backend Service      | Port | Purpose                |
|-------------------------------------------|---------------------|------|------------------------|
| `/api/v1/agents/register`                 | Gateway             | 8080 | Agent registration     |
| `/api/v1/prompts/by-location/{name}`      | Gateway             | 8080 | Fetch prompt config    |
| `/api/v1/models/by-purpose/{purpose}`     | Gateway             | 8080 | Fetch model config     |
| `/api/v1/resources/by-name/{name}`        | Gateway             | 8080 | Fetch resource config  |
| `/api/v1/policies`                        | Gateway → Governance| 8080 | Fetch policies         |
| `agion:policy:updates` (Pub/Sub)          | Redis              | 6379 | Policy update notif    |
| `agion:events:trust` (Stream)             | Redis              | 6379 | Trust events           |
| `agion:events:feedback` (Stream)          | Redis              | 6379 | User feedback          |
| `agion:events:missions` (Stream)          | Redis              | 6379 | Mission events         |

### Service Responsibilities

**Gateway Service** (`http://gateway:8080`)
- Agent registration and discovery
- Prompt registry management
- Model registry management
- Resource registry management
- Policy API proxy (to Governance Service)
- User authentication and RBAC

**Governance Service** (`http://governance:8083`)
- Policy storage and management
- Policy evaluation logic
- Trust score calculation
- Trust event processing (from Redis)
- Violation tracking

**Redis** (`redis://redis:6379`)
- Policy update notifications (Pub/Sub)
- Event streaming (trust, feedback, missions)
- Caching layer
- Message passing for coordination

## Network Requirements

### Agent Container → Backend Services

```
Agent Container
    ↓ HTTP (outbound)
Gateway Service :8080
    ↓ TCP (outbound)
Redis :6379
```

**Required Network Rules:**
- Agent can reach Gateway on port 8080 (HTTP)
- Agent can reach Redis on port 6379 (TCP)
- Gateway can reach Governance Service on port 8083 (HTTP)
- Gateway can reach Redis on port 6379 (TCP)
- Governance Service can reach Redis on port 6379 (TCP)

### Docker Network Configuration

```yaml
networks:
  agion-network:
    driver: bridge

services:
  gateway:
    networks:
      - agion-network

  governance:
    networks:
      - agion-network

  redis:
    networks:
      - agion-network

  my-agent:
    networks:
      - agion-network
```

## Authentication & Security

### Current Implementation

**Agent → Gateway:**
- No authentication required for agent registration (development)
- Configuration endpoints may require auth tokens
- Uses HTTP (not HTTPS) in development

**Agent → Redis:**
- No authentication required (development)
- Direct connection to Redis

### Production Recommendations

**Agent → Gateway:**
- Use HTTPS/TLS: `https://gateway:8443`
- Require API key or JWT for agent registration
- Rotate credentials regularly
- Use service mesh for mTLS

**Agent → Redis:**
- Enable Redis AUTH: `redis://:password@redis:6379`
- Use Redis ACLs to limit permissions
- Use TLS: `rediss://redis:6379`
- Consider Redis Sentinel for HA

## Performance Characteristics

### Policy Enforcement
- **Local evaluation**: < 1ms (99th percentile)
- **No network calls** during evaluation
- **Background sync**: Every 30 seconds (configurable)
- **Update latency**: < 1 second via Pub/Sub

### Event Publishing
- **Non-blocking**: Events buffered in memory
- **Batch publishing**: Every 5 seconds (configurable)
- **Buffer size**: 100 events (configurable)
- **Network overhead**: Minimal (batched)

### Configuration Fetching
- **Cache TTL**: 60 seconds (configurable)
- **HTTP latency**: ~10-50ms (depends on network)
- **Cache hit rate**: High for stable configs
- **Invalidation**: Manual or via Pub/Sub

## Troubleshooting Guide

### Connection Test Checklist

Run this command to test all connections:
```bash
./scripts/test_connectivity.sh
```

Or manually:

1. **Test Gateway HTTP:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **Test Redis:**
   ```bash
   redis-cli ping
   ```

3. **Test Policy Endpoint:**
   ```bash
   curl http://localhost:8080/api/v1/policies?agent_id=test
   ```

4. **Test Redis Streams:**
   ```bash
   redis-cli XREAD COUNT 1 STREAMS agion:events:trust 0-0
   ```

5. **Test Redis Pub/Sub:**
   ```bash
   redis-cli SUBSCRIBE agion:policy:updates
   ```

### Common Issues

**Issue**: SDK initialization fails
**Fix**: Check Gateway URL and Redis URL are correct

**Issue**: Policies not syncing
**Fix**: Verify Governance Service is running and policies exist

**Issue**: Events not appearing in Redis
**Fix**: Wait 5 seconds for flush, or reduce `event_flush_interval`

**Issue**: Config fetching returns 404
**Fix**: Create the prompt/model/resource in admin UI first

## Metrics & Monitoring

### SDK Metrics

```python
metrics = sdk.get_metrics()

# Policy Engine Metrics
metrics["policy_engine"]["total_evaluations"]    # Total checks
metrics["policy_engine"]["average_latency_ms"]   # Avg latency

# Event Client Metrics
metrics["event_client"]["published"]             # Published count
metrics["event_client"]["failed"]                # Failed count
metrics["event_client"]["buffer_size"]           # Current buffer

# Cache Metrics
metrics["cache_sizes"]["prompts"]                # Cached prompts
metrics["cache_sizes"]["models"]                 # Cached models
```

### Backend Health Checks

```bash
# Gateway health
curl http://localhost:8080/health

# Redis health
redis-cli ping

# Governance health (if exposed)
curl http://localhost:8083/health
```

## Quick Reference

### SDK Initialization

```python
from agion_sdk import AgionSDK

sdk = AgionSDK(
    agent_id="langgraph-v2:my_agent",
    gateway_url="http://gateway:8080",  # ← HTTP to Gateway
    redis_url="redis://redis:6379"       # ← Direct to Redis
)

await sdk.initialize()
```

### Environment Variables

```bash
export AGION_GATEWAY_URL="http://gateway:8080"
export AGION_REDIS_URL="redis://redis:6379"
```

### Test Connection

```bash
cd platform-new/agion-sdk-python
./scripts/test_connectivity.sh
```

---

**Need Help?**
- Run connectivity test: `./scripts/test_connectivity.sh`
- Check integration tests: `pytest tests/test_integration.py -v`
- Review logs: Enable debug logging with `logging.getLogger("agion_sdk").setLevel(logging.DEBUG)`
