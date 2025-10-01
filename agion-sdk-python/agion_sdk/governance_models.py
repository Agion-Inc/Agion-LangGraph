"""
Data models for Unified Governance System.

These models align with the Unified Governance SDK Integration Guide v1.0.0
for resource management, permission control, and policy evaluation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Enums

class ResourceType(str, Enum):
    """Types of governed resources."""
    MODEL_PROVIDER = "model_provider"
    AI_MODEL = "ai_model"
    DATABASE = "database"
    API = "api"
    STORAGE = "storage"
    MCP_SERVER = "mcp_server"
    TOOL = "tool"
    WEBHOOK = "webhook"
    COMPUTE = "compute"


class ActorType(str, Enum):
    """Types of actors that can access resources."""
    AGENT = "agent"
    USER = "user"
    SERVICE = "service"


class PermissionType(str, Enum):
    """Types of permissions for resources."""
    USE = "use"              # Use/consume resource
    READ = "read"            # Read resource metadata
    WRITE = "write"          # Modify resource
    EXECUTE = "execute"      # Execute operations
    ADMIN = "admin"          # Full administrative access


class ResourceStatus(str, Enum):
    """Resource availability status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"
    DEPRECATED = "deprecated"


class ResourceHealthStatus(str, Enum):
    """Resource health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PermissionStatus(str, Enum):
    """Permission lifecycle status."""
    PENDING = "pending"           # Awaiting approval
    APPROVED = "approved"         # Approved, can be used
    DENIED = "denied"             # Request denied
    REVOKED = "revoked"           # Previously approved, now revoked
    SUSPENDED = "suspended"       # Temporarily suspended


class RiskLevel(str, Enum):
    """Resource risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyLanguage(str, Enum):
    """Policy expression language."""
    JSON = "json"
    CEL = "cel"


# Resource Models

class GovernanceResource(BaseModel):
    """A governed resource in the platform."""
    id: str
    organization_id: str
    resource_type: ResourceType
    name: str
    resource_data: Dict[str, Any] = Field(default_factory=dict)
    status: ResourceStatus
    health_status: ResourceHealthStatus
    created_at: datetime
    updated_at: datetime
    parent_resource_id: Optional[str] = None
    description: Optional[str] = None
    compliance_labels: List[str] = Field(default_factory=list)
    data_residency: Optional[str] = None
    trust_tier_required: int = Field(0, ge=0, le=100)
    risk_level: RiskLevel = RiskLevel.LOW
    health_check_at: Optional[datetime] = None
    health_message: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class CreateResourceRequest(BaseModel):
    """Request to create a new resource."""
    organization_id: str
    resource_type: ResourceType
    name: str
    resource_data: Dict[str, Any]
    created_by: str
    parent_resource_id: Optional[str] = None
    description: Optional[str] = None
    compliance_labels: List[str] = Field(default_factory=list)
    data_residency: Optional[str] = None
    trust_tier_required: int = Field(0, ge=0, le=100)
    risk_level: RiskLevel = RiskLevel.LOW
    status: ResourceStatus = ResourceStatus.ACTIVE
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateResourceRequest(BaseModel):
    """Request to update a resource."""
    name: Optional[str] = None
    description: Optional[str] = None
    resource_data: Optional[Dict[str, Any]] = None
    trust_tier_required: Optional[int] = Field(None, ge=0, le=100)
    risk_level: Optional[RiskLevel] = None
    status: Optional[ResourceStatus] = None
    health_status: Optional[ResourceHealthStatus] = None
    health_message: Optional[str] = None
    tags: Optional[List[str]] = None
    updated_by: Optional[str] = None


class ResourceFilter(BaseModel):
    """Filter criteria for listing resources."""
    organization_id: str
    resource_type: Optional[ResourceType] = None
    status: Optional[ResourceStatus] = None
    health_status: Optional[ResourceHealthStatus] = None
    risk_level: Optional[RiskLevel] = None
    parent_resource_id: Optional[str] = None
    tags: Optional[List[str]] = None
    compliance_labels: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Permission Models

class PermissionConstraints(BaseModel):
    """Usage constraints for permissions."""
    rate_limit_rpm: Optional[int] = None
    token_limit_per_day: Optional[int] = None
    cost_limit_per_day_usd: Optional[float] = None
    allowed_hours: Optional[str] = None
    allowed_days: Optional[List[str]] = None


