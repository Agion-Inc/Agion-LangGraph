"""
Agion SDK - Lightweight governance, missions, and trust management for AI agents.

This SDK provides local-first policy enforcement with sub-millisecond latency,
automatic background synchronization, and fire-and-forget event publishing.

Example:
    from agion_sdk import AgionSDK

    sdk = AgionSDK(
        agent_id="langgraph-v2:my_agent",
        gateway_url="http://gateway:8080",
        redis_url="redis://redis:6379"
    )

    await sdk.initialize()

    @sdk.governed("my_agent", "process_data")
    async def process_data(state):
        # Your agent logic
        return result
"""

import logging
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime, timedelta

from .types import (
    SDKConfig,
    PolicyRule,
    PolicyContext,
    PolicyResult,
    UserContext,
    PromptConfig,
    ModelConfig,
    ResourceConfig,
    EventType,
    EventSeverity,
    LLMInteraction,
)
from .policy_engine import PolicyEngine
from .policy_sync import PolicySyncWorker
from .events import EventClient, MissionClient
from .decorators import GovernanceDecorator
from .governance_client import GovernanceClient
from .governance_models import (
    ResourceType,
    ActorType,
    PermissionType,
    ResourceStatus,
    PermissionStatus,
    RiskLevel,
    GovernanceResource,
    GovernancePermission,
    PermissionCheckResult,
)
from .exceptions import (
    InitializationError,
    ResourceNotFoundError,
    ConfigurationError,
    GovernanceAPIError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
)

__version__ = "0.2.0"
__all__ = [
    # SDK
    "AgionSDK",
    "MissionClient",
    "EventClient",
    "GovernanceClient",
    # Configuration
    "SDKConfig",
    # Policy
    "PolicyDecision",
    "PolicyResult",
    # Events
    "EventType",
    "EventSeverity",
    "UserContext",
    "LLMInteraction",
    "TrustEvent",
    # Governance enums
    "ResourceType",
    "ActorType",
    "PermissionType",
    "ResourceStatus",
    "PermissionStatus",
    "RiskLevel",
    # Governance models
    "GovernanceResource",
    "GovernancePermission",
    "PermissionCheckResult",
    # Exceptions
    "GovernanceAPIError",
    "PermissionDeniedError",
    "RateLimitError",
    "ServiceUnavailableError",
]

logger = logging.getLogger(__name__)


