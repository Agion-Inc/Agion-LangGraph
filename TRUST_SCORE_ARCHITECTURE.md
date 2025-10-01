# Trust Score Architecture - Where is it Managed?

## Quick Answer

**Trust scores are managed in the Agion Platform (Governance Service), NOT in the SDK.**

The SDK is a **"dumb" event publisher** - it only:
1. Reports events (success, failure, feedback) to Redis Streams
2. Does NOT calculate trust scores
3. Does NOT store trust scores
4. Does NOT make trust-based decisions

The **Agion Platform Governance Service** is the **"smart" brain** that:
1. Consumes events from Redis Streams
2. Calculates trust scores based on events
3. Stores trust scores in the platform database
4. Makes trust-based routing decisions

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Container                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Agent Executes                                            │ │
│  │    ↓                                                       │ │
│  │  @governed_node decorator                                 │ │
│  │    ↓                                                       │ │
│  │  metrics_reporter.report_execution_success()              │ │
│  │    ↓                                                       │ │
│  │  SDK.publish_trust_event(                                 │ │
│  │      agent_id="langgraph-v2:chart_agent",                │ │
│  │      event_type="task_completed",                        │ │
│  │      impact=0.02  // +2% (JUST A SUGGESTION!)           │ │
│  │  )                                                         │ │
│  │    ↓                                                       │ │
│  │  Event → Redis Stream: agion:events:trust                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                   [Redis Streams]
                   agion:events:trust
                   agion:events:feedback
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              Agion Platform - Governance Service                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Consume Events from Redis Streams                     │ │
│  │     XREAD STREAMS agion:events:trust                      │ │
│  │                                                            │ │
│  │  2. Trust Score Calculation Logic (THE BRAIN!)           │ │
│  │     • Parse event: agent_id, event_type, impact          │ │
│  │     • Load current trust score from database             │ │
│  │     • Apply rules:                                        │ │
│  │       - task_completed: +2%                              │ │
│  │       - task_failed: -2%                                 │ │
│  │       - error: -3%                                       │ │
│  │       - governance_violation: -5%                        │ │
│  │       - positive_feedback (rating≥4): +0.5%             │ │
│  │     • Calculate new score                                │ │
│  │     • Validate bounds (0.0 - 1.0)                        │ │
│  │                                                            │ │
│  │  3. Store Updated Trust Score in Database                │ │
│  │     UPDATE agent_trust_scores SET                         │ │
│  │       score = new_score,                                  │ │
│  │       updated_at = NOW()                                  │ │
│  │     WHERE agent_id = 'langgraph-v2:chart_agent'          │ │
│  │                                                            │ │
│  │  4. Publish Trust Score Update Event                     │ │
│  │     (Optional: notify other services)                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Platform Database                                         │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  agent_trust_scores                                  │ │ │
│  │  │  ────────────────────────────────────────────────    │ │ │
│  │  │  agent_id                | trust_score | updated_at │ │ │
│  │  │  ────────────────────────────────────────────────    │ │ │
│  │  │  langgraph-v2:chart_agent    | 0.62   | 2025-10-01 │ │ │
│  │  │  langgraph-v2:supervisor     | 0.58   | 2025-10-01 │ │ │
│  │  │  langgraph-v2:general_agent  | 0.65   | 2025-10-01 │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Trust Score Update

### Step-by-Step Flow

**1. Agent Execution (LangGraph Container)**
```python
# backend/langgraph_agents/governance_wrapper.py
async def wrapper(state):
    execution_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Execute agent
        result = await func(state)

        # Report success to SDK
        await metrics_reporter.report_execution_success(
            agent_id="langgraph-v2:chart_agent",
            execution_id=execution_id,
            start_time=start_time,
            result=result
        )
    except Exception as e:
        # Report error to SDK
        await metrics_reporter.report_execution_error(...)
```

**2. Metrics Reporter Publishes Event**
```python
# backend/langgraph_agents/metrics_reporter.py
async def report_execution_success(...):
    sdk = await get_agion_sdk()

    # Publish to Redis Stream with SUGGESTED impact
    await sdk.event_client.publish_trust_event(
        agent_id=agent_id,
        event_type="task_completed",
        severity="positive",
        impact=0.02,  # Suggestion: +2%
        confidence=1.0,
        context={...}
    )
```

**3. SDK Publishes to Redis Stream**
```python
# agion-sdk-python/agion_sdk/events.py
async def publish_trust_event(...):
    event = TrustEvent(
        agent_id=agent_id,
        event_type=event_type,
        severity=severity,
        impact=impact,  # Just metadata, not enforced
        confidence=confidence,
        context=context,
        timestamp=datetime.utcnow()
    )

    # Fire-and-forget to Redis
    await self._publish_event("agion:events:trust", event.model_dump())
```

