# Agion SDK - Quick Start Guide

Get your LangGraph/LangChain agents connected to Agion platform in 5 minutes.

## Installation

```bash
pip install agion-sdk
```

Or from source:

```bash
cd platform-new/agion-sdk-python
pip install -e .
```

## Basic Usage

### 1. Initialize SDK

```python
from agion_sdk import AgionSDK

sdk = AgionSDK(
    agent_id="langgraph-v2:my_agent",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379"
)

await sdk.initialize()
```

### 2. Add Governance to Your Agent Functions

```python
@sdk.governed("my_agent", "process_data")
async def process_data(state):
    # Your agent logic here
    # Policies are automatically checked before execution
    return {"result": "processed"}
```

### 3. Use Dynamic Configuration

```python
# Fetch current prompt (updates without code changes)
prompt = await sdk.get_prompt(location="data_processing")

# Fetch current model config
model = await sdk.get_model(purpose="analysis")

# Use in your LLM calls
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=model.model_name,
    temperature=model.parameters.get("temperature", 0.7),
    api_key=model.credentials["api_key"]
)
```

### 4. Complete LangGraph Example

```python
from langgraph.graph import StateGraph
from agion_sdk import AgionSDK, UserContext

# Initialize SDK
sdk = AgionSDK(agent_id="langgraph-v2:my_agent")
await sdk.initialize()

# Define governed nodes
@sdk.governed("my_agent", "analyze")
async def analyze_node(state):
    # Your logic
    return {"analysis": "result"}

@sdk.governed("my_agent", "generate")
async def generate_node(state):
    # Your logic
    return {"output": "generated"}

# Build graph
graph = StateGraph(YourState)
graph.add_node("analyze", analyze_node)
graph.add_node("generate", generate_node)
graph.add_edge("analyze", "generate")
graph.set_entry_point("analyze")

# Compile and run
app = graph.compile()

# Pass user context
user = UserContext(
    user_id="user-123",
    org_id="org-456",
    role="analyst",
    permissions=["read", "write"]
)

result = await app.ainvoke(
    {"query": "Analyze this data"},
    {"_agion_user": user}
)
```

## Test Backend Connectivity

Before deploying, verify SDK can connect to your backend:

```bash
# Set environment variables
export AGION_GATEWAY_URL="http://localhost:8080"
export AGION_REDIS_URL="redis://localhost:6379"

# Run connectivity test
./scripts/test_connectivity.sh
```

Or use Python:

```bash
python -m tests.test_backend_connectivity
```

## Configuration Options

### Environment Variables

```bash
export AGION_GATEWAY_URL="http://gateway:8080"
export AGION_REDIS_URL="redis://redis:6379"
```

### In Code

```python
from agion_sdk import SDKConfig

config = SDKConfig(
    agent_id="langgraph-v2:my_agent",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379",

    # Optional: Tune performance
    policy_sync_interval=30,      # seconds
    policy_cache_ttl=60,           # seconds
    event_flush_interval=5,        # seconds
    max_policy_eval_time_ms=1.0,   # milliseconds
)

sdk = AgionSDK(**config.model_dump())
```

## Key Features

### ✅ Local-First Governance
- Policy checks in < 1ms (in-process evaluation)
- No network latency for permission checks
- Background sync keeps policies fresh

### ✅ Dynamic Configuration
- Fetch prompts, models, resources without code changes
- Admin updates via UI → agents pick up changes automatically
- 60-second cache TTL (configurable)

### ✅ Automatic Event Publishing
- Trust events sent to Redis Streams
- Fire-and-forget (doesn't block execution)
- Buffered for performance (5-second flush)

### ✅ User Context Flow
- User permissions enforced at agent level
- RBAC checks before execution
- User feedback integrated into trust scores

### ✅ Mission Coordination
- Multi-agent coordination support
- State management
- Message passing between agents

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy agent code
COPY . .

# Run agent
CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  my-agent:
    build: .
    environment:
      - AGION_GATEWAY_URL=http://gateway:8080
      - AGION_REDIS_URL=redis://redis:6379
    networks:
      - agion-network

networks:
  agion-network:
    external: true
```

## Next Steps

1. **Review Examples**: Check `examples/` directory for complete samples
2. **Read Integration Guide**: See `BACKEND_INTEGRATION.md` for detailed backend setup
3. **Run Tests**: Execute `pytest tests/test_integration.py -v`
4. **Deploy**: Use provided Docker setup to deploy your agent

## Troubleshooting

### SDK won't initialize

```bash
# Check Gateway connectivity
curl http://localhost:8080/health

# Check Redis connectivity
redis-cli ping
```

### Policies not loading

```bash
# Check if policies exist
curl http://localhost:8080/api/v1/policies?agent_id=your-agent-id

# Check Redis Pub/Sub
redis-cli SUBSCRIBE agion:policy:updates
```

### Events not publishing

```python
# Check event metrics
metrics = sdk.event_client.get_metrics()
print(metrics)

# Check Redis Streams
# redis-cli XREAD STREAMS agion:events:trust 0-0
```

## Support

- **Documentation**: `BACKEND_INTEGRATION.md`
- **Examples**: `examples/` directory
- **Tests**: `tests/` directory
- **Issues**: Report at platform repository

## License

MIT