class UsageTracking(BaseModel):
    """Resource usage tracking."""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    current_day_requests: int = 0
    current_day_tokens: int = 0
    current_day_cost_usd: float = 0.0
    last_used_at: Optional[datetime] = None
    current_day_start: Optional[datetime] = None


class GovernancePermission(BaseModel):
    """A permission granting access to a resource."""
    id: str
    actor_id: str
    actor_type: ActorType
    resource_id: str
    permission_type: PermissionType
    status: PermissionStatus
    purpose: str
    constraints: PermissionConstraints = Field(default_factory=PermissionConstraints)
    usage_tracking: UsageTracking = Field(default_factory=UsageTracking)
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


class CreatePermissionRequest(BaseModel):
    """Request permission to access a resource."""
    actor_id: str
    actor_type: ActorType
    resource_id: str
    permission_type: PermissionType
    purpose: str
    justification: Optional[str] = None
    constraints: Optional[PermissionConstraints] = None
    requested_by: Optional[str] = None


class CheckPermissionRequest(BaseModel):
    """Check if an actor can access a resource."""
    organization_id: str
    actor_id: str
    actor_type: ActorType
    resource_id: str
    permission_type: PermissionType
    context: Dict[str, Any] = Field(default_factory=dict)


class PermissionCheckResult(BaseModel):
    """Result of permission check."""
    allowed: bool
    reason: str
    timestamp: datetime
    permission: Optional[GovernancePermission] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateUsageRequest(BaseModel):
    """Update resource usage after consumption."""
    permission_id: str
    request_count: int = 1
    token_count: int = 0
    cost_usd: float = 0.0


class ActivePermissionView(BaseModel):
    """View of active permission with resource details."""
    permission_id: str
    actor_id: str
    actor_type: ActorType
    permission_type: PermissionType
    status: PermissionStatus
    resource_name: str
    resource_type: ResourceType
    compliance_labels: List[str] = Field(default_factory=list)
    constraints: PermissionConstraints = Field(default_factory=PermissionConstraints)
    usage_tracking: UsageTracking = Field(default_factory=UsageTracking)
    approved_at: Optional[datetime] = None
    created_at: datetime


class PermissionFilter(BaseModel):
    """Filter criteria for listing permissions."""
    actor_id: Optional[str] = None
    actor_type: Optional[ActorType] = None
    resource_id: Optional[str] = None
    permission_type: Optional[PermissionType] = None
    status: Optional[PermissionStatus] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Policy Models

class Policy(BaseModel):
    """Policy rule for governance."""
    id: int
    name: str
    description: str
    type: str  # access, dlp, compliance, rate_limit
    category: str
    priority: int
    enabled: bool
    policy_language: PolicyLanguage
    created_at: datetime
    updated_at: datetime
    policy_expr: Optional[str] = None  # CEL expression
    rules: Optional[str] = None  # JSON string
    actions: Optional[str] = None  # JSON string
    tags: List[str] = Field(default_factory=list)
    is_system_policy: bool = False
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class CreatePolicyRequest(BaseModel):
    """Request to create a new policy."""
    name: str
    description: str
    type: str
    category: str
    priority: int
    enabled: bool
    policy_language: PolicyLanguage
    policy_expr: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation."""
    policy_id: str
    result: str  # "allow" or "deny"
    reason: str
    timestamp: datetime


class PolicyFilter(BaseModel):
    """Filter criteria for listing policies."""
    type: Optional[str] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# Response wrappers

class ResourceListResponse(BaseModel):
    """Response for listing resources."""
    resources: List[GovernanceResource]
    total: int
    limit: int
    offset: int


class PermissionListResponse(BaseModel):
    """Response for listing permissions."""
    permissions: List[GovernancePermission]
    total: int
    limit: int
    offset: int


class ActivePermissionListResponse(BaseModel):
    """Response for listing active permissions."""
    permissions: List[ActivePermissionView]
    total: int


class PolicyListResponse(BaseModel):
    """Response for listing policies."""
    policies: List[Policy]
    total: int


class ResourceChildrenResponse(BaseModel):
    """Response for listing resource children."""
    children: List[GovernanceResource]
    total: int
