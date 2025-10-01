# Unified Governance System - SDK Integration Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-01
**Service:** Agion Governance Service - Unified Resource & Permission Management
**Architecture:** Microservices Integration (Option A+)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [Core Concepts](#core-concepts)
4. [HTTP API Reference](#http-api-reference)
5. [CEL Policy Engine](#cel-policy-engine)
6. [Event Publishing](#event-publishing)
7. [SDK Implementation Guidelines](#sdk-implementation-guidelines)
8. [Data Models](#data-models)
9. [Integration Examples](#integration-examples)
10. [Performance & Caching](#performance--caching)
11. [Error Handling](#error-handling)
12. [Testing & Validation](#testing--validation)

---

## Overview

The Unified Governance System provides centralized resource management, permission control, and policy evaluation across the Agion platform. This guide documents all interfaces and integration points needed for SDK implementation.

### Key Features

- **Unified Resource Registry** - Single source of truth for all governed resources
- **Permission Management** - Request-approve-use lifecycle with approval workflow
- **CEL Policy Engine** - Flexible, high-performance policy evaluation (<1ms)
- **Usage Tracking** - Request/token/cost tracking with daily limits
- **Data Loss Prevention** - 6 built-in DLP policies for sensitive data
- **Trust Integration** - Trust-aware permission checks
- **Multi-Tenant** - Organization-level resource isolation

### Performance Characteristics

- **Governance Overhead**: <15ms (< 1% of AI request latency)
- **CEL Policy Evaluation**: <1ms (compiled + cached)
- **Permission Check**: <5ms (database indexed)
- **Cache Hit Rate**: 80-90% (L1) + 10-15% (L2)
- **Throughput**: 1000+ TPS with caching

---

## Architecture Summary

### Service Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Client Application                         │
│                    (Python SDK, etc.)                         │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP REST API
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  Governance Service                           │
│                  (Port 8080/8081)                             │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Resource   │  │  Permission  │  │   Policy     │       │
│  │  Service    │  │  Service     │  │  Service     │       │
│  │             │  │              │  │  + CEL       │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                │                  │                │
│         └────────────────┴──────────────────┘                │
│                          │                                   │
│                          ▼                                   │
│         ┌────────────────────────────────┐                  │
│         │      PostgreSQL Database       │                  │
│         │                                │                  │
│         │  - governance_resources        │                  │
│         │  - governance_permissions      │                  │
│         │  - policies (with CEL)         │                  │
│         │  - trust_scores                │                  │
│         └────────────────────────────────┘                  │
│                                                               │
│         ┌────────────────────────────────┐                  │
│         │       Redis (Events)           │                  │
│         │  - governance-events stream    │                  │
│         │  - trust-events stream         │                  │
│         └────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

### Base URL

```
http(s)://<governance-service-host>:<port>/api/v1
```

Default ports:
- Development: `8080` or `8081`
- Production: Behind load balancer/API gateway

---

## Core Concepts

### 1. Resources

**Definition**: Any governed entity that requires access control.

**Resource Types:**
- `model_provider` - AI model providers (OpenAI, Anthropic, etc.)
- `ai_model` - Specific AI models (GPT-4, Claude, etc.)
- `database` - Database connections
- `api` - External APIs
- `storage` - Storage buckets/volumes
- `mcp_server` - Model Context Protocol servers
- `tool` - External tools/functions
- `webhook` - Webhook endpoints
- `compute` - Compute resources

**Resource Hierarchy:**
Resources can have parent-child relationships:
```
model_provider (OpenAI)
  └── ai_model (GPT-4)
      └── ai_model (GPT-4-turbo)
```

**Resource Properties:**
```json
{
  "id": "uuid",
  "organization_id": "org-uuid",
  "resource_type": "ai_model",
  "parent_resource_id": "parent-uuid",
  "name": "GPT-4",
  "description": "OpenAI GPT-4 model",
  "resource_data": {
    "model_identifier": "gpt-4",
    "context_window": 8192,
    "cost_per_1k_tokens": 0.03
  },
  "compliance_labels": ["GDPR", "SOC2"],
  "data_residency": "US",
  "trust_tier_required": 60,
  "risk_level": "medium",
  "status": "active",
  "health_status": "healthy"
}
```

### 2. Permissions

**Definition**: Access grants linking actors to resources with specific permission types.

**Permission Lifecycle:**
```
pending → approved → active (in use) → revoked
        ↓
      denied
```

**Actor Types:**
- `agent` - AI agents
- `user` - Human users
- `service` - System services

**Permission Types:**
- `use` - Use/consume resource (e.g., call AI model)
- `read` - Read resource metadata
- `write` - Modify resource
- `execute` - Execute operations on resource
- `admin` - Full administrative access

**Constraints:**
Permissions can have usage constraints:
```json
{
  "rate_limit_rpm": 60,
  "token_limit_per_day": 100000,
  "cost_limit_per_day_usd": 10.0,
  "allowed_hours": "09:00-17:00",
  "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
}
```

**Usage Tracking:**
Permissions track cumulative usage:
```json
{
  "total_requests": 1234,
  "total_tokens": 567890,
  "total_cost_usd": 15.25,
  "current_day_requests": 45,
  "current_day_tokens": 23456,
  "current_day_cost_usd": 0.67,
  "last_used_at": "2025-10-01T14:30:00Z",
  "current_day_start": "2025-10-01T00:00:00Z"
}
```

### 3. Policies

**Definition**: Rules that govern resource access and usage.

**Policy Languages:**
- `json` - Legacy JSON-based rules
- `cel` - Google Common Expression Language (recommended)

**Built-in DLP Policies:**
1. **Block API Keys** - `sk-`, `AKIA`, `sk-ant-` patterns
2. **Block SSN** - `XXX-XX-XXXX` format
3. **Block Credit Cards** - Card number patterns
4. **Redact Email Addresses** - Partial email redaction
5. **Block Private Keys** - `-----BEGIN PRIVATE KEY-----`
6. **Block DB Connection Strings** - `postgres://`, `mongodb://`

**Policy Evaluation:**
- Compiled and cached for <1ms evaluation
- Variables: `request`, `actor`, `resource`, `context`
- Boolean result: `allow` or `deny`

### 4. Trust Integration

Governance checks can enforce trust tier requirements:
- Resource specifies `trust_tier_required` (0-100)
- Actor has `trust_score` (from trust scoring system)
- Permission check validates: `actor.trust_score >= resource.trust_tier_required`

**Trust Tiers:**
- `0-20`: untrusted
- `20-40`: basic
- `40-60`: verified
- `60-80`: trusted
- `80-90`: privileged
- `90-100`: admin

---

## HTTP API Reference

### Resource Management

#### 1. Create Resource

Register a new governed resource.

**Endpoint:** `POST /api/v1/resources`

**Request Body:**
```json
{
  "organization_id": "org-abc-123",
  "resource_type": "ai_model",
  "parent_resource_id": "provider-uuid",
  "name": "GPT-4",
  "description": "OpenAI GPT-4 model",
  "resource_data": {
    "model_identifier": "gpt-4",
    "context_window": 8192,
    "cost_per_1k_tokens": 0.03,
    "provider": "openai"
  },
  "compliance_labels": ["GDPR", "SOC2"],
  "data_residency": "US",
  "trust_tier_required": 60,
  "risk_level": "medium",
  "status": "active",
  "tags": ["production", "gpt", "openai"],
  "metadata": {
    "deployment": "production",
    "region": "us-east-1"
  },
  "created_by": "admin-user-123"
}
```

**Response:** `201 Created`
```json
{
  "id": "resource-uuid-123",
  "organization_id": "org-abc-123",
  "resource_type": "ai_model",
  "name": "GPT-4",
  "resource_data": { "model_identifier": "gpt-4", ... },
  "trust_tier_required": 60,
  "risk_level": "medium",
  "status": "active",
  "health_status": "unknown",
  "created_at": "2025-10-01T14:00:00Z",
  "updated_at": "2025-10-01T14:00:00Z"
}
```

---

#### 2. Get Resource

Retrieve resource details.

**Endpoint:** `GET /api/v1/resources/{id}`

**Example:**
```
GET /api/v1/resources/resource-uuid-123
```

**Response:** `200 OK`
```json
{
  "id": "resource-uuid-123",
  "organization_id": "org-abc-123",
  "resource_type": "ai_model",
  "parent_resource_id": "provider-uuid",
  "name": "GPT-4",
  "description": "OpenAI GPT-4 model",
  "resource_data": { ... },
  "compliance_labels": ["GDPR", "SOC2"],
  "trust_tier_required": 60,
  "risk_level": "medium",
  "status": "active",
  "health_status": "healthy",
  "created_at": "2025-10-01T14:00:00Z",
  "updated_at": "2025-10-01T14:00:00Z"
}
```

---

#### 3. List Resources

Query resources with filtering.

**Endpoint:** `GET /api/v1/resources`

**Query Parameters:**
- `organization_id` (required) - Organization UUID
- `resource_type` (optional) - Filter by type
- `status` (optional) - Filter by status: `active`, `inactive`, `pending`, `error`, `deprecated`
- `health_status` (optional) - Filter by health: `healthy`, `degraded`, `unhealthy`, `unknown`
- `risk_level` (optional) - Filter by risk: `low`, `medium`, `high`, `critical`
- `parent_resource_id` (optional) - Filter by parent
- `tags` (optional) - Comma-separated tags
- `compliance_labels` (optional) - Comma-separated labels
- `limit` (optional) - Page size (default: 100, max: 1000)
- `offset` (optional) - Pagination offset (default: 0)

**Example:**
```
GET /api/v1/resources?organization_id=org-abc-123&resource_type=ai_model&status=active&limit=50
```

**Response:** `200 OK`
```json
{
  "resources": [
    {
      "id": "resource-uuid-123",
      "name": "GPT-4",
      "resource_type": "ai_model",
      "status": "active",
      ...
    }
  ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

---

#### 4. Update Resource

Update resource properties.

**Endpoint:** `PUT /api/v1/resources/{id}`

**Request Body:** (all fields optional)
```json
{
  "name": "GPT-4 Turbo",
  "description": "Updated model",
  "resource_data": {
    "model_identifier": "gpt-4-turbo",
    "context_window": 128000
  },
  "trust_tier_required": 70,
  "risk_level": "high",
  "status": "active",
  "health_status": "healthy",
  "health_message": "All systems operational",
  "tags": ["production", "gpt", "turbo"],
  "updated_by": "admin-user-123"
}
```

**Response:** `200 OK` (updated resource)

---

#### 5. Delete Resource

Delete a resource.

**Endpoint:** `DELETE /api/v1/resources/{id}`

**Response:** `204 No Content`

**Note:** Deleting a resource will cascade to dependent permissions.

---

#### 6. Get Resource Children

Get child resources in hierarchy.

**Endpoint:** `GET /api/v1/resources/{id}/children`

**Example:**
```
GET /api/v1/resources/provider-uuid/children
```

**Response:** `200 OK`
```json
{
  "children": [
    {
      "id": "model-uuid-1",
      "name": "GPT-4",
      "resource_type": "ai_model",
      ...
    },
    {
      "id": "model-uuid-2",
      "name": "GPT-3.5",
      "resource_type": "ai_model",
      ...
    }
  ],
  "total": 2
}
```

---

### Permission Management

#### 7. Create Permission (Request Access)

Request permission to access a resource.

**Endpoint:** `POST /api/v1/permissions`

**Request Body:**
```json
{
  "actor_id": "agent-xyz-456",
  "actor_type": "agent",
  "resource_id": "resource-uuid-123",
  "permission_type": "use",
  "purpose": "AI model inference for customer support",
  "justification": "Agent needs GPT-4 access to handle complex customer queries",
  "constraints": {
    "rate_limit_rpm": 60,
    "token_limit_per_day": 100000,
    "cost_limit_per_day_usd": 10.0
  },
  "requested_by": "user-admin-789"
}
```

**Response:** `201 Created`
```json
{
  "id": "perm-uuid-abc",
  "actor_id": "agent-xyz-456",
  "actor_type": "agent",
  "resource_id": "resource-uuid-123",
  "permission_type": "use",
  "status": "pending",
  "purpose": "AI model inference for customer support",
  "constraints": { "rate_limit_rpm": 60, ... },
  "usage_tracking": {
    "total_requests": 0,
    "total_tokens": 0,
    "total_cost_usd": 0
  },
  "requested_at": "2025-10-01T14:30:00Z",
  "created_at": "2025-10-01T14:30:00Z"
}
```

---

#### 8. Check Permission (Critical Endpoint)

**Most important endpoint** - validates if an actor can access a resource.

**Endpoint:** `POST /api/v1/permissions/check`

**Request Body:**
```json
{
  "organization_id": "org-abc-123",
  "actor_id": "agent-xyz-456",
  "actor_type": "agent",
  "resource_id": "resource-uuid-123",
  "permission_type": "use",
  "context": {
    "request_tokens": 1500,
    "estimated_cost": 0.045,
    "client_ip": "192.168.1.100"
  }
}
```

**Response:** `200 OK`
```json
{
  "allowed": true,
  "permission": {
    "id": "perm-uuid-abc",
    "actor_id": "agent-xyz-456",
    "resource_id": "resource-uuid-123",
    "permission_type": "use",
    "status": "approved",
    "constraints": {
      "rate_limit_rpm": 60,
      "token_limit_per_day": 100000,
      "cost_limit_per_day_usd": 10.0
    }
  },
  "reason": "Permission approved and within limits",
  "constraints": {
    "remaining_requests_today": 55,
    "remaining_tokens_today": 76544,
    "remaining_budget_today": 7.33
  },
  "metadata": {
    "trust_score_checked": true,
    "trust_score": 67.8,
    "policies_evaluated": 3
  },
  "timestamp": "2025-10-01T14:35:00Z"
}
```

**Denial Response:**
```json
{
  "allowed": false,
  "permission": null,
  "reason": "Rate limit exceeded: 60 requests per minute",
  "constraints": {},
  "timestamp": "2025-10-01T14:35:00Z"
}
```

**Permission Check Logic:**
1. Find permission by actor + resource + permission_type
2. Check status == `approved`
3. Validate constraints:
   - Rate limit: `current_day_requests < rate_limit_rpm`
   - Token limit: `current_day_tokens + request_tokens < token_limit_per_day`
   - Cost limit: `current_day_cost_usd + estimated_cost < cost_limit_per_day_usd`
4. (Optional) Evaluate CEL policies
5. (Optional) Check trust score
6. Return allow/deny decision

---

#### 9. Update Usage

Track resource usage after consumption.

**Endpoint:** `POST /api/v1/permissions/{id}/usage`

**Request Body:**
```json
{
  "request_count": 1,
  "token_count": 1234,
  "cost_usd": 0.037
}
```

**Response:** `204 No Content`

**Usage Update Logic:**
1. Check if day rolled over since last update
2. If new day: reset `current_day_*` fields, set `current_day_start`
3. Increment `current_day_requests`, `current_day_tokens`, `current_day_cost_usd`
4. Increment `total_requests`, `total_tokens`, `total_cost_usd`
5. Update `last_used_at`

**Note:** Usage updates should be called **after** resource consumption (asynchronously recommended).

---

#### 10. Get Active Permissions

List active permissions for an actor.

**Endpoint:** `GET /api/v1/permissions/active?actor_id={actor_id}`

**Example:**
```
GET /api/v1/permissions/active?actor_id=agent-xyz-456
```

**Response:** `200 OK`
```json
{
  "permissions": [
    {
      "permission_id": "perm-uuid-abc",
      "actor_id": "agent-xyz-456",
      "actor_type": "agent",
      "permission_type": "use",
      "status": "approved",
      "resource_name": "GPT-4",
      "resource_type": "ai_model",
      "compliance_labels": ["GDPR", "SOC2"],
      "constraints": { "rate_limit_rpm": 60, ... },
      "usage_tracking": { "total_requests": 1234, ... },
      "approved_at": "2025-10-01T10:00:00Z",
      "created_at": "2025-10-01T09:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### 11. List Permissions

Query permissions with filtering.

**Endpoint:** `GET /api/v1/permissions`

**Query Parameters:**
- `actor_id` (optional) - Filter by actor
- `actor_type` (optional) - Filter by actor type: `agent`, `user`, `service`
- `resource_id` (optional) - Filter by resource
- `permission_type` (optional) - Filter by type: `use`, `read`, `write`, `execute`, `admin`
- `status` (optional) - Filter by status: `pending`, `approved`, `denied`, `revoked`, `suspended`
- `limit` (optional) - Page size (default: 100)
- `offset` (optional) - Pagination offset (default: 0)

**Example:**
```
GET /api/v1/permissions?actor_id=agent-xyz-456&status=approved&limit=50
```

**Response:** `200 OK`
```json
{
  "permissions": [ ... ],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

---

#### 12. Get Permission

Retrieve specific permission details.

**Endpoint:** `GET /api/v1/permissions/{id}`

**Response:** `200 OK` (permission object)

---

#### 13. Update Permission

Update permission properties (admin only).

**Endpoint:** `PUT /api/v1/permissions/{id}`

**Request Body:** (all fields optional)
```json
{
  "status": "suspended",
  "constraints": {
    "rate_limit_rpm": 30,
    "token_limit_per_day": 50000
  },
  "revoked_by": "admin-user-123",
  "revocation_reason": "Excessive usage detected"
}
```

**Response:** `200 OK` (updated permission)

---

#### 14. Approve Permission

Approve a pending permission request.

**Endpoint:** `POST /api/v1/permissions/{id}/approve`

**Request Body:**
```json
{
  "approved_by": "admin-user-123",
  "notes": "Approved for production use with standard limits"
}
```

**Response:** `200 OK`
```json
{
  "id": "perm-uuid-abc",
  "status": "approved",
  "approved_by": "admin-user-123",
  "approved_at": "2025-10-01T15:00:00Z",
  "approval_notes": "Approved for production use with standard limits",
  ...
}
```

---

#### 15. Revoke Permission

Revoke an active permission.

**Endpoint:** `POST /api/v1/permissions/{id}/revoke`

**Request Body:**
```json
{
  "revoked_by": "admin-user-123",
  "reason": "Security audit - overprivileged access"
}
```

**Response:** `200 OK`
```json
{
  "id": "perm-uuid-abc",
  "status": "revoked",
  "revoked_by": "admin-user-123",
  "revoked_at": "2025-10-01T15:30:00Z",
  "revocation_reason": "Security audit - overprivileged access",
  ...
}
```

---

### Policy Management

#### 16. List Policies

Get all policies.

**Endpoint:** `GET /api/v1/policies`

**Query Parameters:**
- `type` (optional) - Filter by type: `access`, `dlp`, `compliance`, `rate_limit`
- `category` (optional) - Filter by category
- `enabled` (optional) - Filter by enabled status: `true`, `false`
- `limit` (optional) - Page size
- `offset` (optional) - Pagination offset

**Response:** `200 OK`
```json
{
  "policies": [
    {
      "id": 1,
      "name": "Block API Keys",
      "description": "Prevent API keys from being sent in prompts",
      "type": "dlp",
      "category": "data_loss_prevention",
      "priority": 1,
      "enabled": true,
      "policy_expr": "!request.content.contains(\"sk-\") && !request.content.contains(\"AKIA\")",
      "policy_language": "cel",
      "is_system_policy": true,
      "created_at": "2025-10-01T00:00:00Z"
    }
  ],
  "total": 6
}
```

---

#### 17. Create Policy

Create a new policy.

**Endpoint:** `POST /api/v1/policies`

**Request Body:**
```json
{
  "name": "Trust Tier Check",
  "description": "Enforce minimum trust score for resource access",
  "type": "access",
  "category": "trust_enforcement",
  "priority": 10,
  "enabled": true,
  "policy_expr": "actor.trust_score >= resource.trust_tier_required",
  "policy_language": "cel",
  "tags": ["trust", "security"],
  "created_by": "admin-user-123"
}
```

**Response:** `201 Created` (policy object)

---

#### 18. Get Policy

Retrieve policy details.

**Endpoint:** `GET /api/v1/policies/{id}`

**Response:** `200 OK` (policy object)

---

#### 19. Update Policy

Update policy properties.

**Endpoint:** `PUT /api/v1/policies/{id}`

**Request Body:**
```json
{
  "enabled": false,
  "priority": 5,
  "updated_by": "admin-user-123"
}
```

**Response:** `200 OK` (updated policy)

**Note:** System policies (`is_system_policy: true`) cannot be modified.

---

#### 20. Delete Policy

Delete a policy.

**Endpoint:** `DELETE /api/v1/policies/{id}`

**Response:** `204 No Content`

**Note:** System policies cannot be deleted.

---

#### 21. Evaluate Policy

Test policy evaluation with sample data.

**Endpoint:** `POST /api/v1/policies/{id}/evaluate`

**Request Body:**
```json
{
  "context": {
    "request": {
      "content": "What is the weather?",
      "has_credentials": false
    },
    "actor": {
      "trust_score": 0.75,
      "role": "agent"
    },
    "resource": {
      "trust_tier_required": 0.6,
      "risk_level": "low"
    }
  }
}
```

**Response:** `200 OK`
```json
{
  "policy_id": "1",
  "result": "allow",
  "reason": "Policy expression evaluated to true",
  "timestamp": "2025-10-01T16:00:00Z"
}
```

---

### Audit & Compliance

#### 22. Log Audit Event

**Endpoint:** `POST /api/v1/audit/events`

(Documented in Trust Scoring SDK Integration Guide)

#### 23. Get Audit Events

**Endpoint:** `GET /api/v1/audit/events`

(Documented in Trust Scoring SDK Integration Guide)

#### 24. Get Compliance Report

**Endpoint:** `GET /api/v1/audit/compliance/{entity_id}`

(Documented in Trust Scoring SDK Integration Guide)

---

## CEL Policy Engine

### Overview

Google Common Expression Language (CEL) provides fast, safe policy evaluation.

**Benefits:**
- **Fast**: <1ms evaluation (compiled + cached)
- **Safe**: Sandboxed, no side effects
- **Expressive**: Rich expression syntax
- **Type-safe**: Static type checking

### Available Variables

When evaluating CEL policies, these variables are available:

```go
request  // map[string]interface{} - Request context
actor    // map[string]interface{} - Actor properties
resource // map[string]interface{} - Resource properties
context  // map[string]interface{} - Additional context
```

### CEL Expression Examples

#### DLP Policies

**Block API Keys:**
```cel
!request.content.contains("sk-") &&
!request.content.contains("AKIA") &&
!request.content.contains("sk-ant-")
```

**Block SSN:**
```cel
!request.content.matches("\\d{3}-\\d{2}-\\d{4}")
```

**Block Private Keys:**
```cel
!request.content.contains("-----BEGIN") ||
!request.content.contains("PRIVATE KEY")
```

**Block Database Connections:**
```cel
!request.content.contains("postgres://") &&
!request.content.contains("mongodb://") &&
!request.content.contains("mysql://")
```

#### Access Control Policies

**Trust Score Check:**
```cel
actor.trust_score >= resource.trust_tier_required
```

**Role-Based Access:**
```cel
actor.role in ["admin", "owner"] || resource.public == true
```

**Time-Based Access:**
```cel
context.hour >= 9 && context.hour <= 17
```

**Cost Budget Check:**
```cel
context.cost_today < actor.budget_limit
```

#### Compliance Policies

**GDPR Compliance:**
```cel
resource.compliance_labels.exists(l, l in ["GDPR", "SOC2"])
```

**Data Residency:**
```cel
resource.data_residency == "EU" && actor.location == "EU"
```

**Availability Window:**
```cel
request.timestamp >= resource.available_from &&
request.timestamp <= resource.available_until
```

#### Complex Policies

**Risk-Based Access:**
```cel
(actor.trust_score >= 80 && resource.risk_level == "low") ||
(actor.trust_score >= 90 && resource.risk_level == "medium") ||
(actor.role == "admin")
```

**Multi-Factor Check:**
```cel
actor.trust_score >= resource.trust_tier_required &&
resource.status == "active" &&
resource.health_status == "healthy" &&
!context.has_credentials
```

### CEL Syntax Reference

**Operators:**
- Logical: `&&`, `||`, `!`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- String: `contains()`, `matches()`, `startsWith()`, `endsWith()`
- List: `in`, `exists()`, `all()`, `map()`, `filter()`

**Example Testing:**
```python
# SDK method to validate CEL expression
try:
    governance_client.validate_cel_expression(
        "actor.trust_score >= 60 && resource.status == 'active'"
    )
    print("Valid CEL expression")
except ValueError as e:
    print(f"Invalid CEL: {e}")
```

---

## Event Publishing

### Overview

The Governance Service publishes events to Redis streams for real-time updates.

### Redis Streams

1. **`governance-events`** - Resource/permission/policy changes
2. **`trust-events`** - Trust score updates (see Trust Scoring SDK guide)

### Event Types

#### Governance Decision Event

Published when permission checks occur.

**Stream:** `governance-events`
**Event Type:** `governance_decision`

**Payload:**
```json
{
  "event_id": "uuid-event-123",
  "rule_id": "rule-789",
  "action": "triggered",
  "category": "permission_check",
  "actor_id": "agent-xyz-456",
  "actor_type": "agent",
  "resource_id": "resource-uuid-123",
  "resource_type": "ai_model",
  "decision": "allow",
  "reason": "Permission approved and within limits",
  "metadata": {
    "permission_id": "perm-uuid-abc",
    "constraints_checked": true,
    "trust_score": 67.8,
    "policies_evaluated": 3
  },
  "timestamp": "2025-10-01T14:35:00Z"
}
```

**Decision Values:**
- `allow` - Access granted
- `deny` - Access denied
- `block` - Blocked by policy

---

#### Permission Change Event

Published when permissions are approved, revoked, or denied.

**Stream:** `governance-events`
**Event Type:** `permission_approved`, `permission_revoked`, `permission_denied`

**Payload:**
```json
{
  "event_id": "uuid-event-456",
  "permission_id": "perm-uuid-abc",
  "actor_id": "agent-xyz-456",
  "actor_type": "agent",
  "resource_id": "resource-uuid-123",
  "permission_type": "use",
  "old_status": "pending",
  "new_status": "approved",
  "changed_by": "admin-user-123",
  "reason": "Approved for production use",
  "metadata": {
    "constraints": {
      "rate_limit_rpm": 60,
      "token_limit_per_day": 100000
    }
  },
  "timestamp": "2025-10-01T15:00:00Z"
}
```

---

#### Resource Change Event

Published when resources are created, updated, or deleted.

**Stream:** `governance-events`
**Event Type:** `resource_created`, `resource_updated`, `resource_deleted`

**Payload:**
```json
{
  "event_id": "uuid-event-789",
  "resource_id": "resource-uuid-123",
  "organization_id": "org-abc-123",
  "resource_type": "ai_model",
  "resource_name": "GPT-4",
  "action": "created",
  "changed_by": "admin-user-123",
  "changes": {
    "status": "active",
    "trust_tier_required": 60
  },
  "timestamp": "2025-10-01T14:00:00Z"
}
```

---

## SDK Implementation Guidelines

### Recommended SDK Structure

```python
from agion_sdk import GovernanceClient

# Initialize client
governance = GovernanceClient(
    base_url="http://governance-service:8080/api/v1",
    api_key="your-api-key",
    organization_id="org-abc-123"
)

# Resource management
resource = governance.create_resource(...)
resource = governance.get_resource(resource_id)
resources = governance.list_resources(filters)
governance.update_resource(resource_id, updates)
governance.delete_resource(resource_id)

# Permission management (critical)
permission = governance.request_permission(...)
result = governance.check_permission(actor_id, resource_id, permission_type, context)
governance.update_usage(permission_id, requests, tokens, cost)
permissions = governance.get_active_permissions(actor_id)

# Permission lifecycle
governance.approve_permission(permission_id, approved_by, notes)
governance.revoke_permission(permission_id, revoked_by, reason)

# Policy management
policy = governance.create_policy(...)
policies = governance.list_policies(filters)
result = governance.evaluate_policy(policy_id, context)

# Event subscription (optional)
governance.subscribe_governance_events(callback)
```

### Client Class Structure

```python
class GovernanceClient:
    """Main client for Agion Governance Service"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        organization_id: str,
        timeout: int = 30,
        retry_config: dict = None
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.organization_id = organization_id
        self.timeout = timeout
        self.session = self._create_session()

    # Resource methods
    def create_resource(self, req: CreateResourceRequest) -> GovernanceResource:
        pass

    def get_resource(self, resource_id: str) -> GovernanceResource:
        pass

    def list_resources(self, filters: ResourceFilter) -> List[GovernanceResource]:
        pass

    def update_resource(
        self,
        resource_id: str,
        updates: UpdateResourceRequest
    ) -> GovernanceResource:
        pass

    def delete_resource(self, resource_id: str) -> None:
        pass

    def get_resource_children(self, resource_id: str) -> List[GovernanceResource]:
        pass

    # Permission methods (CRITICAL)
    def request_permission(
        self,
        actor_id: str,
        actor_type: str,
        resource_id: str,
        permission_type: str,
        purpose: str,
        constraints: dict = None,
        justification: str = None
    ) -> GovernancePermission:
        pass

    def check_permission(
        self,
        actor_id: str,
        actor_type: str,
        resource_id: str,
        permission_type: str,
        context: dict = None
    ) -> PermissionCheckResult:
        """
        CRITICAL METHOD - validates access before resource consumption

        Returns:
            PermissionCheckResult with allowed=True/False

        Raises:
            PermissionDeniedError if not allowed
            GovernanceAPIError for other errors
        """
        pass

    def update_usage(
        self,
        permission_id: str,
        request_count: int = 1,
        token_count: int = 0,
        cost_usd: float = 0.0
    ) -> None:
        """Track resource usage after consumption (async recommended)"""
        pass

    def get_active_permissions(
        self,
        actor_id: str
    ) -> List[ActivePermissionView]:
        pass

    def approve_permission(
        self,
        permission_id: str,
        approved_by: str,
        notes: str = None
    ) -> GovernancePermission:
        pass

    def revoke_permission(
        self,
        permission_id: str,
        revoked_by: str,
        reason: str
    ) -> GovernancePermission:
        pass

    # Policy methods
    def list_policies(self, filters: dict = None) -> List[Policy]:
        pass

    def create_policy(self, req: CreatePolicyRequest) -> Policy:
        pass

    def evaluate_policy(
        self,
        policy_id: str,
        context: dict
    ) -> PolicyEvaluationResult:
        pass

    def validate_cel_expression(self, expression: str) -> bool:
        """Validate CEL expression syntax"""
        pass

    # Event subscription (optional)
    def subscribe_governance_events(
        self,
        callback: Callable[[GovernanceEvent], None],
        event_types: List[str] = None
    ):
        """Subscribe to governance events from Redis"""
        pass
```

---

## Data Models

### Resource Models

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class ResourceType(str, Enum):
    MODEL_PROVIDER = "model_provider"
    AI_MODEL = "ai_model"
    DATABASE = "database"
    API = "api"
    STORAGE = "storage"
    MCP_SERVER = "mcp_server"
    TOOL = "tool"
    WEBHOOK = "webhook"
    COMPUTE = "compute"

class ResourceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"
    DEPRECATED = "deprecated"

class ResourceHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class GovernanceResource:
    id: str
    organization_id: str
    resource_type: ResourceType
    name: str
    resource_data: Dict
    status: ResourceStatus
    health_status: ResourceHealthStatus
    created_at: datetime
    updated_at: datetime
    parent_resource_id: Optional[str] = None
    description: Optional[str] = None
    compliance_labels: List[str] = None
    data_residency: Optional[str] = None
    trust_tier_required: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    health_check_at: Optional[datetime] = None
    health_message: Optional[str] = None
    tags: List[str] = None
    metadata: Dict = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

@dataclass
class CreateResourceRequest:
    organization_id: str
    resource_type: ResourceType
    name: str
    resource_data: Dict
    created_by: str
    parent_resource_id: Optional[str] = None
    description: Optional[str] = None
    compliance_labels: List[str] = None
    data_residency: Optional[str] = None
    trust_tier_required: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    status: ResourceStatus = ResourceStatus.ACTIVE
    tags: List[str] = None
    metadata: Dict = None
```

### Permission Models

```python
class ActorType(str, Enum):
    AGENT = "agent"
    USER = "user"
    SERVICE = "service"

class PermissionType(str, Enum):
    USE = "use"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class PermissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    REVOKED = "revoked"
    SUSPENDED = "suspended"

@dataclass
class GovernancePermission:
    id: str
    actor_id: str
    actor_type: ActorType
    resource_id: str
    permission_type: PermissionType
    status: PermissionStatus
    purpose: str
    constraints: Dict
    usage_tracking: Dict
    requested_at: datetime
    created_at: datetime
    updated_at: datetime
    justification: Optional[str] = None
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    revoked_by: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

@dataclass
class PermissionCheckResult:
    allowed: bool
    reason: str
    timestamp: datetime
    permission: Optional[GovernancePermission] = None
    constraints: Dict = None
    metadata: Dict = None

@dataclass
class UsageUpdate:
    permission_id: str
    request_count: int = 1
    token_count: int = 0
    cost_usd: float = 0.0
```

### Policy Models

```python
class PolicyLanguage(str, Enum):
    JSON = "json"
    CEL = "cel"

@dataclass
class Policy:
    id: int
    name: str
    description: str
    type: str
    category: str
    priority: int
    enabled: bool
    policy_language: PolicyLanguage
    created_at: datetime
    updated_at: datetime
    policy_expr: Optional[str] = None
    rules: Optional[str] = None  # JSON string
    actions: Optional[str] = None  # JSON string
    tags: List[str] = None
    is_system_policy: bool = False
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
```

---

## Integration Examples

### Example 1: Register a Resource

```python
from agion_sdk import GovernanceClient, ResourceType, RiskLevel

client = GovernanceClient(
    base_url="http://governance:8080/api/v1",
    api_key="api-key",
    organization_id="org-abc-123"
)

# Create AI model resource
resource = client.create_resource(
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
    trust_tier_required=60,
    risk_level=RiskLevel.MEDIUM,
    tags=["production", "gpt", "openai"],
    created_by="admin-user"
)

print(f"Resource created: {resource.id}")
```

---

### Example 2: Request Permission

```python
# Agent requests permission to use GPT-4
permission = client.request_permission(
    actor_id="agent-xyz-456",
    actor_type="agent",
    resource_id=resource.id,
    permission_type="use",
    purpose="AI model inference for customer support",
    justification="Agent handles complex customer queries requiring GPT-4",
    constraints={
        "rate_limit_rpm": 60,
        "token_limit_per_day": 100000,
        "cost_limit_per_day_usd": 10.0
    }
)

print(f"Permission requested: {permission.id}, status: {permission.status}")
```

---

### Example 3: Approve Permission (Admin)

```python
# Admin approves the permission
approved = client.approve_permission(
    permission_id=permission.id,
    approved_by="admin-user-123",
    notes="Approved for production use with standard limits"
)

print(f"Permission approved: {approved.status}")
```

---

### Example 4: Check Permission Before Use

```python
from agion_sdk.exceptions import PermissionDeniedError

# Before making AI model call, check permission
try:
    result = client.check_permission(
        actor_id="agent-xyz-456",
        actor_type="agent",
        resource_id=resource.id,
        permission_type="use",
        context={
            "request_tokens": 1500,
            "estimated_cost": 0.045
        }
    )

    if result.allowed:
        print("Permission granted - proceeding with AI call")
        # Make AI model call here

        # After AI call, track usage
        client.update_usage(
            permission_id=result.permission.id,
            request_count=1,
            token_count=1234,
            cost_usd=0.037
        )
    else:
        print(f"Permission denied: {result.reason}")

except PermissionDeniedError as e:
    print(f"Access denied: {e}")
```

---

### Example 5: List Active Permissions

```python
# Get all active permissions for an agent
permissions = client.get_active_permissions(actor_id="agent-xyz-456")

for perm in permissions:
    print(f"Resource: {perm.resource_name} ({perm.resource_type})")
    print(f"Permission: {perm.permission_type}, Status: {perm.status}")
    print(f"Usage: {perm.usage_tracking['total_requests']} requests")
    print(f"Constraints: {perm.constraints}")
    print()
```

---

### Example 6: Create CEL Policy

```python
# Create trust-based access policy
policy = client.create_policy(
    name="Trust Tier Enforcement",
    description="Ensure actor trust score meets resource requirements",
    type="access",
    category="trust_enforcement",
    priority=10,
    enabled=True,
    policy_language="cel",
    policy_expr="actor.trust_score >= resource.trust_tier_required",
    tags=["trust", "security"]
)

print(f"Policy created: {policy.id}")
```

---

### Example 7: Evaluate Policy

```python
# Test policy evaluation
result = client.evaluate_policy(
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

### Example 8: Full Workflow

```python
from agion_sdk import GovernanceClient, ResourceType
import asyncio

async def main():
    client = GovernanceClient(
        base_url="http://governance:8080/api/v1",
        api_key="api-key",
        organization_id="org-abc-123"
    )

    # 1. Register resource
    resource = client.create_resource(
        resource_type=ResourceType.AI_MODEL,
        name="Claude 3 Opus",
        resource_data={
            "model_identifier": "claude-3-opus-20240229",
            "provider": "anthropic"
        },
        trust_tier_required=70,
        created_by="admin"
    )

    # 2. Request permission
    permission = client.request_permission(
        actor_id="agent-123",
        actor_type="agent",
        resource_id=resource.id,
        permission_type="use",
        purpose="Production AI inference",
        constraints={"rate_limit_rpm": 30}
    )

    # 3. Approve (admin)
    client.approve_permission(
        permission_id=permission.id,
        approved_by="admin-user"
    )

    # 4. Check permission before each use
    for i in range(5):
        result = client.check_permission(
            actor_id="agent-123",
            actor_type="agent",
            resource_id=resource.id,
            permission_type="use"
        )

        if result.allowed:
            print(f"Request {i+1}: Allowed")
            # Make AI call
            await make_ai_call()
            # Track usage (async)
            asyncio.create_task(
                client.update_usage(permission.id, request_count=1, token_count=500)
            )
        else:
            print(f"Request {i+1}: Denied - {result.reason}")

asyncio.run(main())
```

---

## Performance & Caching

### Client-Side Caching

**Recommended**: Implement L1 cache in SDK for permission checks.

```python
from functools import lru_cache
from datetime import datetime, timedelta

class GovernanceClient:
    def __init__(self, ...):
        self._permission_cache = {}
        self._cache_ttl = 30  # seconds

    def check_permission(self, actor_id, resource_id, permission_type, context=None):
        # Generate cache key
        cache_key = f"perm:{actor_id}:{resource_id}:{permission_type}"

        # Check L1 cache
        if cache_key in self._permission_cache:
            cached_result, cached_at = self._permission_cache[cache_key]
            age = (datetime.now() - cached_at).total_seconds()

            if age < self._cache_ttl:
                # Cache hit - return immediately
                return cached_result

        # Cache miss - call API
        result = self._api_check_permission(actor_id, resource_id, permission_type, context)

        # Cache the result (only if approved, shorter TTL for denied)
        ttl = self._cache_ttl if result.allowed else 5
        self._permission_cache[cache_key] = (result, datetime.now())

        return result
```

### Performance Tips

1. **Cache permission checks** - 30s TTL for approved, 5s for denied
2. **Async usage updates** - Don't block on usage tracking
3. **Batch operations** - Use list endpoints to reduce round trips
4. **Connection pooling** - Reuse HTTP connections
5. **Circuit breaker** - Implement fallback for service unavailability
6. **Retry logic** - Exponential backoff for transient errors

### Expected Latencies

| Operation | Cold (No Cache) | Warm (Cached) | Notes |
|-----------|-----------------|---------------|-------|
| Check Permission | 5-15ms | <1μs | L1 cache in SDK |
| Get Resource | 3-8ms | <1ms | L2 cache in service |
| List Permissions | 10-30ms | N/A | Database query |
| Update Usage | 5-10ms | N/A | Async recommended |
| Create Resource | 8-15ms | N/A | Database write |
| CEL Policy Eval | <1ms | <100μs | Compiled + cached |

---

## Error Handling

### HTTP Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Missing fields, invalid values, constraint violations |
| 401 | Unauthorized | Missing/invalid API key |
| 403 | Forbidden | Insufficient permissions for operation |
| 404 | Not Found | Resource/permission not found |
| 409 | Conflict | Duplicate resource, concurrent modification |
| 422 | Unprocessable Entity | Validation failed, CEL syntax error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Database error, service unavailable |
| 503 | Service Unavailable | Governance service down |

### Error Response Format

```json
{
  "error": "Bad Request",
  "message": "Invalid resource_type: invalid_type",
  "details": "resource_type must be one of: model_provider, ai_model, database, ...",
  "timestamp": "2025-10-01T16:00:00Z"
}
```

### SDK Exception Hierarchy

```python
class GovernanceAPIError(Exception):
    """Base exception for all governance API errors"""
    def __init__(self, message, status_code, response):
        self.message = message
        self.status_code = status_code
        self.response = response

class PermissionDeniedError(GovernanceAPIError):
    """Permission check returned denied"""
    pass

class ResourceNotFoundError(GovernanceAPIError):
    """Resource not found"""
    pass

class ValidationError(GovernanceAPIError):
    """Request validation failed"""
    pass

class RateLimitError(GovernanceAPIError):
    """Rate limit exceeded"""
    pass

class ServiceUnavailableError(GovernanceAPIError):
    """Governance service unavailable"""
    pass
```

### Error Handling Example

```python
from agion_sdk import GovernanceClient
from agion_sdk.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    RateLimitError,
    ServiceUnavailableError
)

client = GovernanceClient(...)

try:
    result = client.check_permission(
        actor_id="agent-123",
        resource_id="resource-456",
        permission_type="use"
    )

    if result.allowed:
        # Proceed with operation
        pass
    else:
        # Handle denial gracefully
        print(f"Access denied: {result.reason}")

except PermissionDeniedError as e:
    # Explicit denial (status or constraints violated)
    logger.warning(f"Permission denied: {e.message}")
    # Maybe retry with different resource

except ResourceNotFoundError as e:
    # Resource or permission doesn't exist
    logger.error(f"Resource not found: {e.message}")
    # Create permission request

except RateLimitError as e:
    # Rate limit exceeded
    logger.warning(f"Rate limit: {e.message}")
    # Implement backoff
    time.sleep(60)

except ServiceUnavailableError as e:
    # Governance service down
    logger.error(f"Service unavailable: {e.message}")
    # Fallback to cached decision or fail-open based on trust
    if actor_trust_score >= 0.7:
        # Allow high-trust actors during outage
        logger.info("Fail-open for high-trust actor")
    else:
        # Deny low-trust actors
        raise

except GovernanceAPIError as e:
    # Other API errors
    logger.error(f"Governance API error: {e.message}")
    raise
```

---

## Testing & Validation

### Unit Testing

```python
import pytest
from agion_sdk import GovernanceClient
from agion_sdk.models import ResourceType

def test_create_resource():
    client = GovernanceClient(
        base_url="http://localhost:8080/api/v1",
        api_key="test-key",
        organization_id="test-org"
    )

    resource = client.create_resource(
        resource_type=ResourceType.AI_MODEL,
        name="Test Model",
        resource_data={"test": "data"},
        created_by="test-user"
    )

    assert resource.id is not None
    assert resource.name == "Test Model"
    assert resource.status == "active"

def test_check_permission_allowed():
    client = GovernanceClient(...)

    # Assuming permission exists and is approved
    result = client.check_permission(
        actor_id="agent-test",
        actor_type="agent",
        resource_id="resource-test",
        permission_type="use"
    )

    assert result.allowed == True
    assert result.permission is not None

def test_check_permission_denied():
    client = GovernanceClient(...)

    result = client.check_permission(
        actor_id="agent-test",
        actor_type="agent",
        resource_id="restricted-resource",
        permission_type="admin"
    )

    assert result.allowed == False
    assert "denied" in result.reason.lower()
```

### Integration Testing

```python
import pytest
from agion_sdk import GovernanceClient

@pytest.fixture
def governance_client():
    return GovernanceClient(
        base_url="http://governance-test:8080/api/v1",
        api_key="test-api-key",
        organization_id="test-org-123"
    )

def test_full_permission_workflow(governance_client):
    # 1. Create resource
    resource = governance_client.create_resource(
        resource_type="ai_model",
        name="Test GPT-4",
        resource_data={"model": "gpt-4"},
        created_by="test-admin"
    )

    # 2. Request permission
    permission = governance_client.request_permission(
        actor_id="test-agent",
        actor_type="agent",
        resource_id=resource.id,
        permission_type="use",
        purpose="Testing"
    )
    assert permission.status == "pending"

    # 3. Approve permission
    approved = governance_client.approve_permission(
        permission_id=permission.id,
        approved_by="test-admin"
    )
    assert approved.status == "approved"

    # 4. Check permission (should be allowed)
    result = governance_client.check_permission(
        actor_id="test-agent",
        actor_type="agent",
        resource_id=resource.id,
        permission_type="use"
    )
    assert result.allowed == True

    # 5. Track usage
    governance_client.update_usage(
        permission_id=permission.id,
        request_count=1,
        token_count=500,
        cost_usd=0.015
    )

    # 6. Verify usage tracked
    permissions = governance_client.get_active_permissions("test-agent")
    assert len(permissions) >= 1
    assert permissions[0].usage_tracking["total_requests"] >= 1

    # 7. Revoke permission
    revoked = governance_client.revoke_permission(
        permission_id=permission.id,
        revoked_by="test-admin",
        reason="Test complete"
    )
    assert revoked.status == "revoked"

    # 8. Check permission (should be denied)
    result = governance_client.check_permission(
        actor_id="test-agent",
        actor_type="agent",
        resource_id=resource.id,
        permission_type="use"
    )
    assert result.allowed == False

    # 9. Cleanup
    governance_client.delete_resource(resource.id)
```

### CEL Expression Validation

```python
def test_cel_validation():
    client = GovernanceClient(...)

    # Valid expressions
    assert client.validate_cel_expression(
        "actor.trust_score >= resource.trust_tier_required"
    ) == True

    assert client.validate_cel_expression(
        "!request.content.contains('sk-')"
    ) == True

    # Invalid expressions
    with pytest.raises(ValidationError):
        client.validate_cel_expression(
            "actor.trust_score >> invalid syntax"
        )
```

---

## Database Schema Reference

### governance_resources

```sql
CREATE TABLE governance_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    parent_resource_id UUID REFERENCES governance_resources(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_data JSONB NOT NULL DEFAULT '{}',
    compliance_labels TEXT[] DEFAULT ARRAY[]::TEXT[],
    data_residency VARCHAR(50),
    trust_tier_required INTEGER DEFAULT 0 CHECK (trust_tier_required >= 0 AND trust_tier_required <= 100),
    risk_level VARCHAR(20) DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending', 'error', 'deprecated')),
    health_status VARCHAR(20) DEFAULT 'unknown' CHECK (health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown')),
    health_check_at TIMESTAMP WITH TIME ZONE,
    health_message TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_resource_per_org UNIQUE(organization_id, resource_type, name)
);

CREATE INDEX idx_resources_org_type ON governance_resources(organization_id, resource_type);
CREATE INDEX idx_resources_parent ON governance_resources(parent_resource_id) WHERE parent_resource_id IS NOT NULL;
CREATE INDEX idx_resources_status ON governance_resources(status, health_status);
CREATE INDEX idx_resources_compliance ON governance_resources USING GIN(compliance_labels);
CREATE INDEX idx_resources_tags ON governance_resources USING GIN(tags);
```

### governance_permissions

```sql
CREATE TABLE governance_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id VARCHAR(255) NOT NULL,
    actor_type VARCHAR(50) NOT NULL CHECK (actor_type IN ('agent', 'user', 'service')),
    resource_id UUID NOT NULL REFERENCES governance_resources(id) ON DELETE CASCADE,
    permission_type VARCHAR(50) NOT NULL CHECK (permission_type IN ('use', 'read', 'write', 'execute', 'admin')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied', 'revoked', 'suspended')),
    purpose TEXT NOT NULL,
    justification TEXT,
    constraints JSONB DEFAULT '{}',
    usage_tracking JSONB DEFAULT '{"total_requests":0,"total_tokens":0,"total_cost_usd":0}',
    requested_by VARCHAR(255),
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    revoked_by VARCHAR(255),
    revoked_at TIMESTAMP WITH TIME ZONE,
    revocation_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_permission UNIQUE(actor_id, actor_type, resource_id, permission_type)
);

CREATE INDEX idx_permissions_actor ON governance_permissions(actor_id, actor_type, status);
CREATE INDEX idx_permissions_resource ON governance_permissions(resource_id, status);
CREATE INDEX idx_permissions_status ON governance_permissions(status);
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-01 | Initial release - Unified governance system |

---

## Appendix: Quick Reference

### Resource Types
```
model_provider, ai_model, database, api, storage,
mcp_server, tool, webhook, compute
```

### Actor Types
```
agent, user, service
```

### Permission Types
```
use, read, write, execute, admin
```

### Status Values

**Resource Status:**
```
active, inactive, pending, error, deprecated
```

**Permission Status:**
```
pending, approved, denied, revoked, suspended
```

**Health Status:**
```
healthy, degraded, unhealthy, unknown
```

**Risk Levels:**
```
low, medium, high, critical
```

### Constraint Fields

```json
{
  "rate_limit_rpm": 60,
  "token_limit_per_day": 100000,
  "cost_limit_per_day_usd": 10.0,
  "allowed_hours": "09:00-17:00",
  "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
}
```

### Usage Tracking Fields

```json
{
  "total_requests": 1234,
  "total_tokens": 567890,
  "total_cost_usd": 15.25,
  "current_day_requests": 45,
  "current_day_tokens": 23456,
  "current_day_cost_usd": 0.67,
  "last_used_at": "2025-10-01T14:30:00Z",
  "current_day_start": "2025-10-01T00:00:00Z"
}
```

---

**End of Unified Governance SDK Integration Guide**

For trust scoring integration, see: `TRUST_SCORING_SDK_INTEGRATION_GUIDE.md`
