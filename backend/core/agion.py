"""
Agion SDK Integration
Centralized SDK initialization and lifecycle management
"""

import logging
from typing import Optional
from agion_sdk import AgionSDK
from core.config import settings

logger = logging.getLogger(__name__)


class AgionClient:
    """
    Singleton wrapper for Agion SDK.

    Manages SDK lifecycle and provides global access to SDK instance.
    """

    _instance: Optional[AgionSDK] = None
    _initialized: bool = False

    @classmethod
    async def get_sdk(cls) -> AgionSDK:
        """
        Get or create SDK instance.

        Returns:
            AgionSDK instance

        Raises:
            RuntimeError: If SDK not initialized
        """
        if not cls._initialized:
            raise RuntimeError(
                "Agion SDK not initialized. Call AgionClient.initialize() first."
            )
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """
        Initialize Agion SDK.

        This should be called during application startup.
        """
        if cls._initialized:
            logger.warning("Agion SDK already initialized")
            return

        try:
            logger.info("Initializing Agion SDK...")

            # Create SDK instance
            cls._instance = AgionSDK(
                agent_id=settings.agion_agent_id,
                agent_version=settings.agion_agent_version,
                gateway_url=settings.agion_gateway_url,
                redis_url=settings.agion_redis_url,
                policy_sync_enabled=settings.agion_policy_sync_enabled,
                policy_sync_interval=30,  # 30 seconds
                policy_cache_ttl=60,      # 60 seconds
                event_buffer_size=100,
                event_flush_interval=5,   # 5 seconds
                config_cache_ttl=60,      # 60 seconds
                enable_metrics=True,
            )

            # Initialize connection
            await cls._instance.initialize()

            cls._initialized = True
            logger.info(
                f"Agion SDK initialized successfully for agent {settings.agion_agent_id}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Agion SDK: {e}")
            # Don't fail startup - agent can run without platform integration
            logger.warning("Agent will run without Agion platform integration")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shutdown Agion SDK.

        This should be called during application shutdown.
        """
        if not cls._initialized:
            return

        try:
            logger.info("Shutting down Agion SDK...")

            if cls._instance:
                await cls._instance.shutdown()

            cls._initialized = False
            cls._instance = None

            logger.info("Agion SDK shutdown complete")

        except Exception as e:
            logger.error(f"Error shutting down Agion SDK: {e}")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if SDK is initialized."""
        return cls._initialized

    @classmethod
    async def get_metrics(cls) -> dict:
        """
        Get SDK metrics.

        Returns:
            Dict with SDK metrics
        """
        if not cls._initialized or not cls._instance:
            return {"error": "SDK not initialized"}

        try:
            return cls._instance.get_metrics()
        except Exception as e:
            logger.error(f"Failed to get SDK metrics: {e}")
            return {"error": str(e)}


# Convenience function for getting SDK instance
async def get_agion_sdk() -> Optional[AgionSDK]:
    """
    Get Agion SDK instance.

    Returns:
        AgionSDK instance or None if not initialized
    """
    if not AgionClient.is_initialized():
        logger.warning("Agion SDK not initialized, returning None")
        return None

    return await AgionClient.get_sdk()
