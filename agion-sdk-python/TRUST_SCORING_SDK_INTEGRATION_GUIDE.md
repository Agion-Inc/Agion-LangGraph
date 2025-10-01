# Trust Scoring Engine - SDK Integration Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-01
**Service:** Agion Governance Service - Trust Scoring & Human Feedback System

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [Trust Scoring System](#trust-scoring-system)
4. [Human Feedback System](#human-feedback-system)
5. [HTTP API Reference](#http-api-reference)
6. [Event Publishing](#event-publishing)
7. [SDK Implementation Guidelines](#sdk-implementation-guidelines)
8. [Data Models](#data-models)
9. [Integration Examples](#integration-examples)
10. [Error Handling](#error-handling)

---

## Overview

The Agion Governance Service provides a comprehensive trust scoring system with two primary components:

1. **Automated Trust Evaluation** - System-generated trust events based on agent/user behavior
2. **Human-in-the-Loop Feedback** - User-provided feedback on agent responses that directly influences trust scores

This guide documents all interfaces, data structures, and integration points needed for SDK implementation.

---

## Architecture Summary

### Services

```
┌─────────────────────────────────────────────────────────────┐
│                   Governance Service                        │
│                                                             │
│  ┌─────────────────┐    ┌──────────────────┐              │
│  │  TrustService   │    │ FeedbackService  │              │
│  │                 │    │                  │              │
│  │ - EvaluateTrust │◄───┤ - SubmitFeedback │              │
│  │ - GetTrustScore │    │ - GetFeedbackStats│              │
│  │ - GetHistory    │    │ - ListFeedback   │              │
│  └────────┬────────┘    └─────────┬────────┘              │
│           │                       │                         │
│           └───────────┬───────────┘                         │
│                       │                                     │
│              ┌────────▼────────┐                            │
│              │ EventPublisher  │                            │
│              │                 │                            │
│              │ - Trust Events  │                            │
│              │ - Governance    │                            │
│              └────────┬────────┘                            │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
               ┌────────────────┐
               │  Redis Streams │
               │                │
               │ trust-events   │
               │ governance-*   │
               └────────────────┘
```

### Base URL

```
http(s)://<governance-service-host>:<port>/api/v1
```

Default port: `8080`

---

## Trust Scoring System

### Core Concepts

#### Trust Scores
- **Range:** 0.0 - 100.0 (stored as float64)
- **Initial Value:** 50.0 for new entities
- **Components:**
  - `score` - Overall trust score (weighted average)
  - `reputation_score` - Long-term reputation (40% weight)
  - `behavior_score` - Recent behavior patterns (40% weight)
  - `compliance_score` - Compliance adherence (20% weight)

#### Trust Tiers
Trust scores map to six trust tiers:

| Tier ID      | Name            | Score Range | Color  | Typical Permissions                    |
|--------------|-----------------|-------------|--------|----------------------------------------|
| `untrusted`  | Untrusted       | 0-20        | Red    | Read only                              |
| `basic`      | Basic Trust     | 20-40       | Orange | Read, Write                            |
| `verified`   | Verified        | 40-60       | Yellow | Read, Write, Delete                    |
| `trusted`    | Trusted         | 60-80       | Blue   | Read, Write, Delete, Manage            |
| `privileged` | Privileged      | 80-90       | Purple | Read, Write, Delete, Manage, Configure |
| `admin`      | Administrator   | 90-100      | Green  | Full access + Admin                    |

#### Trust Events
Events that trigger trust score updates:

| Event Type   | Description                          | Impact Formula                         |
|--------------|--------------------------------------|----------------------------------------|
| `positive`   | Positive behavior                    | Reputation×0.6 + Behavior×0.3 + Compliance×0.1 |
| `negative`   | Negative behavior                    | Reputation×0.8 + Behavior×0.5 + Compliance×0.7 |
| `compliance` | Compliance-related event             | Compliance×1.0 + Reputation×0.2        |
| `behavior`   | Behavioral event                     | Behavior×1.0 + Reputation×0.3          |

#### Time Decay
Trust scores decay over time to encourage continued good behavior:
- **Decay Rate:** 5% per day (0.95^days)
- **Applied:** On each trust evaluation
- **Formula:** `score_component *= 0.95^(days_since_last_update)`

---

## Human Feedback System

### Trust Impact Algorithm (v1.0.0)

The human feedback trust impact algorithm is centralized in `/internal/services/trust_impact_algorithm.go`.

#### Impact Rules

```go
type TrustImpactRules struct {
    NotHelpfulImpact            float64  // -2.0 (symmetric with 5-star)
    Star5Impact                 float64  // +2.0 (excellent)
    Star4Impact                 float64  // +0.5 (good)
    Star3Impact                 float64  //  0.0 (ignored when marked helpful)
    Star2Impact                 float64  //  0.0 (ignored when marked helpful)
    Star1Impact                 float64  //  0.0 (ignored when marked helpful)
    IgnoreLowRatingsWhenHelpful bool     //  true
    HelpfulWithoutRatingImpact  float64  //  0.0 (neutral)
}
```

#### Feedback Logic Table

| User Action                          | is_helpful | star_rating | Trust Impact | Rationale                              |
|--------------------------------------|------------|-------------|--------------|----------------------------------------|
| Marks "Not Helpful"                  | `false`    | `null`      | **-2.0%**    | Symmetric penalty with 5-star reward   |
| Marks "Helpful" + 5 stars            | `true`     | `5`         | **+2.0%**    | Excellent response - maximum boost     |
| Marks "Helpful" + 4 stars            | `true`     | `4`         | **+0.5%**    | Good response - modest boost           |
| Marks "Helpful" + 3 stars            | `true`     | `3`         | **0%**       | User being generous - ignored          |
| Marks "Helpful" + 2 stars            | `true`     | `2`         | **0%**       | User being generous - ignored          |
| Marks "Helpful" + 1 star             | `true`     | `1`         | **0%**       | User being generous - ignored          |
| Marks "Helpful" without rating       | `true`     | `null`      | **0%**       | Need rating for meaningful signal      |
| Provides 5 stars only (no helpful)   | `null`     | `5`         | **+2.0%**    | Assume positive intent                 |
| Provides 4 stars only (no helpful)   | `null`     | `4`         | **+0.5%**    | Assume positive intent                 |
| Provides 1-3 stars only (no helpful) | `null`     | `1-3`       | **0%**       | Neutral (unclear intent)               |

#### Design Principles

1. **Symmetric Scoring** - Negative feedback (-2.0%) equals maximum positive feedback (+2.0%)
2. **Excellence Rewarded** - Only 5-star ratings give maximum trust boost
3. **Quality Differentiation** - 4 stars (+0.5%) is clearly less than 5 stars (+2.0%)
4. **Generous Ratings Ignored** - Low ratings (1-3) when marked "helpful" are ignored
5. **Rating Required** - "Helpful" alone has no impact (need star rating for signal)

#### Feedback Categories

Optional categorization for detailed analytics:

- `accuracy` - Factual correctness of response
- `relevance` - Response relevance to query
- `clarity` - Response clarity and readability
- `safety` - Safety and ethical considerations
- `speed` - Response speed and efficiency

---

## HTTP API Reference

### Trust Evaluation Endpoints

#### 1. Evaluate Trust

Submit a trust event and update entity's trust score.

**Endpoint:** `POST /api/v1/trust/evaluate`

**Request Body:**
```json
{
  "entity_id": "agent-abc-123",
  "entity_type": "agent",
  "event_type": "positive",
  "impact": 5.0,
  "description": "Successfully completed task with high quality",
  "metadata": {
    "task_id": "task-456",
    "quality_score": 0.95
  }
}
```

**Request Schema:**
```go
type TrustEvaluationRequest struct {
    EntityID    string                 `json:"entity_id"`    // Required
    EntityType  string                 `json:"entity_type"`  // Required: "user", "agent", "service"
    EventType   string                 `json:"event_type"`   // Required: "positive", "negative", "compliance", "behavior"
    Impact      float64                `json:"impact"`       // Required: -100.0 to +100.0
    Description string                 `json:"description"`  // Required
    Metadata    map[string]interface{} `json:"metadata"`     // Optional
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 12345,
    "entity_id": "agent-abc-123",
    "entity_type": "agent",
    "score": 67.8,
    "reputation_score": 65.2,
    "behavior_score": 72.5,
    "compliance_score": 64.0,
    "last_updated": "2025-10-01T14:30:00Z",
    "created_at": "2025-09-01T10:00:00Z"
  },
  "message": "Trust evaluated successfully",
  "timestamp": "2025-10-01T14:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid request (missing fields, impact out of range)
- `500 Internal Server Error` - Database or processing error

---

#### 2. Get Trust Score

Retrieve current trust score for an entity.

**Endpoint:** `GET /api/v1/trust/score/{entity_id}`

**Query Parameters:**
- `entity_type` (optional) - Entity type (`user`, `agent`, `service`). Default: `user`

**Example:**
```
GET /api/v1/trust/score/agent-abc-123?entity_type=agent
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 12345,
    "entity_id": "agent-abc-123",
    "entity_type": "agent",
    "score": 67.8,
    "reputation_score": 65.2,
    "behavior_score": 72.5,
    "compliance_score": 64.0,
    "last_updated": "2025-10-01T14:30:00Z",
    "created_at": "2025-09-01T10:00:00Z"
  },
  "message": "Trust score retrieved successfully",
  "timestamp": "2025-10-01T14:35:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Entity does not have a trust score
- `500 Internal Server Error` - Database error

---

#### 3. Get Trust History

Retrieve trust events for an entity.

**Endpoint:** `GET /api/v1/trust/history/{entity_id}`

**Query Parameters:**
- `entity_type` (optional) - Entity type. Default: `user`
- `limit` (optional) - Number of events to return (1-1000). Default: `100`

**Example:**
```
GET /api/v1/trust/history/agent-abc-123?entity_type=agent&limit=50
```

**Response:**
```json
{
  "success": true,
  "data": {
    "entity_id": "agent-abc-123",
    "entity_type": "agent",
    "events": [
      {
        "id": 9876,
        "entity_id": "agent-abc-123",
        "entity_type": "agent",
        "event_type": "positive",
        "impact": 5.0,
        "description": "Successfully completed task",
        "metadata": "{\"task_id\":\"task-456\"}",
        "timestamp": "2025-10-01T14:30:00Z",
        "created_at": "2025-10-01T14:30:00Z"
      }
    ],
    "count": 1
  },
  "message": "Trust history retrieved successfully",
  "timestamp": "2025-10-01T14:40:00Z"
}
```

---

### Feedback Endpoints

#### 4. Submit Feedback

Submit user feedback on an agent response.

**Endpoint:** `POST /api/v1/feedback/submit`

**Request Body:**
```json
{
  "response_id": "resp-abc-789",
  "conversation_id": "conv-123",
  "agent_id": "agent-abc-123",
  "user_id": "user-xyz-456",
  "organization_id": "org-company-001",
  "is_helpful": true,
  "star_rating": 5,
  "feedback_text": "Excellent response, very accurate and helpful!",
  "feedback_category": "accuracy",
  "response_metadata": {
    "response_time_ms": 234,
    "model": "gpt-4"
  },
  "user_metadata": {
    "client_version": "1.2.3"
  }
}
```

**Request Schema:**
```go
type SubmitFeedbackRequest struct {
    ResponseID       string                 `json:"response_id"`       // Required
    ConversationID   *string                `json:"conversation_id"`   // Optional
    AgentID          string                 `json:"agent_id"`          // Required
    UserID           string                 `json:"user_id"`           // Required
    OrganizationID   string                 `json:"organization_id"`   // Required
    IsHelpful        *bool                  `json:"is_helpful"`        // Optional (true/false)
    StarRating       *int                   `json:"star_rating"`       // Optional (1-5)
    FeedbackText     *string                `json:"feedback_text"`     // Optional
    FeedbackCategory *string                `json:"feedback_category"` // Optional: "accuracy", "relevance", "clarity", "safety", "speed"
    ResponseMetadata map[string]interface{} `json:"response_metadata"` // Optional
    UserMetadata     map[string]interface{} `json:"user_metadata"`     // Optional
}
```

**Validation Rules:**
- Must provide at least one of: `is_helpful` OR `star_rating`
- `star_rating` must be 1-5 if provided
- `feedback_category` must be valid if provided
- Cannot submit duplicate feedback (same `response_id` + `user_id`)

**Response:**
```json
{
  "success": true,
  "feedback": {
    "id": "uuid-feedback-123",
    "response_id": "resp-abc-789",
    "conversation_id": "conv-123",
    "agent_id": "agent-abc-123",
    "user_id": "user-xyz-456",
    "organization_id": "org-company-001",
    "is_helpful": true,
    "star_rating": 5,
    "feedback_text": "Excellent response, very accurate and helpful!",
    "feedback_category": "accuracy",
    "trust_impact_calculated": 2.0,
    "trust_event_id": 9877,
    "applied_at": "2025-10-01T15:00:00Z",
    "review_status": "pending",
    "response_metadata": { "response_time_ms": 234, "model": "gpt-4" },
    "user_metadata": { "client_version": "1.2.3" },
    "created_at": "2025-10-01T15:00:00Z",
    "updated_at": "2025-10-01T15:00:00Z"
  },
  "message": "Feedback submitted successfully"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid request (missing required fields, invalid star_rating, duplicate feedback)
- `500 Internal Server Error` - Database or trust evaluation error

---

#### 5. Get Agent Feedback Stats

Retrieve aggregated feedback statistics for an agent.

**Endpoint:** `GET /api/v1/feedback/agent/{agent_id}/stats`

**Query Parameters:**
- `days` (optional) - Number of days to look back (default: 30)

**Example:**
```
GET /api/v1/feedback/agent/agent-abc-123/stats?days=7
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "agent_id": "agent-abc-123",
    "total_feedback": 142,
    "helpful_count": 128,
    "not_helpful_count": 14,
    "helpful_percent": 90.14,
    "avg_star_rating": 4.32,
    "rating_count": 135,
    "total_trust_impact": 56.5,
    "pending_reviews": 3,
    "flagged_reviews": 1
  }
}
```

**Response Schema:**
```go
type FeedbackStats struct {
    AgentID          string  `json:"agent_id"`
    TotalFeedback    int64   `json:"total_feedback"`     // Total feedback entries
    HelpfulCount     int64   `json:"helpful_count"`      // Count of is_helpful=true
    NotHelpfulCount  int64   `json:"not_helpful_count"`  // Count of is_helpful=false
    HelpfulPercent   float64 `json:"helpful_percent"`    // Percentage helpful
    AvgStarRating    float64 `json:"avg_star_rating"`    // Average star rating (0 if none)
    RatingCount      int64   `json:"rating_count"`       // Count with star_rating
    TotalTrustImpact float64 `json:"total_trust_impact"` // Sum of trust impacts
    PendingReviews   int64   `json:"pending_reviews"`    // Feedback awaiting admin review
    FlaggedReviews   int64   `json:"flagged_reviews"`    // Flagged as suspicious
}
```

---

#### 6. Get Feedback by ID

Retrieve a specific feedback record.

**Endpoint:** `GET /api/v1/feedback/{feedback_id}`

**Example:**
```
GET /api/v1/feedback/uuid-feedback-123
```

**Response:**
```json
{
  "success": true,
  "feedback": {
    "id": "uuid-feedback-123",
    "response_id": "resp-abc-789",
    "agent_id": "agent-abc-123",
    "user_id": "user-xyz-456",
    "organization_id": "org-company-001",
    "is_helpful": true,
    "star_rating": 5,
    "feedback_text": "Excellent response!",
    "feedback_category": "accuracy",
    "trust_impact_calculated": 2.0,
    "trust_event_id": 9877,
    "applied_at": "2025-10-01T15:00:00Z",
    "review_status": "approved",
    "created_at": "2025-10-01T15:00:00Z",
    "updated_at": "2025-10-01T15:00:00Z"
  }
}
```

**Error Responses:**
- `404 Not Found` - Feedback not found
- `500 Internal Server Error` - Database error

---

#### 7. List Feedback

List feedback with filtering and pagination.

**Endpoint:** `GET /api/v1/feedback`

**Query Parameters:**
- `agent_id` (optional) - Filter by agent
- `user_id` (optional) - Filter by user
- `organization_id` (optional) - Filter by organization
- `review_status` (optional) - Filter by status: `pending`, `approved`, `rejected`, `flagged`
- `min_star_rating` (optional) - Minimum star rating (1-5)
- `max_star_rating` (optional) - Maximum star rating (1-5)
- `limit` (optional) - Results per page (1-100, default: 50)
- `offset` (optional) - Offset for pagination (default: 0)

**Example:**
```
GET /api/v1/feedback?agent_id=agent-abc-123&review_status=pending&limit=20&offset=0
```

**Response:**
```json
{
  "success": true,
  "feedback": [
    {
      "id": "uuid-feedback-123",
      "response_id": "resp-abc-789",
      "agent_id": "agent-abc-123",
      "star_rating": 5,
      "trust_impact_calculated": 2.0,
      "review_status": "pending",
      "created_at": "2025-10-01T15:00:00Z"
    }
  ],
  "total": 142,
  "limit": 20,
  "offset": 0
}
```

---

## Event Publishing

The Governance Service publishes events to Redis streams for real-time updates.

### Redis Streams

1. **`trust-events`** - Trust score updates
2. **`governance-events`** - Governance decisions and permission changes

### Event Types

#### Trust Score Updated Event

**Stream:** `trust-events`
**Event Type:** `trust_score_updated` or `trust_tier_changed`

**Payload:**
```json
{
  "event_id": "uuid-event-123",
  "entity_id": "agent-abc-123",
  "entity_type": "agent",
  "old_score": 65.3,
  "new_score": 67.8,
  "old_tier": "trusted",
  "new_tier": "trusted",
  "tier": "trusted",
  "reason": "User marked helpful and rated 5/5 stars",
  "update_type": "score_change",
  "metadata": {
    "source": "user_feedback",
    "feedback_id": "uuid-feedback-123",
    "user_id": "user-xyz-456"
  },
  "timestamp": "2025-10-01T15:00:00Z"
}
```

**Update Types:**
- `score_change` - Score changed but tier stayed the same
- `tier_change` - Trust tier changed (promotion or demotion)
- `escalation` - Significant negative event requiring attention

#### Governance Decision Event

**Stream:** `governance-events`
**Event Type:** `governance_decision`

**Payload:**
```json
{
  "event_id": "uuid-event-456",
  "rule_id": "rule-789",
  "action": "triggered",
  "category": "permission_check",
  "actor_id": "agent-abc-123",
  "actor_type": "agent",
  "resource_id": "resource-xyz-001",
  "resource_type": "api",
  "decision": "allow",
  "reason": "Actor trust score (67.8) meets resource requirement (60.0)",
  "metadata": {
    "trust_score": 67.8,
    "required_trust": 60.0,
    "policies_evaluated": 3
  },
  "timestamp": "2025-10-01T15:05:00Z"
}
```

#### Permission Change Event

**Stream:** `governance-events`
**Event Type:** `permission_approved`, `permission_revoked`, `permission_denied`

**Payload:**
```json
{
  "event_id": "uuid-event-789",
  "permission_id": "perm-456",
  "actor_id": "agent-abc-123",
  "actor_type": "agent",
  "resource_id": "resource-xyz-001",
  "permission_type": "api_access",
  "old_status": "pending",
  "new_status": "approved",
  "changed_by": "admin-user-123",
  "reason": "Approved after trust verification",
  "metadata": {},
  "timestamp": "2025-10-01T15:10:00Z"
}
```

---

## SDK Implementation Guidelines

### Recommended SDK Components

#### 1. TrustClient

```python
class TrustClient:
    """Client for trust scoring operations"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def evaluate_trust(
        self,
        entity_id: str,
        entity_type: str,
        event_type: str,
        impact: float,
        description: str,
        metadata: dict = None
    ) -> TrustScore:
        """Submit a trust evaluation event"""
        pass

    def get_trust_score(
        self,
        entity_id: str,
        entity_type: str = "user"
    ) -> TrustScore:
        """Get current trust score for an entity"""
        pass

    def get_trust_history(
        self,
        entity_id: str,
        entity_type: str = "user",
        limit: int = 100
    ) -> List[TrustEvent]:
        """Get trust event history"""
        pass
```

#### 2. FeedbackClient

```python
class FeedbackClient:
    """Client for human feedback operations"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def submit_feedback(
        self,
        response_id: str,
        agent_id: str,
        user_id: str,
        organization_id: str,
        is_helpful: bool = None,
        star_rating: int = None,
        feedback_text: str = None,
        feedback_category: str = None,
        conversation_id: str = None,
        response_metadata: dict = None,
        user_metadata: dict = None
    ) -> AgentResponseFeedback:
        """Submit user feedback on agent response"""
        pass

    def get_agent_stats(
        self,
        agent_id: str,
        days: int = 30
    ) -> FeedbackStats:
        """Get aggregated feedback statistics"""
        pass

    def get_feedback(self, feedback_id: str) -> AgentResponseFeedback:
        """Get specific feedback by ID"""
        pass

    def list_feedback(
        self,
        agent_id: str = None,
        user_id: str = None,
        organization_id: str = None,
        review_status: str = None,
        min_star_rating: int = None,
        max_star_rating: int = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AgentResponseFeedback], int]:
        """List feedback with filtering"""
        pass
```

#### 3. EventSubscriber (Optional)

```python
class GovernanceEventSubscriber:
    """Subscribe to governance and trust events from Redis"""

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)

    def subscribe_trust_events(self, callback: Callable[[TrustScoreEvent], None]):
        """Subscribe to trust-events stream"""
        pass

    def subscribe_governance_events(self, callback: Callable[[GovernanceEvent], None]):
        """Subscribe to governance-events stream"""
        pass
```

---

## Data Models

### TrustScore

```python
@dataclass
class TrustScore:
    id: int
    entity_id: str
    entity_type: str  # "user", "agent", "service"
    score: float  # 0.0-100.0
    reputation_score: float
    behavior_score: float
    compliance_score: float
    last_updated: datetime
    created_at: datetime
```

### TrustEvent

```python
@dataclass
class TrustEvent:
    id: int
    entity_id: str
    entity_type: str
    event_type: str  # "positive", "negative", "compliance", "behavior"
    impact: float
    description: str
    metadata: str  # JSON string
    timestamp: datetime
    created_at: datetime
```

### AgentResponseFeedback

```python
@dataclass
class AgentResponseFeedback:
    id: str  # UUID
    response_id: str
    conversation_id: Optional[str]
    agent_id: str
    user_id: str
    organization_id: str
    is_helpful: Optional[bool]
    star_rating: Optional[int]  # 1-5
    feedback_text: Optional[str]
    feedback_category: Optional[str]
    trust_impact_calculated: Optional[float]
    trust_event_id: Optional[int]
    applied_at: Optional[datetime]
    review_status: str  # "pending", "approved", "rejected", "flagged"
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    response_metadata: dict
    user_metadata: dict
    created_at: datetime
    updated_at: datetime
```

### FeedbackStats

```python
@dataclass
class FeedbackStats:
    agent_id: str
    total_feedback: int
    helpful_count: int
    not_helpful_count: int
    helpful_percent: float
    avg_star_rating: float
    rating_count: int
    total_trust_impact: float
    pending_reviews: int
    flagged_reviews: int
```

---

## Integration Examples

### Example 1: Submit Trust Event

```python
from agion_sdk import TrustClient

# Initialize client
trust_client = TrustClient(
    base_url="http://governance-service:8080/api/v1",
    api_key="your-api-key"
)

# Submit positive trust event
trust_score = trust_client.evaluate_trust(
    entity_id="agent-abc-123",
    entity_type="agent",
    event_type="positive",
    impact=5.0,
    description="Successfully completed task with high quality",
    metadata={
        "task_id": "task-456",
        "quality_score": 0.95
    }
)

print(f"New trust score: {trust_score.score}")
print(f"Reputation: {trust_score.reputation_score}")
```

### Example 2: Submit User Feedback (Helpful + 5 Stars)

```python
from agion_sdk import FeedbackClient

# Initialize client
feedback_client = FeedbackClient(
    base_url="http://governance-service:8080/api/v1",
    api_key="your-api-key"
)

# User marks response as helpful with 5-star rating
feedback = feedback_client.submit_feedback(
    response_id="resp-abc-789",
    agent_id="agent-abc-123",
    user_id="user-xyz-456",
    organization_id="org-company-001",
    is_helpful=True,
    star_rating=5,
    feedback_text="Excellent response, very accurate and helpful!",
    feedback_category="accuracy",
    conversation_id="conv-123",
    response_metadata={
        "response_time_ms": 234,
        "model": "gpt-4"
    }
)

print(f"Feedback ID: {feedback.id}")
print(f"Trust impact: {feedback.trust_impact_calculated}%")  # +2.0%
print(f"Trust event ID: {feedback.trust_event_id}")
```

### Example 3: Submit Negative Feedback

```python
# User marks response as not helpful (no star rating)
feedback = feedback_client.submit_feedback(
    response_id="resp-xyz-999",
    agent_id="agent-abc-123",
    user_id="user-xyz-456",
    organization_id="org-company-001",
    is_helpful=False,
    feedback_text="Response was inaccurate and not helpful",
    feedback_category="accuracy"
)

print(f"Trust impact: {feedback.trust_impact_calculated}%")  # -2.0%
```

### Example 4: Get Agent Feedback Statistics

```python
# Get 7-day feedback stats
stats = feedback_client.get_agent_stats(
    agent_id="agent-abc-123",
    days=7
)

print(f"Total feedback: {stats.total_feedback}")
print(f"Helpful: {stats.helpful_percent}%")
print(f"Average rating: {stats.avg_star_rating}/5.0")
print(f"Total trust impact: {stats.total_trust_impact}%")
```

### Example 5: Check Agent Trust Before Action

```python
# Check if agent has sufficient trust for sensitive operation
trust_score = trust_client.get_trust_score(
    entity_id="agent-abc-123",
    entity_type="agent"
)

REQUIRED_TRUST = 60.0  # "trusted" tier minimum

if trust_score.score >= REQUIRED_TRUST:
    print("Agent authorized for sensitive operation")
    # Proceed with operation
else:
    print(f"Insufficient trust: {trust_score.score} < {REQUIRED_TRUST}")
    # Deny operation
```

### Example 6: Subscribe to Trust Events

```python
from agion_sdk import GovernanceEventSubscriber

# Initialize subscriber
subscriber = GovernanceEventSubscriber(
    redis_url="redis://redis-service:6379"
)

# Define callback
def on_trust_update(event):
    print(f"Trust updated for {event.entity_id}")
    print(f"Score: {event.old_score} → {event.new_score}")
    if event.update_type == "tier_change":
        print(f"Tier changed: {event.old_tier} → {event.new_tier}")

# Subscribe
subscriber.subscribe_trust_events(on_trust_update)
```

---

## Error Handling

### HTTP Error Codes

| Code | Meaning            | Common Causes                                      |
|------|--------------------|---------------------------------------------------|
| 400  | Bad Request        | Missing fields, invalid values, duplicate feedback|
| 401  | Unauthorized       | Missing/invalid API key                           |
| 404  | Not Found          | Entity or feedback not found                      |
| 429  | Too Many Requests  | Rate limit exceeded                               |
| 500  | Internal Error     | Database error, Redis unavailable                 |

### Error Response Format

```json
{
  "success": false,
  "error": "Bad Request",
  "message": "star_rating must be between 1 and 5",
  "details": "invalid star_rating",
  "timestamp": "2025-10-01T15:00:00Z"
}
```

### SDK Error Handling Example

```python
from agion_sdk import FeedbackClient, AgionAPIError

client = FeedbackClient(base_url="...", api_key="...")

try:
    feedback = client.submit_feedback(
        response_id="resp-123",
        agent_id="agent-456",
        user_id="user-789",
        organization_id="org-001",
        star_rating=6  # Invalid!
    )
except AgionAPIError as e:
    if e.status_code == 400:
        print(f"Validation error: {e.message}")
    elif e.status_code == 409:
        print("Duplicate feedback - already submitted")
    else:
        print(f"API error: {e}")
```

---

## Validation Rules Summary

### Trust Evaluation Request
- `entity_id` - Required, non-empty string
- `entity_type` - Required, must be: `user`, `agent`, `service`
- `event_type` - Required, must be: `positive`, `negative`, `compliance`, `behavior`
- `impact` - Required, must be -100.0 to +100.0
- `description` - Required, non-empty string
- `metadata` - Optional JSON object

### Feedback Submission Request
- `response_id` - Required, non-empty string
- `agent_id` - Required, non-empty string
- `user_id` - Required, non-empty string
- `organization_id` - Required, non-empty string
- Must provide at least one: `is_helpful` OR `star_rating`
- `star_rating` - If provided, must be 1-5
- `feedback_category` - If provided, must be: `accuracy`, `relevance`, `clarity`, `safety`, `speed`
- Unique constraint: Cannot submit duplicate feedback for same `response_id` + `user_id`

---

## Database Schema Reference

### trust_scores table

```sql
CREATE TABLE trust_scores (
    id BIGSERIAL PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    score DECIMAL(5,2) DEFAULT 50.0,
    reputation_score DECIMAL(5,2) DEFAULT 50.0,
    behavior_score DECIMAL(5,2) DEFAULT 50.0,
    compliance_score DECIMAL(5,2) DEFAULT 50.0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_entity UNIQUE(entity_id, entity_type)
);
```

### trust_events table

```sql
CREATE TABLE trust_events (
    id BIGSERIAL PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    impact DECIMAL(5,2) NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### agent_response_feedback table

```sql
CREATE TABLE agent_response_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255),
    agent_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    is_helpful BOOLEAN,
    star_rating INTEGER CHECK (star_rating >= 1 AND star_rating <= 5),
    feedback_text TEXT,
    feedback_category VARCHAR(50),
    trust_impact_calculated DECIMAL(5,2),
    trust_event_id BIGINT REFERENCES trust_events(id),
    applied_at TIMESTAMP WITH TIME ZONE,
    review_status VARCHAR(20) DEFAULT 'pending',
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    response_metadata JSONB DEFAULT '{}',
    user_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_feedback_per_user_response UNIQUE(response_id, user_id)
);
```

---

## Version History

| Version | Date       | Changes                                              |
|---------|------------|------------------------------------------------------|
| 1.0.0   | 2025-10-01 | Initial release - Trust scoring + Human feedback     |

---

## Support & Contact

For SDK integration support, please refer to:
- **Documentation:** `/docs/` directory in repository
- **API Specification:** This document
- **Trust Impact Algorithm:** `/internal/services/trust_impact_algorithm.go`
- **Implementation Status:** `/docs/HUMAN_FEEDBACK_IMPLEMENTATION_COMPLETE.md`

---

**End of SDK Integration Guide**
