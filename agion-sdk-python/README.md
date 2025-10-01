# Agion SDK for Python

Lightweight SDK for integrating LangChain/LangGraph agents with Agion's governance, mission coordination, and trust management platform.

**Requirements**: Python 3.12 or 3.13

## Features

- **Local-First Governance**: Policy enforcement in < 1ms with local policy engine
- **Automatic Policy Sync**: Background synchronization via Redis Pub/Sub + HTTP fallback
- **Event Publishing**: Fire-and-forget events to Redis Streams
- **Dynamic Configuration**: Fetch prompts, models, and resources without code changes
- **RBAC Integration**: User permission enforcement at agent execution level
- **Trust Management**: Automatic trust score updates from execution events
- **Mission Coordination**: Participate in multi-agent missions

## Installation

```bash
pip install agion-sdk
```

## Quick Start

```python
from agion_sdk import AgionSDK

# Initialize SDK
sdk = AgionSDK(
    agent_id="langgraph-v2:chart_generator",
    agent_version="1.0.0",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379"
)

# Initialize connection
await sdk.initialize()

# Use governance decorator
@sdk.governed("chart_generator", "generate_chart")
async def chart_agent_node(state):
    # Your agent logic here
    return {"chart": "..."}
```

## LangGraph Integration

```python
from langgraph.graph import StateGraph
from agion_sdk import AgionSDK

sdk = AgionSDK(agent_id="langgraph-v2:my_agent")
await sdk.initialize()

# Create graph with governed nodes
graph = StateGraph()
graph.add_node("start", sdk.governed("agent", "start")(start_node))
graph.add_node("process", sdk.governed("agent", "process")(process_node))
```

## Documentation

See [AGION_SDK_SPECIFICATION.md](../../docs/AGION_SDK_SPECIFICATION.md) for complete API documentation.

## License

MIT
