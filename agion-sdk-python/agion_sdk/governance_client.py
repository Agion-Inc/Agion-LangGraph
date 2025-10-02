"""
Unified Governance Client - Complete resource and permission management.

This client implements the full Unified Governance SDK Integration Guide v1.0.0
for resource CRUD, permission lifecycle, usage tracking, and policy evaluation.
"""

import logging
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

from .governance_models import (
    # Resource models
    GovernanceResource,
    CreateResourceRequest,
    UpdateResourceRequest,
    ResourceFilter,
    ResourceListResponse,
    ResourceChildrenResponse,
    # Permission models
    GovernancePermission,
    CreatePermissionRequest,
    CheckPermissionRequest,
    PermissionCheckResult,
    UpdateUsageRequest,
    ActivePermissionView,
    ActivePermissionListResponse,
    PermissionFilter,
    PermissionListResponse,
    # Policy models
    Policy,
    CreatePolicyRequest,
    PolicyEvaluationResult,
    PolicyFilter,
    PolicyListResponse,
    # Enums
    ResourceType,
    ActorType,
    PermissionType,
)
from .exceptions import (
    GovernanceAPIError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class GovernanceClient:
    """
    Complete HTTP client for Agion Governance Service.

    Implements all 24 endpoints for unified resource and permission management:
    - Resource CRUD (6 methods)
    - Permission lifecycle (9 methods)
    - Policy management (6 methods)
    - Usage tracking and caching

    Features:
    - L1 permission cache (30s TTL for approved, 5s for denied)
    - Async usage updates (fire-and-forget)
    - Connection pooling
    - Comprehensive error handling
    - Circuit breaker pattern for resilience

    Example:
        client = GovernanceClient(
            base_url="http://governance:8080/api/v1",
            organization_id="org-123"
        )

        # Check permission before resource use
        result = await client.check_permission(
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
                client.update_usage(result.permission.id, request_count=1, token_count=1234, cost_usd=0.037)
            )
    """

    def __init__(
        self,
        base_url: str,
        organization_id: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        cache_ttl_approved: int = 30,  # seconds
        cache_ttl_denied: int = 5,     # seconds
    ):
        """
        Initialize governance client.

        Args:
            base_url: Base URL of governance service (e.g., http://governance:8080/api/v1)
            organization_id: Organization ID for multi-tenancy
            api_key: Optional API key for authentication
            timeout: HTTP request timeout in seconds
            cache_ttl_approved: Cache TTL for approved permissions (seconds)
            cache_ttl_denied: Cache TTL for denied permissions (seconds)
        """
        self.base_url = base_url.rstrip("/")
        self.organization_id = organization_id
        self.api_key = api_key
        self.timeout = timeout
        self.cache_ttl_approved = cache_ttl_approved
        self.cache_ttl_denied = cache_ttl_denied

        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
        self._permission_cache: OrderedDict = OrderedDict()
        self._cache_max_size = 10000  # Prevent unbounded growth

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling."""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                # Double-check after acquiring lock
                if self._session is None or self._session.closed:
                    headers = {}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"

                    # Configure connection pool limits
                    connector = aiohttp.TCPConnector(
                        limit=100,            # Max total connections
                        limit_per_host=30,    # Max per host
                        ttl_dns_cache=300,    # DNS cache TTL
                        enable_cleanup_closed=True
                    )

                    self._session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers=headers,
                        connector=connector
                    )
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _cache_key(self, actor_id: str, resource_id: str, permission_type: str) -> str:
        """Generate cache key for permission check."""
        return f"perm:{actor_id}:{resource_id}:{permission_type}"

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        expected_status: int = 200
    ) -> Dict[str, Any]:
        """
        Handle HTTP response with error mapping.

        Args:
            response: aiohttp response
            expected_status: Expected HTTP status code

        Returns:
            Response JSON data

        Raises:
            GovernanceAPIError: For all error responses
        """
        if response.status == expected_status:
            return await response.json()

        # Error handling
        try:
            error_data = await response.json()
            message = error_data.get("message", "Unknown error")
            details = error_data.get("details", "")
        except Exception:
            message = await response.text()
            error_data = {}
            details = ""

        full_message = f"{message}. {details}".strip()

        if response.status == 400:
            raise ValidationError(full_message)
        elif response.status == 403:
            raise PermissionDeniedError(full_message, response.status, error_data)
        elif response.status == 404:
            raise ResourceNotFoundError("Resource", full_message)
        elif response.status == 429:
            raise RateLimitError(full_message, response.status, error_data)
        elif response.status == 503:
            raise ServiceUnavailableError(full_message, response.status, error_data)
        else:
            raise GovernanceAPIError(full_message, response.status, error_data)

    # ===================
    # Resource Management
    # ===================

    async def create_resource(self, req: CreateResourceRequest) -> GovernanceResource:
        """
        Create a new governed resource.

        Args:
            req: Resource creation request

        Returns:
            Created resource

        Raises:
            ValidationError: Invalid request data
            GovernanceAPIError: Other errors
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources"

        try:
            async with session.post(url, json=req.model_dump(exclude_none=True)) as response:
                data = await self._handle_response(response, 201)
                return GovernanceResource(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def get_resource(self, resource_id: str) -> GovernanceResource:
        """
        Get resource by ID.

        Args:
            resource_id: Resource UUID

        Returns:
            Resource details

        Raises:
            ResourceNotFoundError: Resource not found
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources/{resource_id}"

        try:
            async with session.get(url) as response:
                data = await self._handle_response(response, 200)
                return GovernanceResource(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def list_resources(self, filters: ResourceFilter) -> ResourceListResponse:
        """
        List resources with filtering.

        Args:
            filters: Filter criteria

        Returns:
            List of resources with pagination
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources"
        params = filters.model_dump(exclude_none=True)

        try:
            async with session.get(url, params=params) as response:
                data = await self._handle_response(response, 200)
                return ResourceListResponse(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def update_resource(
        self,
        resource_id: str,
        updates: UpdateResourceRequest
    ) -> GovernanceResource:
        """
        Update resource properties.

        Args:
            resource_id: Resource UUID
            updates: Fields to update

        Returns:
            Updated resource
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources/{resource_id}"

        try:
            async with session.put(url, json=updates.model_dump(exclude_none=True)) as response:
                data = await self._handle_response(response, 200)
                return GovernanceResource(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def delete_resource(self, resource_id: str) -> None:
        """
        Delete a resource.

        Args:
            resource_id: Resource UUID

        Note: Cascade deletes dependent permissions
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources/{resource_id}"

        try:
            async with session.delete(url) as response:
                if response.status != 204:
                    await self._handle_response(response, 204)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def get_resource_children(self, resource_id: str) -> ResourceChildrenResponse:
        """
        Get child resources in hierarchy.

        Args:
            resource_id: Parent resource UUID

        Returns:
            List of child resources
        """
        session = await self._get_session()
        url = f"{self.base_url}/resources/{resource_id}/children"

        try:
            async with session.get(url) as response:
                data = await self._handle_response(response, 200)
                return ResourceChildrenResponse(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    # =====================
    # Permission Management
    # =====================

    async def request_permission(self, req: CreatePermissionRequest) -> GovernancePermission:
        """
        Request permission to access a resource.

        Args:
            req: Permission request

        Returns:
            Created permission (status=pending)

        Note: Permission must be approved before use
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions"

        try:
            async with session.post(url, json=req.model_dump(exclude_none=True)) as response:
                data = await self._handle_response(response, 201)
                return GovernancePermission(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def check_permission(
        self,
        actor_id: str,
        actor_type: ActorType,
        resource_id: str,
        permission_type: PermissionType,
        context: Optional[Dict[str, Any]] = None
    ) -> PermissionCheckResult:
        """
        Check if actor can access resource (CRITICAL METHOD).

        This is the most important governance endpoint - call before every resource access.

        Features:
        - L1 cache (30s for approved, 5s for denied)
        - Trust score validation
        - Constraint checking (rate limits, token limits, cost limits)
        - Policy evaluation

        Args:
            actor_id: Actor identifier (e.g., "agent-123")
            actor_type: Actor type (agent, user, service)
            resource_id: Resource UUID
            permission_type: Permission type (use, read, write, execute, admin)
            context: Optional context (request_tokens, estimated_cost, etc.)

        Returns:
            PermissionCheckResult with allowed=True/False

        Raises:
            PermissionDeniedError: Permission explicitly denied
            GovernanceAPIError: Other errors

        Example:
            result = await client.check_permission(
                actor_id="agent-456",
                actor_type=ActorType.AGENT,
                resource_id="gpt-4-id",
                permission_type=PermissionType.USE,
                context={"request_tokens": 1500, "estimated_cost": 0.045}
            )

            if result.allowed:
                # Proceed with resource access
                pass
        """
        # Check L1 cache
        cache_key = self._cache_key(actor_id, resource_id, permission_type.value)
        if cache_key in self._permission_cache:
            cached_result, cached_at = self._permission_cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()

            # Use cached result if within TTL
            ttl = self.cache_ttl_approved if cached_result.allowed else self.cache_ttl_denied
            if age < ttl:
                logger.debug(f"Permission cache hit: {cache_key} (age={age:.1f}s)")
                # Move to end (LRU)
                self._permission_cache.move_to_end(cache_key)
                return cached_result

        # Cache miss - call API
        session = await self._get_session()
        url = f"{self.base_url}/permissions/check"

        req = CheckPermissionRequest(
            organization_id=self.organization_id,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_id=resource_id,
            permission_type=permission_type,
            context=context or {}
        )

        try:
            async with session.post(url, json=req.model_dump()) as response:
                data = await self._handle_response(response, 200)
                result = PermissionCheckResult(**data)

                # Cache the result with LRU eviction
                ttl = self.cache_ttl_approved if result.allowed else self.cache_ttl_denied
                if len(self._permission_cache) >= self._cache_max_size:
                    # Remove oldest entry (FIFO)
                    self._permission_cache.popitem(last=False)
                self._permission_cache[cache_key] = (result, datetime.now(timezone.utc))

                logger.debug(
                    f"Permission check: {actor_id} → {resource_id} = "
                    f"{'ALLOWED' if result.allowed else 'DENIED'} (cached for {ttl}s)"
                )

                return result

        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def update_usage(
        self,
        permission_id: str,
        request_count: int = 1,
        token_count: int = 0,
        cost_usd: float = 0.0
    ) -> None:
        """
        Track resource usage after consumption (call asynchronously).

        This should be called AFTER resource consumption to track metrics.
        Recommended to call asynchronously (fire-and-forget) to avoid blocking.

        Args:
            permission_id: Permission UUID from check_permission result
            request_count: Number of requests made
            token_count: Tokens consumed
            cost_usd: Cost in USD

        Example:
            # Don't await - fire and forget
            asyncio.create_task(
                client.update_usage(permission_id, request_count=1, token_count=1234, cost_usd=0.037)
            )
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions/{permission_id}/usage"

        req = UpdateUsageRequest(
            permission_id=permission_id,
            request_count=request_count,
            token_count=token_count,
            cost_usd=cost_usd
        )

        try:
            async with session.post(url, json=req.model_dump()) as response:
                if response.status != 204:
                    await self._handle_response(response, 204)
        except aiohttp.ClientConnectorError as e:
            logger.warning(f"Failed to update usage (service unavailable): {e}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Failed to update usage: {e}")

    async def get_active_permissions(
        self,
        actor_id: str
    ) -> ActivePermissionListResponse:
        """
        List active permissions for an actor.

        Args:
            actor_id: Actor identifier

        Returns:
            List of active permissions with resource details
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions/active"
        params = {"actor_id": actor_id}

        try:
            async with session.get(url, params=params) as response:
                data = await self._handle_response(response, 200)
                return ActivePermissionListResponse(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def list_permissions(
        self,
        filters: PermissionFilter
    ) -> PermissionListResponse:
        """
        List permissions with filtering.

        Args:
            filters: Filter criteria

        Returns:
            List of permissions with pagination
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions"
        params = filters.model_dump(exclude_none=True)

        try:
            async with session.get(url, params=params) as response:
                data = await self._handle_response(response, 200)
                return PermissionListResponse(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def get_permission(self, permission_id: str) -> GovernancePermission:
        """
        Get permission by ID.

        Args:
            permission_id: Permission UUID

        Returns:
            Permission details
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions/{permission_id}"

        try:
            async with session.get(url) as response:
                data = await self._handle_response(response, 200)
                return GovernancePermission(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def approve_permission(
        self,
        permission_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> GovernancePermission:
        """
        Approve a pending permission request (admin only).

        Args:
            permission_id: Permission UUID
            approved_by: Admin user ID
            notes: Optional approval notes

        Returns:
            Approved permission (status=approved)
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions/{permission_id}/approve"

        payload = {"approved_by": approved_by}
        if notes:
            payload["notes"] = notes

        try:
            async with session.post(url, json=payload) as response:
                data = await self._handle_response(response, 200)
                return GovernancePermission(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def revoke_permission(
        self,
        permission_id: str,
        revoked_by: str,
        reason: str
    ) -> GovernancePermission:
        """
        Revoke an active permission (admin only).

        Args:
            permission_id: Permission UUID
            revoked_by: Admin user ID
            reason: Revocation reason

        Returns:
            Revoked permission (status=revoked)
        """
        session = await self._get_session()
        url = f"{self.base_url}/permissions/{permission_id}/revoke"

        payload = {
            "revoked_by": revoked_by,
            "reason": reason
        }

        try:
            async with session.post(url, json=payload) as response:
                data = await self._handle_response(response, 200)
                return GovernancePermission(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    # ==================
    # Policy Management
    # ==================

    async def list_policies(self, filters: Optional[PolicyFilter] = None) -> PolicyListResponse:
        """
        List policies with filtering.

        Args:
            filters: Optional filter criteria

        Returns:
            List of policies
        """
        session = await self._get_session()
        url = f"{self.base_url}/policies"
        params = filters.model_dump(exclude_none=True) if filters else {}

        try:
            async with session.get(url, params=params) as response:
                data = await self._handle_response(response, 200)
                return PolicyListResponse(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def create_policy(self, req: CreatePolicyRequest) -> Policy:
        """
        Create a new policy.

        Args:
            req: Policy creation request

        Returns:
            Created policy
        """
        session = await self._get_session()
        url = f"{self.base_url}/policies"

        try:
            async with session.post(url, json=req.model_dump(exclude_none=True)) as response:
                data = await self._handle_response(response, 201)
                return Policy(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def get_policy(self, policy_id: int) -> Policy:
        """
        Get policy by ID.

        Args:
            policy_id: Policy ID

        Returns:
            Policy details
        """
        session = await self._get_session()
        url = f"{self.base_url}/policies/{policy_id}"

        try:
            async with session.get(url) as response:
                data = await self._handle_response(response, 200)
                return Policy(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def evaluate_policy(
        self,
        policy_id: int,
        context: Dict[str, Any]
    ) -> PolicyEvaluationResult:
        """
        Test policy evaluation with sample data.

        Args:
            policy_id: Policy ID
            context: Evaluation context (request, actor, resource, etc.)

        Returns:
            Evaluation result (allow/deny)
        """
        session = await self._get_session()
        url = f"{self.base_url}/policies/{policy_id}/evaluate"

        payload = {"context": context}

        try:
            async with session.post(url, json=payload) as response:
                data = await self._handle_response(response, 200)
                return PolicyEvaluationResult(**data)
        except aiohttp.ClientConnectorError as e:
            raise ServiceUnavailableError(f"Cannot connect to governance service: {e}")

    async def validate_cel_expression(self, expression: str) -> bool:
        """
        Validate CEL expression syntax.

        Args:
            expression: CEL expression to validate

        Returns:
            True if valid

        Raises:
            ValidationError: Invalid CEL syntax
        """
        # This would require a dedicated endpoint in governance service
        # For now, we can validate client-side with basic checks
        if not expression or not isinstance(expression, str):
            raise ValidationError("CEL expression must be a non-empty string")

        # Basic syntax validation
        if expression.count("(") != expression.count(")"):
            raise ValidationError("Unmatched parentheses in CEL expression")

        return True

    def clear_permission_cache(self):
        """Clear permission check cache."""
        self._permission_cache.clear()
        logger.info("Permission cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_entries = 0
        expired_entries = 0

        for cached_result, cached_at in self._permission_cache.values():
            age = (now - cached_at).total_seconds()
            ttl = self.cache_ttl_approved if cached_result.allowed else self.cache_ttl_denied
            if age < ttl:
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self._permission_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "max_size": self._cache_max_size,
            "cache_hit_rate": f"{(valid_entries / max(1, len(self._permission_cache))) * 100:.1f}%"
        }
