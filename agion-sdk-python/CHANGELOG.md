# Changelog

All notable changes to the Agion SDK will be documented in this file.

## [0.1.0] - 2025-10-01

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