**4. Governance Service Consumes Event (Platform)**
```python
# platform/governance-service/trust_score_calculator.py (EXAMPLE)
async def process_trust_events():
    # Consume from Redis Stream
    events = await redis.xread(
        {'agion:events:trust': last_id},
        count=100,
        block=1000
    )

    for event in events:
        agent_id = event['agent_id']
        event_type = event['event_type']
        suggested_impact = float(event['impact'])  # SDK suggestion

        # Load current trust score from database
        current_score = await db.get_trust_score(agent_id)

        # Calculate new score (GOVERNANCE DECIDES, NOT SDK!)
        if event_type == "task_completed":
            new_score = current_score + 0.02  # +2%
        elif event_type == "task_failed":
            new_score = current_score - 0.02  # -2%
        elif event_type == "error":
            new_score = current_score - 0.03  # -3%
        elif event_type == "governance_violation":
            new_score = current_score - 0.05  # -5%
        elif event_type == "positive_feedback":
            new_score = current_score + 0.005  # +0.5%

        # Clamp to [0.0, 1.0]
        new_score = max(0.0, min(1.0, new_score))

        # Store in database
        await db.update_trust_score(agent_id, new_score)

        logger.info(f"Trust score updated: {agent_id} {current_score} → {new_score}")
```

**5. Platform Database Stores Score**
```sql
-- Platform database (NOT LangGraph database)
UPDATE agent_trust_scores
SET score = 0.62,
    execution_count = execution_count + 1,
    last_event_type = 'task_completed',
    updated_at = NOW()
WHERE agent_id = 'langgraph-v2:chart_agent';
```

## Key Design Principles

### 1. SDK is "Dumb" (Event Publisher)
```python
# SDK ONLY publishes events - it does NOT:
# ❌ Calculate trust scores
# ❌ Store trust scores
# ❌ Make routing decisions
# ❌ Enforce trust thresholds
# ❌ Query trust scores

# SDK ONLY:
# ✅ Publishes events to Redis Streams
# ✅ Includes suggested impact values (metadata)
# ✅ Fire-and-forget (non-blocking)
# ✅ Local policy enforcement (< 1ms)
```

### 2. Platform is "Smart" (Trust Manager)
```python
# Governance Service:
# ✅ Consumes events from Redis Streams
# ✅ Calculates actual trust scores
# ✅ Stores trust scores in database
# ✅ Makes routing decisions based on trust
# ✅ Enforces trust thresholds
# ✅ Provides trust score API
# ✅ Historical tracking and analytics
```

### 3. Separation of Concerns

| Responsibility | LangGraph Container (SDK) | Platform (Governance) |
|----------------|---------------------------|----------------------|
| Event Publishing | ✅ YES | ❌ NO |
| Trust Calculation | ❌ NO | ✅ YES |
| Trust Storage | ❌ NO | ✅ YES |
| Trust Queries | ❌ NO | ✅ YES |
| Routing Decisions | ❌ NO | ✅ YES |
| Policy Enforcement | ✅ YES (local) | ✅ YES (global) |

## Why This Architecture?

### Benefits of "Dumb" SDK

1. **Simplicity**: Agent containers don't need complex trust logic
2. **Flexibility**: Platform can change trust algorithms without updating agents
3. **Consistency**: Single source of truth (platform database)
4. **Scalability**: Stateless agent containers
5. **Security**: Agents can't manipulate their own scores

### Benefits of "Smart" Platform

1. **Centralized Logic**: Trust calculation in one place
2. **Auditability**: All trust changes tracked in platform
3. **Flexibility**: Easy to adjust trust formulas
4. **Cross-Agent Intelligence**: Platform sees all agent scores
5. **Historical Analysis**: Platform stores full event history

## Trust Score Queries

### How to Get Trust Scores?

**Agent containers CANNOT query trust scores directly**. They publish events and let the platform handle the rest.

**Platform Admin/Dashboard queries trust scores:**

```python
# Platform API (not in LangGraph container)
GET /api/v1/agents/langgraph-v2:chart_agent/trust-score

Response:
{
  "agent_id": "langgraph-v2:chart_agent",
  "trust_score": 0.62,
  "status": "graduated",  // >= 0.6
  "execution_count": 15,
  "success_rate": 0.93,
  "last_updated": "2025-10-01T12:34:56Z"
}
```

## Summary Table

| Component | Role | Responsibility |
|-----------|------|----------------|
| **LangGraph Agent** | Event Generator | Execute tasks, report results |
| **SDK (agion-sdk-python)** | Event Publisher | Publish events to Redis Streams |
| **Redis Streams** | Message Bus | Deliver events to platform |
| **Governance Service** | Trust Manager | Calculate, store, manage trust scores |
| **Platform Database** | Trust Store | Store trust scores and history |
| **Platform API** | Trust Query | Provide trust score access |

## Trust Score Philosophy

**Location**: Documented in SDK (for reference), **enforced in Platform**

```
Starting Trust: 0.4 (40% baseline)
Graduation: 0.6 (60% proven reliability)

Impact Values (enforced by Governance Service):
- task_completed: +2%
- task_failed: -2%
- error: -3%
- governance_violation: -5%
- positive_feedback (rating≥4): +0.5%

After 10 successes: 0.4 + (10 × 0.02) = 0.6 ✅ Graduated
```

## Conclusion

**Trust scores are managed in the Agion Platform, NOT in the SDK.**

- **SDK**: "Dumb" event publisher (fire-and-forget)
- **Platform**: "Smart" trust manager (calculation, storage, decisions)
- **Redis**: Message bus connecting them

This architecture provides:
- ✅ Separation of concerns
- ✅ Centralized trust management
- ✅ Stateless agent containers
- ✅ Flexible trust algorithms
- ✅ Single source of truth

The SDK documentation includes trust score philosophy for **reference**, but the **actual calculation happens in the platform**.
