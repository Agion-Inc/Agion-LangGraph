"""Background policy synchronization worker."""

import asyncio
import json
import logging
from typing import Callable, Optional
from datetime import datetime, timedelta

import redis.asyncio as aioredis
import aiohttp

from .types import PolicyRule, SDKConfig
from .exceptions import PolicySyncError

logger = logging.getLogger(__name__)


class PolicySyncWorker:
    """
    Background worker for policy synchronization.

    Uses Redis Pub/Sub for instant updates and HTTP polling as fallback.
    Runs in background without blocking agent execution.
    """

    def __init__(
        self,
        config: SDKConfig,
        on_policy_update: Callable[[list[PolicyRule]], None],
    ):
        self.config = config
        self.on_policy_update = on_policy_update

        self._redis: Optional[aioredis.Redis] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._pubsub_task: Optional[asyncio.Task] = None

        self._last_sync: Optional[datetime] = None
        self._sync_count = 0
        self._sync_errors = 0

    async def start(self) -> None:
        """Start the background sync worker."""
        if self._running:
            return

        self._running = True
        logger.info("Starting policy sync worker")

        try:
            # Connect to Redis for Pub/Sub
            self._redis = await aioredis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Create HTTP session
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )

            # Start Pub/Sub listener
            self._pubsub_task = asyncio.create_task(self._pubsub_listener())

            # Start periodic HTTP sync (fallback)
            self._sync_task = asyncio.create_task(self._periodic_sync())

            # Do initial sync
            await self._sync_policies()

        except Exception as e:
            logger.error(f"Failed to start policy sync worker: {e}")
            self._running = False
            raise PolicySyncError(f"Failed to start sync worker: {e}") from e

    async def stop(self) -> None:
        """Stop the background sync worker."""
        if not self._running:
            return

        logger.info("Stopping policy sync worker")
        self._running = False

        # Cancel tasks
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Close connections
        if self._redis:
            await self._redis.close()

        if self._http_session:
            await self._http_session.close()

    async def _pubsub_listener(self) -> None:
        """Listen for policy updates via Redis Pub/Sub."""
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe("agion:policy:updates")

            logger.info("Listening for policy updates on Redis Pub/Sub")

            async for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        logger.info(f"Received policy update: {data.get('event')}")

                        # Fetch latest policies
                        await self._sync_policies()

                    except Exception as e:
                        logger.error(f"Failed to process policy update: {e}")

        except asyncio.CancelledError:
            logger.info("Pub/Sub listener cancelled")
        except Exception as e:
            logger.error(f"Pub/Sub listener error: {e}")
            # Don't stop worker - HTTP fallback will continue

    async def _periodic_sync(self) -> None:
        """Periodic HTTP sync as fallback."""
        try:
            while self._running:
                await asyncio.sleep(self.config.policy_sync_interval)

                if not self._running:
                    break

                # Check if we need to sync (fallback if Pub/Sub missed updates)
                if self._should_sync():
                    await self._sync_policies()

        except asyncio.CancelledError:
            logger.info("Periodic sync cancelled")
        except Exception as e:
            logger.error(f"Periodic sync error: {e}")

    def _should_sync(self) -> bool:
        """Check if we should perform a sync."""
        if self._last_sync is None:
            return True

        # Sync if we haven't synced in the last interval
        elapsed = datetime.utcnow() - self._last_sync
        return elapsed.total_seconds() >= self.config.policy_sync_interval

    async def _sync_policies(self) -> None:
        """Fetch policies from Gateway Service via HTTP."""
        try:
            url = f"{self.config.gateway_url}/api/v1/governance/policies"
            params = {
                "agent_id": self.config.agent_id,
                "status": "active",
            }

            async with self._http_session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    policies_data = data.get("policies", [])

                    # Convert to PolicyRule objects
                    policies = [self._parse_policy(p) for p in policies_data]

                    # Update local policy engine
                    self.on_policy_update(policies)

                    self._last_sync = datetime.utcnow()
                    self._sync_count += 1

                    logger.info(f"Synced {len(policies)} policies")

                elif response.status == 404:
                    # No policies for this agent
                    self.on_policy_update([])
                    self._last_sync = datetime.utcnow()
                    logger.info("No policies found for agent")

                else:
                    error_text = await response.text()
                    logger.error(f"Failed to fetch policies: {response.status} {error_text}")
                    self._sync_errors += 1

        except Exception as e:
            logger.error(f"Policy sync failed: {e}")
            self._sync_errors += 1

            # Don't raise - keep worker running with cached policies

    def _parse_policy(self, data: dict) -> PolicyRule:
        """Parse policy data from API response."""
        return PolicyRule(
            id=data["id"],
            name=data["name"],
            expression=data.get("policy_expression", "True"),
            decision=data.get("enforcement", "allow"),
            priority=data.get("priority", 100),
            enforcement=data.get("enforcement_level", "soft"),
            metadata={
                "description": data.get("description"),
                "category": data.get("category"),
                "scope": data.get("scope", []),
                "owner": data.get("owner"),
            },
        )

    def get_metrics(self) -> dict:
        """Get sync worker metrics."""
        return {
            "running": self._running,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "sync_count": self._sync_count,
            "sync_errors": self._sync_errors,
        }
