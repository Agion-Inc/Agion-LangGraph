# Agion SDK - Backend Integration Guide

This document explains how to connect the Agion SDK to the platform backend services.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Container                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              LangGraph/LangChain Agent               │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │           Agion SDK                          │  │   │
│  │  │                                              │  │   │
│  │  │  • Local Policy Engine (< 1ms checks)      │  │   │
│  │  │  • Background Policy Sync                   │  │   │
│  │  │  • Event Publisher (Redis Streams)          │  │   │
│  │  │  • Config Fetcher (Prompts/Models)          │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ HTTP (Config/Registration)
                        │ Redis Pub/Sub (Policy Updates)
                        │ Redis Streams (Events)
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Platform Backend Services                  │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐│
│  │ Gateway Service  │  │ Governance       │  │  Redis    ││
│  │ :8080            │  │ Service          │  │  :6379    ││
│  │                  │  │ :8083            │  │           ││
│  │ • Agent Reg      │  │ • Policies       │  │ • Streams ││
│  │ • Prompts        │  │ • Trust Events   │  │ • Pub/Sub ││
│  │ • Models         │  │ • Evaluation     │  │ • Cache   ││
│  │ • Resources      │  │                  │  │           ││
│  └──────────────────┘  └──────────────────┘  └───────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Backend API Endpoints Used by SDK

### 1. Gateway Service (Default: `http://gateway:8080`)

#### Agent Registration
- **POST** `/api/v1/agents/register`
- Called during SDK initialization
- Registers agent with platform
- **Request:**
  ```json
  {
    "name": "test_agent",
    "type": "ai",
    "capabilities": ["data_analysis", "chart_generation"],
    "version": "1.0.0",
    "owner": "system",
    "metadata": {}
  }
  ```

#### Get Prompt Configuration
- **GET** `/api/v1/prompts/by-location/{location}`
- Fetches dynamic prompt by name/location
- **Response:**
  ```json
  {
    "id": "prompt-123",
    "name": "chart_generation",
    "content": "Generate a chart based on...",
    "variables": ["data", "chart_type"],
    "version": "1.0.0"
  }
  ```

#### Get Model Configuration
- **GET** `/api/v1/models/by-purpose/{purpose}`
- Fetches AI model config by purpose
- **Response:**
  ```json
  {
    "id": "model-456",
    "name": "gpt-4",
    "provider": "openai",
    "model_name": "gpt-4-turbo",
    "parameters": {"temperature": 0.7},
    "credentials": {"api_key": "sk-..."}
  }
  ```

#### Get Resource Configuration
- **GET** `/api/v1/resources/by-name/{name}`
- Fetches external resource config
- **Response:**
  ```json
  {
    "id": "resource-789",
    "name": "analytics_db",
    "resource_type": "postgresql",
    "connection_string": "postgresql://...",
    "credentials": {"username": "...", "password": "..."}
  }
  ```

### 2. Governance Service (Default: `http://governance:8083`)

#### List Policies for Agent
- **GET** `/api/v1/policies?agent_id={agent_id}&status=active`
- Called by policy sync worker
- **Response:**
  ```json
  {
    "policies": [
      {
        "id": "policy-123",
        "name": "Data Access Policy",
        "policy_expression": "role in ['admin', 'analyst']",
        "enforcement": "hard",
        "priority": 100,
        "status": "active"
      }
    ],
    "total": 1
  }
  ```

### 3. Redis Streams (Default: `redis://redis:6379`)

#### Trust Events Stream
- **Stream:** `agion:events:trust`
- **Fields:**
  - `agent_id`: Agent identifier
  - `event_type`: Type of event (task_completed, task_failed, etc.)
  - `severity`: Event severity (positive, negative, critical)
  - `impact`: Trust score impact (-1.0 to +1.0)
  - `confidence`: Confidence level (0.0 to 1.0)
  - `context`: JSON context data
  - `timestamp`: ISO timestamp

#### User Feedback Stream
- **Stream:** `agion:events:feedback`
- **Fields:**
  - `execution_id`: Execution identifier
  - `user_id`: User who provided feedback
  - `feedback_type`: Type (thumbs_up, thumbs_down)
  - `rating`: Optional 1-5 rating
  - `comment`: Optional comment
  - `timestamp`: ISO timestamp