class AgionSDK:
    """
    Main SDK class for Agion agent governance.

    Features:
    - Local policy enforcement (< 1ms)
    - Background policy sync (Redis Pub/Sub + HTTP)
    - Event publishing (fire-and-forget)
    - Dynamic configuration (prompts, models, resources)
    - Mission coordination
    - RBAC integration

    Example:
        # Simple usage
        sdk = AgionSDK(agent_id="my-agent", redis_url="redis://localhost:6379")
        await sdk.initialize()
        try:
            # Use SDK
            pass
        finally:
            await sdk.disconnect()

        # Context manager (recommended)
        async with AgionSDK(agent_id="my-agent") as sdk:
            # Use SDK
            pass
    """

    def __init__(
        self,
        agent_id: str,
        agent_version: str = "1.0.0",
        gateway_url: str = "http://gateway:8080",
        redis_url: str = "redis://redis:6379",
        organization_id: Optional[str] = None,
        enable_governance: bool = False,
        **kwargs,
    ):
        """
        Initialize the Agion SDK.

        Args:
            agent_id: Unique agent identifier (e.g., "langgraph-v2:my_agent")
            agent_version: Agent version
            gateway_url: Gateway service URL
            redis_url: Redis connection URL
            organization_id: Organization ID for governance (required if enable_governance=True)
            enable_governance: Enable unified governance client
            **kwargs: Additional configuration options
        """
        self.config = SDKConfig(
            agent_id=agent_id,
            agent_version=agent_version,
            gateway_url=gateway_url,
            redis_url=redis_url,
            **kwargs,
        )

        # Core components
        self.policy_engine = PolicyEngine()
        self.event_client = EventClient(self.config)
        self.mission_client = MissionClient(self.event_client, agent_id)

        # Governance client (optional)
        self.governance: Optional[GovernanceClient] = None
        if enable_governance:
            if not organization_id:
                raise ConfigurationError("organization_id required when enable_governance=True")
            self.governance = GovernanceClient(
                base_url=f"{gateway_url}/api/v1",
                organization_id=organization_id
            )

        # Background workers
        self._policy_sync: Optional[PolicySyncWorker] = None
        self._http_session: Optional[aiohttp.ClientSession] = None

        # Configuration cache
        self._prompt_cache: Dict[str, tuple[PromptConfig, datetime]] = {}
        self._model_cache: Dict[str, tuple[ModelConfig, datetime]] = {}
        self._resource_cache: Dict[str, tuple[ResourceConfig, datetime]] = {}

        # Initialization state
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False

    async def initialize(self) -> None:
        """
        Initialize the SDK and start background workers.

        This must be called before using the SDK.
        """
        if self._initialized:
            return

        try:
            logger.info(f"Initializing Agion SDK for agent {self.config.agent_id}")

            # Create HTTP session
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )

            # Connect event client
            await self.event_client.connect()

            # Start policy sync worker
            if self.config.policy_sync_enabled:
                self._policy_sync = PolicySyncWorker(
                    config=self.config,
                    on_policy_update=self._on_policy_update,
                )
                await self._policy_sync.start()

            # Register agent
            await self._register_agent()

            self._initialized = True
            logger.info("Agion SDK initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SDK: {e}")
            raise InitializationError(f"Failed to initialize SDK: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect the SDK and cleanup resources."""
        if not self._initialized:
            return

        logger.info("Disconnecting Agion SDK")

        # Stop policy sync
        if self._policy_sync:
            await self._policy_sync.stop()

        # Disconnect event client
        await self.event_client.disconnect()

        # Close governance client
        if self.governance:
            await self.governance.close()

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()

        self._initialized = False
        logger.info("Agion SDK disconnected")

    async def shutdown(self) -> None:
        """Alias for disconnect() for backwards compatibility."""
        await self.disconnect()

    def governed(
        self,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
    ):
        """
        Decorator for governance enforcement.

        Args:
            agent_id: Agent identifier (defaults to SDK agent_id)
            action: Action being performed (defaults to function name)
            resource: Optional resource being accessed

        Example:
            @sdk.governed("my_agent", "process_data")
            async def process_data(state):
                return result
        """
        decorator = GovernanceDecorator(self)
        return decorator(agent_id, action, resource)

    async def check_policy(
        self,
        action: str,
        user: Optional[UserContext] = None,
        resource: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> PolicyResult:
        """
        Manually check policies without using the decorator.

        Args:
            action: Action being performed
            user: Optional user context
            resource: Optional resource being accessed
            metadata: Additional context metadata

        Returns:
            PolicyResult with decision and matched policies
        """
        context = PolicyContext(
            user_id=user.user_id if user else None,
            org_id=user.org_id if user else None,
            role=user.role if user else None,
            permissions=user.permissions if user else [],
            agent_id=self.config.agent_id,
            action=action,
            resource=resource,
            metadata=metadata or {},
        )

        return self.policy_engine.evaluate(context, user)

    # Configuration API

    async def get_prompt(
        self,
        location: str,
        use_cache: bool = True,
    ) -> PromptConfig:
        """
        Get a prompt configuration by location/name.

        Args:
            location: Prompt location or name
            use_cache: Whether to use cached value

        Returns:
            PromptConfig with current prompt data

        Raises:
            ResourceNotFoundError: If prompt not found
        """
        # Check cache
        if use_cache and location in self._prompt_cache:
            prompt, cached_at = self._prompt_cache[location]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.config.config_cache_ttl):
                return prompt

        # Fetch from API
        try:
            url = f"{self.config.gateway_url}/api/v1/prompts/by-location/{location}"
            async with self._http_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    prompt = PromptConfig(**data)

                    # Cache
                    self._prompt_cache[location] = (prompt, datetime.utcnow())

                    return prompt
                elif response.status == 404:
                    raise ResourceNotFoundError("Prompt", location)
                else:
                    raise ConfigurationError(f"Failed to fetch prompt: {response.status}")

        except Exception as e:
            if isinstance(e, (ResourceNotFoundError, ConfigurationError)):
                raise
            raise ConfigurationError(f"Failed to fetch prompt: {e}") from e

    async def get_model(
        self,
        purpose: str,
        use_cache: bool = True,
    ) -> ModelConfig:
        """
        Get a model configuration by purpose/name.

        Args:
            purpose: Model purpose or name
            use_cache: Whether to use cached value

        Returns:
            ModelConfig with current model data
        """
        # Check cache
        if use_cache and purpose in self._model_cache:
            model, cached_at = self._model_cache[purpose]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.config.config_cache_ttl):
                return model

        # Fetch from API
        try:
            url = f"{self.config.gateway_url}/api/v1/models/by-purpose/{purpose}"
            async with self._http_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    model = ModelConfig(**data)

                    # Cache
                    self._model_cache[purpose] = (model, datetime.utcnow())

                    return model
                elif response.status == 404:
                    raise ResourceNotFoundError("Model", purpose)
                else:
                    raise ConfigurationError(f"Failed to fetch model: {response.status}")

        except Exception as e:
            if isinstance(e, (ResourceNotFoundError, ConfigurationError)):
                raise
            raise ConfigurationError(f"Failed to fetch model: {e}") from e

    async def get_resource(
        self,
        name: str,
        use_cache: bool = True,
    ) -> ResourceConfig:
        """
        Get a resource configuration by name.

        Args:
            name: Resource name
            use_cache: Whether to use cached value

        Returns:
            ResourceConfig with current resource data
        """
        # Check cache
        if use_cache and name in self._resource_cache:
            resource, cached_at = self._resource_cache[name]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.config.config_cache_ttl):
                return resource

        # Fetch from API
        try:
            url = f"{self.config.gateway_url}/api/v1/resources/by-name/{name}"
            async with self._http_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    resource = ResourceConfig(**data)

                    # Cache
                    self._resource_cache[name] = (resource, datetime.utcnow())

                    return resource
                elif response.status == 404:
                    raise ResourceNotFoundError("Resource", name)
                else:
                    raise ConfigurationError(f"Failed to fetch resource: {response.status}")

        except Exception as e:
            if isinstance(e, (ResourceNotFoundError, ConfigurationError)):
                raise
            raise ConfigurationError(f"Failed to fetch resource: {e}") from e

    # User feedback

    async def report_user_feedback(
        self,
        execution_id: str,
        user_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> None:
        """
        Report user feedback on agent execution.

        Args:
            execution_id: Execution identifier
            user_id: User who provided feedback
            feedback_type: Type of feedback (thumbs_up/thumbs_down)
            rating: Optional rating (1-5)
            comment: Optional comment
        """
        await self.event_client.publish_user_feedback(
            execution_id=execution_id,
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
        )

    # Internal methods

    def _on_policy_update(self, policies: List[PolicyRule]) -> None:
        """Callback for policy updates from sync worker."""
        self.policy_engine.load_policies(policies)
        logger.info(f"Loaded {len(policies)} policies")

    async def _register_agent(self) -> None:
        """Register agent with Gateway Service."""
        try:
            url = f"{self.config.gateway_url}/api/v1/agents/register"
            data = {
                "agent_id": self.config.agent_id,
                "version": self.config.agent_version,
                "status": "active",
                "registered_at": datetime.utcnow().isoformat(),
            }

            async with self._http_session.post(url, json=data) as response:
                if response.status in (200, 201):
                    logger.info(f"Registered agent {self.config.agent_id}")
                else:
                    logger.warning(f"Failed to register agent: {response.status}")

        except Exception as e:
            logger.warning(f"Failed to register agent: {e}")
            # Don't fail initialization if registration fails

    # Metrics

    def get_metrics(self) -> Dict:
        """Get SDK metrics."""
        return {
            "policy_engine": self.policy_engine.get_metrics(),
            "event_client": self.event_client.get_metrics(),
            "policy_sync": self._policy_sync.get_metrics() if self._policy_sync else None,
            "cache_sizes": {
                "prompts": len(self._prompt_cache),
                "models": len(self._model_cache),
                "resources": len(self._resource_cache),
            },
        }
