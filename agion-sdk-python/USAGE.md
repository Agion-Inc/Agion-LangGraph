# Agion SDK Usage Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Features](#core-features)
3. [Unified Governance](#unified-governance)
4. [Integration Examples](#integration-examples)
5. [Best Practices](#best-practices)

---

## Quick Start

### Basic SDK Usage

```python
from agion_sdk import AgionSDK

# Initialize SDK
async with AgionSDK(
    agent_id="langgraph-v2:my_agent",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379"
) as sdk:
    # Your agent logic here
    pass
```

### With Unified Governance

```python
from agion_sdk import AgionSDK, ActorType, PermissionType, ResourceType

# Initialize SDK with governance
async with AgionSDK(
    agent_id="langgraph-v2:my_agent",
    gateway_url="http://gateway:8080",
    redis_url="redis://redis:6379",
    organization_id="org-abc-123",
    enable_governance=True  # Enable unified governance
) as sdk:
    # Check permission before using resource
    result = await sdk.governance.check_permission(
        actor_id="agent-456",
        actor_type=ActorType.AGENT,
        resource_id="gpt-4-resource-id",
        permission_type=PermissionType.USE,
        context={"request_tokens": 1500, "estimated_cost": 0.045}
    )

    if result.allowed:
        # Use resource
        await make_llm_call()

        # Track usage (async)
        asyncio.create_task(
            sdk.governance.update_usage(
                result.permission.id,
                request_count=1,
                token_count=1234,
                cost_usd=0.037
            )
        )
```

---

## Core Features

### 1. Policy Enforcement

```python
from agion_sdk import AgionSDK

sdk = AgionSDK(agent_id="my-agent")
await sdk.initialize()

# Use decorator for governance
@sdk.governed("my_agent", "process_data")
async def process_data(state):
    # Your logic
    return result

# Or check manually
result = await sdk.check_policy(
    action="access_database",
    resource="customers_db",
    metadata={"query": "SELECT * FROM users"}
)

if result.allowed:
    # Proceed
    pass
```

### 2. Event Publishing

```python
from agion_sdk import EventType, EventSeverity

# Publish trust event
await sdk.event_client.publish_trust_event(
    agent_id="my-agent",
    event_type=EventType.TASK_COMPLETED,
    severity=EventSeverity.POSITIVE,
    impact=0.02,  # +2% trust
    confidence=1.0,
    context={"execution_id": "exec-123"}
)

# Publish user feedback
await sdk.event_client.publish_user_feedback(
    execution_id="exec-123",
    user_id="user-456",
    feedback_type="thumbs_up",
    rating=5,
    comment="Excellent response!"
)
```

### 3. Mission Coordination

```python
# Join a mission
await sdk.mission_client.join_mission(
    mission_id="mission-789",
    role="worker",
    state={"status": "ready"}
)

# Send message
await sdk.mission_client.send_message(
    mission_id="mission-789",
    message_type="status_update",
    content={"progress": 0.5}
)

# Leave mission
await sdk.mission_client.leave_mission("mission-789")
```

---

## Unified Governance

### Architecture

The unified governance system provides centralized control over **all resources** (AI models, databases, APIs, etc.) with:

- **Resource Management**: CRUD operations for governed resources
- **Permission Lifecycle**: Request → Approve → Use → Track
- **Usage Tracking**: Requests, tokens, costs with daily limits
- **Trust-Based Access**: Higher trust = more access
- **Policy Evaluation**: CEL-based access control

### Resource Management

#### Register a Resource

```python
from agion_sdk import ResourceType, RiskLevel

# Create AI model resource
resource = await sdk.governance.create_resource(
    CreateResourceRequest(
        organization_id="org-abc-123",
        resource_type=ResourceType.AI_MODEL,
        name="GPT-4",
        description="OpenAI GPT-4 model",
        resource_data={
            "model_identifier": "gpt-4",
            "provider": "openai",
            "context_window": 8192,
            "cost_per_1k_tokens": 0.03
        },
        compliance_labels=["GDPR", "SOC2"],
        trust_tier_required=60,  # Requires 60% trust score
        risk_level=RiskLevel.MEDIUM,
        tags=["production", "gpt", "openai"],
        created_by="admin-user"
    )
)

print(f"Resource created: {resource.id}")
```

#### List Resources

```python
from agion_sdk import ResourceFilter, ResourceType, ResourceStatus

# Query resources
response = await sdk.governance.list_resources(
    ResourceFilter(
        organization_id="org-abc-123",
        resource_type=ResourceType.AI_MODEL,
        status=ResourceStatus.ACTIVE,
        limit=50
    )
)

for resource in response.resources:
    print(f"{resource.name} ({resource.resource_type}) - Trust: {resource.trust_tier_required}%")
```

### Permission Management

#### Request Permission

```python
from agion_sdk import CreatePermissionRequest, ActorType, PermissionType

# Agent requests permission to use GPT-4
permission = await sdk.governance.request_permission(
    CreatePermissionRequest(
        actor_id="agent-xyz-456",
        actor_type=ActorType.AGENT,
        resource_id=resource.id,
        permission_type=PermissionType.USE,
        purpose="AI model inference for customer support",
        justification="Agent handles complex customer queries",
        constraints=PermissionConstraints(
            rate_limit_rpm=60,
            token_limit_per_day=100000,
            cost_limit_per_day_usd=10.0
        )
    )
)

print(f"Permission requested: {permission.id}, status: {permission.status}")
# Output: Permission requested: perm-uuid-abc, status: pending
```

#### Approve Permission (Admin)

```python
# Admin approves the permission
approved = await sdk.governance.approve_permission(
    permission_id=permission.id,
    approved_by="admin-user-123",
    notes="Approved for production use"
)

print(f"Permission approved: {approved.status}")
# Output: Permission approved: approved
```

#### Check Permission Before Use (Critical)

```python
from agion_sdk import PermissionDeniedError

# ALWAYS check permission before using resource
try:
    result = await sdk.governance.check_permission(
        actor_id="agent-xyz-456",
        actor_type=ActorType.AGENT,
        resource_id=resource.id,
        permission_type=PermissionType.USE,
        context={
            "request_tokens": 1500,
            "estimated_cost": 0.045
        }
    )

    if result.allowed:
        print(f"✅ Permission granted - proceeding")
        print(f"Remaining today: {result.constraints['remaining_tokens_today']} tokens")

        # Make AI model call
        response = await openai.ChatCompletion.create(...)

        # Track usage (async - fire and forget)
        asyncio.create_task(
            sdk.governance.update_usage(
                permission_id=result.permission.id,
                request_count=1,
                token_count=response.usage.total_tokens,
                cost_usd=response.usage.total_tokens * 0.03 / 1000
            )
        )
    else:
        print(f"❌ Permission denied: {result.reason}")

except PermissionDeniedError as e:
    print(f"Access denied: {e}")
except ServiceUnavailableError as e:
    # Governance service down - implement fallback
    if actor_trust_score >= 0.7:
        print("Fail-open for high-trust actor")
    else:
        raise
```

#### List Active Permissions

```python
# Get all active permissions for an agent
response = await sdk.governance.get_active_permissions(
    actor_id="agent-xyz-456"
)

for perm in response.permissions:
    print(f"Resource: {perm.resource_name} ({perm.resource_type})")
    print(f"Permission: {perm.permission_type}, Status: {perm.status}")
    print(f"Usage: {perm.usage_tracking.total_requests} requests")
    print(f"Constraints: {perm.constraints}")
```

### Policy Management

#### Create CEL Policy

```python
from agion_sdk import CreatePolicyRequest, PolicyLanguage

# Create trust-based access policy
policy = await sdk.governance.create_policy(
    CreatePolicyRequest(
        name="Trust Tier Enforcement",
        description="Ensure actor trust score meets resource requirements",
        type="access",
        category="trust_enforcement",
        priority=10,
        enabled=True,
        policy_language=PolicyLanguage.CEL,
        policy_expr="actor.trust_score >= resource.trust_tier_required",
        tags=["trust", "security"],
        created_by="admin-user"
    )
)

print(f"Policy created: {policy.id}")
```

#### Evaluate Policy

```python
# Test policy evaluation
result = await sdk.governance.evaluate_policy(
    policy_id=policy.id,
    context={
        "actor": {
            "trust_score": 75.0,
            "role": "agent"
        },
        "resource": {
            "trust_tier_required": 60.0,
            "risk_level": "medium"
        }
    }
)

print(f"Policy result: {result.result}")  # "allow" or "deny"
print(f"Reason: {result.reason}")
```

---

## Integration Examples

### Example 1: Complete Agent Workflow

```python
import asyncio
from agion_sdk import (
    AgionSDK,
    ActorType,
    PermissionType,
    ResourceType,
    CreateResourceRequest,
    CreatePermissionRequest
)

async def main():
    # Initialize SDK with governance
    async with AgionSDK(
        agent_id="langgraph-v2:support_agent",
        gateway_url="http://gateway:8080",
        redis_url="redis://redis:6379",
        organization_id="org-abc-123",
        enable_governance=True
    ) as sdk:

        # 1. Register GPT-4 resource (admin task, done once)
        resource = await sdk.governance.create_resource(
            CreateResourceRequest(
                organization_id="org-abc-123",
                resource_type=ResourceType.AI_MODEL,
                name="GPT-4",
                resource_data={"model": "gpt-4", "provider": "openai"},
                trust_tier_required=60,
                created_by="admin"
            )
        )

        # 2. Request permission (done once per agent-resource pair)
        permission = await sdk.governance.request_permission(
            CreatePermissionRequest(
                actor_id="support_agent",
                actor_type=ActorType.AGENT,
                resource_id=resource.id,
                permission_type=PermissionType.USE,
                purpose="Customer support AI",
                constraints={"rate_limit_rpm": 30, "cost_limit_per_day_usd": 10.0}
            )
        )

        # 3. Approve permission (admin task)
        await sdk.governance.approve_permission(
            permission_id=permission.id,
            approved_by="admin"
        )

        # 4. Agent runtime: Check permission before each use
        for i in range(5):
            result = await sdk.governance.check_permission(
                actor_id="support_agent",
                actor_type=ActorType.AGENT,
                resource_id=resource.id,
                permission_type=PermissionType.USE
            )

            if result.allowed:
                print(f"Request {i+1}: ✅ Allowed")
                # Make AI call
                await make_llm_call()
                # Track usage (async)
                asyncio.create_task(
                    sdk.governance.update_usage(permission.id, request_count=1, token_count=500)
                )
            else:
                print(f"Request {i+1}: ❌ Denied - {result.reason}")

asyncio.run(main())
```

### Example 2: High-Performance Permission Checking

```python
from agion_sdk import AgionSDK, ActorType, PermissionType

async def process_requests(sdk: AgionSDK, resource_id: str, requests: list):
    """Process multiple requests with cached permission checks."""

    for request in requests:
        # Permission check with L1 cache (30s TTL for approved)
        # First call: API request (~5-15ms)
        # Subsequent calls: Cache hit (<1μs)
        result = await sdk.governance.check_permission(
            actor_id="agent-123",
            actor_type=ActorType.AGENT,
            resource_id=resource_id,
            permission_type=PermissionType.USE,
            context={"request_tokens": request.token_estimate}
        )

        if result.allowed:
            # Process request
            response = await process_llm_request(request)

            # Track usage asynchronously (non-blocking)
            asyncio.create_task(
                sdk.governance.update_usage(
                    permission_id=result.permission.id,
                    request_count=1,
                    token_count=response.tokens,
                    cost_usd=response.cost
                )
            )
        else:
            print(f"Request denied: {result.reason}")

    # Check cache stats
    stats = sdk.governance.get_cache_stats()
    print(f"Cache stats: {stats}")
```

### Example 3: Error Handling

```python
from agion_sdk import (
    AgionSDK,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError
)

async def safe_llm_call(sdk: AgionSDK, resource_id: str, actor_trust_score: float):
    """LLM call with comprehensive error handling."""

    try:
        result = await sdk.governance.check_permission(
            actor_id="agent-123",
            actor_type=ActorType.AGENT,
            resource_id=resource_id,
            permission_type=PermissionType.USE
        )

        if result.allowed:
            # Proceed with LLM call
            return await make_llm_call()
        else:
            print(f"Permission denied: {result.reason}")
            return None

    except PermissionDeniedError as e:
        # Explicit denial (constraint violated)
        print(f"Denied: {e.message}")
        # Maybe retry with different resource or wait
        return None

    except RateLimitError as e:
        # Rate limit exceeded
        print(f"Rate limit exceeded: {e.message}")
        # Implement exponential backoff
        await asyncio.sleep(60)
        return await safe_llm_call(sdk, resource_id, actor_trust_score)

    except ServiceUnavailableError as e:
        # Governance service down - implement circuit breaker
        print(f"Service unavailable: {e.message}")

        # Fail-open for high-trust actors
        if actor_trust_score >= 0.7:
            print("⚠️ Fail-open: allowing high-trust actor during outage")
            return await make_llm_call()
        else:
            print("❌ Fail-closed: denying low-trust actor during outage")
            return None
```

---

## Best Practices

### 1. Always Check Permissions

```python
# ❌ BAD - Direct resource access
response = await openai.ChatCompletion.create(...)

# ✅ GOOD - Checked permission first
result = await sdk.governance.check_permission(...)
if result.allowed:
    response = await openai.ChatCompletion.create(...)
    await sdk.governance.update_usage(...)
```

### 2. Async Usage Tracking

```python
# ❌ BAD - Blocking on usage update
await sdk.governance.update_usage(permission_id, ...)

# ✅ GOOD - Fire and forget
asyncio.create_task(
    sdk.governance.update_usage(permission_id, ...)
)
```

### 3. Cache Leverage

```python
# Permission checks are cached (30s for approved, 5s for denied)
# Subsequent checks for same actor+resource are <1μs

for i in range(100):
    # First call: API (~15ms)
    # Calls 2-100: Cache (<1μs each)
    result = await sdk.governance.check_permission(...)
```

### 4. Error Handling

```python
# Always handle governance errors gracefully
try:
    result = await sdk.governance.check_permission(...)
except ServiceUnavailableError:
    # Implement circuit breaker
    if high_trust:
        # Fail-open
        pass
    else:
        # Fail-closed
        raise
```

### 5. Trust-Based Resource Access

```python
# Use trust tiers to control resource access:
# - GPT-3.5: trust_tier_required=40 (verified agents)
# - GPT-4: trust_tier_required=60 (trusted agents)
# - Database access: trust_tier_required=80 (privileged agents)

# Agents automatically graduate from 40% → 60% trust after 10 successes
# Higher trust = access to more sensitive resources
```

### 6. Resource Hierarchy

```python
# Organize resources in hierarchies:
# OpenAI Provider (parent)
#   ├── GPT-4 (child)
#   ├── GPT-3.5 (child)
#   └── DALL-E (child)

# Permissions can be granted at parent or child level
```

### 7. Monitoring

```python
# Check cache performance
stats = sdk.governance.get_cache_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']}")

# List agent's permissions
permissions = await sdk.governance.get_active_permissions("agent-123")
for perm in permissions.permissions:
    print(f"Resource: {perm.resource_name}")
    print(f"Usage: {perm.usage_tracking}")
```

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Permission check (cold) | 5-15ms | API call to governance service |
| Permission check (cached) | <1μs | L1 cache hit |
| Usage update (async) | Non-blocking | Fire-and-forget |
| Resource CRUD | 8-15ms | Database write |
| Policy evaluation | <1ms | CEL compiled + cached |

**Governance overhead**: <15ms (<1% of typical AI request latency)

---

## Next Steps

- Review [UNIFIED_GOVERNANCE_SDK_INTEGRATION_GUIDE.md](./UNIFIED_GOVERNANCE_SDK_INTEGRATION_GUIDE.md) for complete API reference
- Review [TRUST_SCORING_SDK_INTEGRATION_GUIDE.md](./TRUST_SCORING_SDK_INTEGRATION_GUIDE.md) for trust scoring details
- Check [CHANGELOG.md](./CHANGELOG.md) for version history