#### Mission Events Stream
- **Stream:** `agion:events:missions`
- **Fields:**
  - `mission_id`: Mission identifier
  - `event_type`: Event type (joined, left, state_updated)
  - `participant_id`: Agent identifier
  - `data`: JSON event data
  - `timestamp`: ISO timestamp

#### Mission Messages Stream
- **Stream:** `agion:missions:{mission_id}:messages`
- **Fields:**
  - `mission_id`: Mission identifier
  - `from_participant`: Sender agent ID
  - `to_participant`: Recipient agent ID (null = broadcast)
  - `message_type`: Message type
  - `content`: JSON message content
  - `timestamp`: ISO timestamp

#### Policy Update Pub/Sub
- **Channel:** `agion:policy:updates`
- **Message:**
  ```json
  {
    "event": "policy_updated",
    "policy_id": "policy-123",
    "agent_id": "langgraph-v2:my_agent",
    "timestamp": "2025-09-30T10:00:00Z"
  }
  ```

## SDK Configuration

### Basic Configuration

```python
from agion_sdk import AgionSDK

sdk = AgionSDK(
    agent_id="langgraph-v2:my_agent",
    agent_version="1.0.0",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379",
)

await sdk.initialize()
```

### Full Configuration Options

```python
from agion_sdk import SDKConfig, AgionSDK

config = SDKConfig(
    # Required
    agent_id="langgraph-v2:my_agent",
    agent_version="1.0.0",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379",

    # Policy sync settings
    policy_sync_enabled=True,
    policy_sync_interval=30,  # seconds
    policy_cache_ttl=60,      # seconds

    # Event publishing settings
    event_buffer_size=100,
    event_flush_interval=5,   # seconds

    # Configuration cache settings
    config_cache_ttl=60,      # seconds

    # Performance settings
    max_policy_eval_time_ms=1.0,
    enable_metrics=True,

    # Fail-safe settings
    offline_mode=False,
    fail_open=False,  # If True, allow on policy fetch failure
)

sdk = AgionSDK(**config.model_dump())
await sdk.initialize()
```

### Environment Variables

```bash
# Gateway Service
export AGION_GATEWAY_URL="http://gateway:8080"

# Redis
export AGION_REDIS_URL="redis://redis:6379"

# Optional: Redis with password
export AGION_REDIS_URL="redis://:password@redis:6379"

# Optional: Redis Sentinel
export AGION_REDIS_URL="redis-sentinel://sentinel1:26379,sentinel2:26379/mymaster"
```

## Docker Deployment

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Your agent container
  my-agent:
    build: .
    environment:
      - AGION_GATEWAY_URL=http://gateway:8080
      - AGION_REDIS_URL=redis://redis:6379
      - AGENT_ID=langgraph-v2:my_agent
      - AGENT_VERSION=1.0.0
    depends_on:
      - gateway
      - redis
    networks:
      - agion-network

  # Gateway Service (from platform)
  gateway:
    image: agion/gateway:latest
    ports:
      - "8080:8080"
    environment:
      - GOVERNANCE_SERVICE_URL=http://governance:8083
      - REDIS_URL=redis://redis:6379
    networks:
      - agion-network

  # Governance Service (from platform)
  governance:
    image: agion/governance:latest
    ports:
      - "8083:8083"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@db:5432/agion
    networks:
      - agion-network

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - agion-network

networks:
  agion-network:
    driver: bridge
```

### Agent Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install SDK
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy agent code
COPY . .

# Run agent
CMD ["python", "main.py"]
```

### requirements.txt

```
agion-sdk
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
```

## Testing Backend Connectivity

### 1. Run Integration Tests

```bash
cd platform-new/agion-sdk-python

# Set environment variables
export AGION_GATEWAY_URL="http://localhost:8080"
export AGION_REDIS_URL="redis://localhost:6379"

# Install test dependencies
pip install -e ".[dev]"

# Run integration tests
pytest tests/test_integration.py -v

# Run specific test
pytest tests/test_integration.py::TestSDKInitialization::test_initialize_success -v
```

### 2. Manual Testing Script

