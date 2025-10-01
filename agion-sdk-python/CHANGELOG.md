# Changelog

All notable changes to the Agion SDK will be documented in this file.

## [0.2.0] - 2025-10-01

### Added - Unified Governance System

- **Complete GovernanceClient** with 24 HTTP endpoints for resource and permission management
- **Resource Management**: CRUD operations for governed resources (model_provider, ai_model, database, api, storage, mcp_server, tool, webhook, compute)
- **Permission Lifecycle**: Request → Approve → Use → Track workflow with status management
- **Permission Checking**: Critical `check_permission()` method with L1 cache (30s TTL for approved, 5s for denied)
- **Usage Tracking**: Async `update_usage()` for requests, tokens, and costs (fire-and-forget pattern)
- **Policy Management**: List, create, evaluate CEL-based policies
- **Data Models**: Complete Pydantic models (GovernanceResource, GovernancePermission, Policy, etc.)
- **Exception Hierarchy**: `GovernanceAPIError`, `PermissionDeniedError`, `RateLimitError`, `ServiceUnavailableError`
- **Performance Optimizations**:
  - L1 permission cache with <1μs cache hits
  - Async usage updates (non-blocking)
  - Connection pooling with aiohttp
  - Cache statistics tracking (`get_cache_stats()`)

### Enhanced

- **AgionSDK**: Added optional `governance` client (enabled with `enable_governance=True` + `organization_id`)
- **Exports**: Added governance enums (ResourceType, ActorType, PermissionType, ResourceStatus, PermissionStatus, RiskLevel)
- **Documentation**: Created comprehensive [USAGE.md](./USAGE.md) with integration examples
- **Error Handling**: Improved error mapping for governance API responses (400, 403, 404, 429, 503)
- **Version**: Bumped to 0.2.0

### Integration Points

- Agents can request permissions to use governed resources
- Trust-based access control (agents with higher trust scores can access more sensitive resources)
- Rate limiting and budget constraints enforced at permission check time
- Complete audit trail for all resource access via usage tracking
- Resource hierarchy support (parent-child relationships)

### Breaking Changes

None (unified governance is opt-in via `enable_governance=True`)

### Migration Guide

To enable unified governance:

```python
# Before (v0.1.0)
sdk = AgionSDK(
    agent_id="my-agent",
    gateway_url="http://gateway:8080"
)

# After (v0.2.0) - Opt-in governance
sdk = AgionSDK(
    agent_id="my-agent",
    gateway_url="http://gateway:8080",
    organization_id="org-123",      # Required for governance
    enable_governance=True           # Opt-in
)

# Use governance client
result = await sdk.governance.check_permission(
    actor_id="my-agent",
    actor_type=ActorType.AGENT,
    resource_id="gpt-4-resource-id",
    permission_type=PermissionType.USE
)
```

---

## [0.1.0] - 2025-09-25

### Added
- Initial release of Agion SDK for Python
- Governance client with local policy engine and policy sync
- Event client for publishing trust events, user feedback, and LLM interactions to Redis Streams
- Mission coordination client for multi-agent collaboration
- Type definitions for all SDK models with Pydantic validation
- Automatic datetime serialization to ISO format using `model_dump(mode='json')`
- Trust event types: `TASK_COMPLETED`, `TASK_FAILED`, `TIMEOUT_EXCEEDED`, `RESOURCE_OVERUSE`, `POLICY_VIOLATION`, `USER_FEEDBACK`
- Event severities: `POSITIVE`, `NEUTRAL`, `NEGATIVE`, `CRITICAL`
- Fire-and-forget event publishing with buffering and automatic retry
- Redis Streams integration for real-time event processing
- Policy sync via Redis Pub/Sub with HTTP fallback
- Local policy evaluation for sub-millisecond latency
- User context with org_id, role, and permissions
- LLM interaction logging for compliance and audit trails
- **Async context manager support** for elegant resource management (`async with AgionSDK() as sdk`)
- **Input validation** for trust impact (-1.0 to +1.0), confidence (0.0 to 1.0), and rating (1-5)
- **Extended __all__ exports** including `MissionClient`, `EventClient`, `PolicyResult`, and `TrustEvent`

### Requirements
- Python 3.12 or 3.13
- Redis 6.4.0+
- Pydantic 2.11.9+

### Dependencies
- `redis>=6.4.0` - Redis client for event publishing and policy sync
- `aiohttp>=3.12.15` - Async HTTP client for gateway communication
- `pydantic>=2.11.9` - Data validation and serialization

### Breaking Changes
- Requires Python 3.12+ (dropped support for Python 3.9-3.11)
- Event types must use `EventType` enum (string values no longer accepted)
- Event severities must use `EventSeverity` enum (string values no longer accepted)

### Fixed
- Datetime objects now properly serialize to ISO strings in events
- Event type validation enforced via Pydantic enums
- Event severity validation enforced via Pydantic enums
- PolicyResult.matched_policies correctly handled as List[str] instead of List[PolicyRule]
- User feedback rating validation (must be 1-5)
- Trust event impact and confidence validation with Pydantic Field constraints

### API
- Primary method: `disconnect()` - Clean shutdown of SDK and resource cleanup
- Backwards compatible: `shutdown()` - Alias for `disconnect()`
- Context manager: `async with AgionSDK() as sdk` - Automatic initialization and cleanup

### Notes
- This SDK is designed for integration with the Agion AI Platform
- Trust scores are managed platform-side, not in the SDK
- All events are fire-and-forget for non-blocking agent execution
- Context manager usage is recommended for automatic resource cleanup
