"""Type definitions for Agion SDK."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PolicyDecision(str, Enum):
    """Policy evaluation decision."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"


class PolicyStatus(str, Enum):
    """Policy status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class EnforcementLevel(str, Enum):
    """Policy enforcement level."""
    ADVISORY = "advisory"
    SOFT = "soft"
    HARD = "hard"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Event types for trust and mission updates."""
    # Trust events
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    RESOURCE_OVERUSE = "resource_overuse"
    POLICY_VIOLATION = "policy_violation"
    USER_FEEDBACK = "user_feedback"

    # Mission events
    MISSION_JOINED = "mission_joined"
    MISSION_LEFT = "mission_left"
    STATE_UPDATED = "state_updated"
    MESSAGE_SENT = "message_sent"


class EventSeverity(str, Enum):
    """Event severity for trust calculations."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRITICAL = "critical"


# Policy Types

class PolicyRule(BaseModel):
    """Compiled policy rule for fast local evaluation."""
    id: str
    name: str
    expression: str
    decision: PolicyDecision
    priority: int = 100
    enforcement: EnforcementLevel = EnforcementLevel.SOFT
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyContext(BaseModel):
    """Context for policy evaluation."""
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    agent_id: str
    action: str
    resource: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    """Result of policy evaluation."""
    decision: PolicyDecision
    allowed: bool
    matched_policies: List[str] = Field(default_factory=list)
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Event Types

class TrustEvent(BaseModel):
    """Trust event for agent behavior tracking."""
    agent_id: str
    event_type: EventType
    severity: EventSeverity
    impact: float = Field(0.0, ge=-1.0, le=1.0, description="Trust impact from -1.0 to +1.0")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence from 0.0 to 1.0")
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class MissionParticipant(BaseModel):
    """Mission participant information."""
    mission_id: str
    participant_id: str
    role: str
    state: Dict[str, Any] = Field(default_factory=dict)
    joined_at: Optional[datetime] = None


class MissionMessage(BaseModel):
    """Message between mission participants."""
    mission_id: str
    from_participant: str
    to_participant: Optional[str] = None  # None = broadcast
    message_type: str
    content: Dict[str, Any]
    timestamp: Optional[datetime] = None


# Configuration Types

class PromptConfig(BaseModel):
    """Dynamic prompt configuration."""
    id: str
    name: str
    content: str
    variables: List[str] = Field(default_factory=list)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelConfig(BaseModel):
    """Dynamic model configuration."""
    id: str
    name: str
    provider: str
    model_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceConfig(BaseModel):
    """Dynamic resource configuration."""
    id: str
    name: str
    resource_type: str
    connection_string: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# SDK Configuration

class SDKConfig(BaseModel):
    """SDK initialization configuration."""
    agent_id: str
    agent_version: str = "1.0.0"
    gateway_url: str = "http://gateway:8080"
    redis_url: str = "redis://redis:6379"

    # Policy sync settings
    policy_sync_enabled: bool = True
    policy_sync_interval: int = 30  # seconds
    policy_cache_ttl: int = 60  # seconds

    # Event publishing settings
    event_buffer_size: int = 100
    event_flush_interval: int = 5  # seconds

    # Configuration cache settings
    config_cache_ttl: int = 60  # seconds

    # Performance settings
    max_policy_eval_time_ms: float = 1.0
    enable_metrics: bool = True

    # Fail-safe settings
    offline_mode: bool = False
    fail_open: bool = False  # If True, allow on policy fetch failure

    class Config:
        frozen = True


# User Context

class UserContext(BaseModel):
    """User context from JWT/authentication."""
    user_id: str
    org_id: str
    role: str
    permissions: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Execution Context

class ExecutionContext(BaseModel):
    """Context for agent execution."""
    execution_id: str
    agent_id: str
    user: Optional[UserContext] = None
    session_id: Optional[str] = None
    parent_execution_id: Optional[str] = None
    mission_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Metrics

class PolicyMetrics(BaseModel):
    """Policy enforcement metrics."""
    total_checks: int = 0
    allowed: int = 0
    denied: int = 0
    warned: int = 0
    average_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0


class EventMetrics(BaseModel):
    """Event publishing metrics."""
    total_published: int = 0
    publish_failures: int = 0
    average_latency_ms: float = 0.0
    buffer_size: int = 0


# LLM Interaction Types

class LLMInteraction(BaseModel):
    """Complete LLM interaction for audit trail."""
    execution_id: str
    agent_id: str
    interaction_id: str  # Unique ID for this specific LLM call
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Prompt details
    system_prompt: str
    user_prompt: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # [{role, content}]

    # Model details
    model: str
    provider: str  # e.g., "openai", "anthropic", "requesty"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None
    other_params: Dict[str, Any] = Field(default_factory=dict)

    # Response details
    response_text: str
    finish_reason: Optional[str] = None

    # Token usage
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Metadata
    latency_ms: float
    user_id: Optional[str] = None
    cost_estimate: Optional[float] = None  # Estimated cost in USD
    metadata: Dict[str, Any] = Field(default_factory=dict)