```python
import asyncio
from agion_sdk import AgionSDK

async def test_connectivity():
    sdk = AgionSDK(
        agent_id="test:connectivity_test",
        gateway_url="http://localhost:8080",
        redis_url="redis://localhost:6379",
    )

    try:
        # Test initialization
        print("Initializing SDK...")
        await sdk.initialize()
        print("✓ SDK initialized")

        # Test policy sync
        print("Waiting for policy sync...")
        await asyncio.sleep(3)
        policies = sdk.policy_engine.get_policies()
        print(f"✓ Loaded {len(policies)} policies")

        # Test event publishing
        print("Publishing test event...")
        await sdk.event_client.publish_trust_event(
            agent_id=sdk.config.agent_id,
            event_type="task_completed",
            severity="positive",
            impact=0.01,
            confidence=1.0,
        )
        await asyncio.sleep(6)  # Wait for flush
        print("✓ Event published")

        # Test metrics
        metrics = sdk.get_metrics()
        print(f"✓ Metrics: {metrics}")

        print("\n✅ All connectivity tests passed!")

    finally:
        await sdk.shutdown()

if __name__ == "__main__":
    asyncio.run(test_connectivity())
```

### 3. Verify Backend Endpoints

```bash
# Test Gateway health
curl http://localhost:8080/health

# Test policy endpoint (requires auth)
curl -H "Authorization: Bearer <token>" \
     http://localhost:8080/api/v1/policies?agent_id=test:my_agent

# Test Redis connectivity
redis-cli ping

# Watch Redis Streams
redis-cli XREAD COUNT 10 STREAMS agion:events:trust 0-0
```

## Troubleshooting

### SDK won't initialize

**Symptom:** `InitializationError` on `await sdk.initialize()`

**Solutions:**
1. Check Redis connectivity: `redis-cli ping`
2. Verify Gateway URL is accessible: `curl http://gateway:8080/health`
3. Check network connectivity from agent container to backend services
4. Review SDK logs for connection errors

### Policies not syncing

**Symptom:** `sdk.policy_engine.get_policies()` returns empty list

**Solutions:**
1. Verify Governance Service is running
2. Check if policies exist for your agent:
   ```bash
   curl http://localhost:8080/api/v1/policies?agent_id=your-agent-id
   ```
3. Check Redis Pub/Sub is working: `redis-cli SUBSCRIBE agion:policy:updates`
4. Enable policy sync logging: `logging.getLogger("agion_sdk.policy_sync").setLevel(logging.DEBUG)`

### Events not publishing

**Symptom:** Events don't appear in Redis Streams

**Solutions:**
1. Check event client metrics: `sdk.event_client.get_metrics()`
2. Verify Redis connection: `await sdk.event_client._redis.ping()`
3. Check Redis Streams manually: `redis-cli XREAD STREAMS agion:events:trust 0-0`
4. Reduce flush interval for testing: `event_flush_interval=1`

### Configuration fetching fails

**Symptom:** `ResourceNotFoundError` when fetching prompts/models

**Solutions:**
1. Verify Gateway Service is running
2. Check if resource exists in admin UI
3. Test endpoint manually:
   ```bash
   curl http://localhost:8080/api/v1/prompts/by-location/your-prompt-name
   ```
4. Check for typos in resource names

## Production Checklist

- [ ] Gateway Service accessible from agent containers
- [ ] Redis accessible from agent containers
- [ ] Agent registration endpoint working
- [ ] Policy sync enabled and working
- [ ] Event publishing to Redis Streams working
- [ ] Configuration endpoints (prompts, models, resources) accessible
- [ ] Network policies allow agent → gateway, agent → redis communication
- [ ] Proper error handling and retry logic configured
- [ ] Monitoring and logging enabled
- [ ] Resource limits configured appropriately
- [ ] Security: Use TLS for production (wss://, https://)
- [ ] Security: Use Redis AUTH for production

## Support

For issues:
- Check integration tests: `pytest tests/test_integration.py -v`
- Review SDK logs: `logging.getLogger("agion_sdk").setLevel(logging.DEBUG)`
- Verify backend health: Check Gateway and Governance Service logs
- Test Redis: Use `redis-cli` to verify streams and pub/sub
