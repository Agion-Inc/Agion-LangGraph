"""Event publishing to Redis Streams for trust and mission coordination."""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import deque

import redis.asyncio as aioredis

from .types import (
    TrustEvent,
    MissionParticipant,
    MissionMessage,
    EventType,
    EventSeverity,
    SDKConfig,
    LLMInteraction,
)
from .exceptions import EventPublishError

logger = logging.getLogger(__name__)


class EventClient:
    """
    Client for publishing events to Redis Streams.

    Features:
    - Fire-and-forget publishing (doesn't block agent execution)
    - Buffered publishing for better performance
    - Automatic retry on failure
    - Metrics tracking
    """

    def __init__(self, config: SDKConfig):
        self.config = config
        self._redis: Optional[aioredis.Redis] = None
        self._buffer: deque = deque(maxlen=config.event_buffer_size)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._published_count = 0
        self._failed_count = 0
        self._total_latency_ms = 0.0

    async def connect(self) -> None:
        """Connect to Redis and start flush worker."""
        if self._running:
            return

        try:
            self._redis = await aioredis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            self._running = True
            self._flush_task = asyncio.create_task(self._flush_worker())

            logger.info("Event client connected")

        except Exception as e:
            logger.error(f"Failed to connect event client: {e}")
            raise EventPublishError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis and stop flush worker."""
        if not self._running:
            return

        self._running = False

        # Flush remaining events
        await self._flush_buffer()

        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self._redis:
            await self._redis.close()

        logger.info("Event client disconnected")

    async def publish_trust_event(
        self,
        agent_id: str,
        event_type: EventType,
        severity: EventSeverity,
        impact: float = 0.0,
        confidence: float = 1.0,
        context: Optional[Dict] = None,
    ) -> None:
        """
        Publish a trust event.

        Args:
            agent_id: Agent identifier
            event_type: Type of event
            severity: Event severity
            impact: Trust impact (-1.0 to +1.0)
            confidence: Confidence in the event (0.0 to 1.0)
            context: Additional context data
        """
        event = TrustEvent(
            agent_id=agent_id,
            event_type=event_type,
            severity=severity,
            impact=impact,
            confidence=confidence,
            context=context or {},
            timestamp=datetime.utcnow(),
        )

        await self._publish_event("agion:events:trust", event.model_dump())

    async def publish_user_feedback(
        self,
        execution_id: str,
        user_id: str,
        feedback_type: str,  # "thumbs_up" or "thumbs_down"
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> None:
        """
        Publish user feedback event.

        Args:
            execution_id: Execution ID
            user_id: User who provided feedback
            feedback_type: Type of feedback (thumbs_up/thumbs_down)
            rating: Optional rating (1-5)
            comment: Optional comment
        """
        event = {
            "execution_id": execution_id,
            "user_id": user_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._publish_event("agion:events:feedback", event)

    async def publish_llm_interaction(
        self,
        interaction: LLMInteraction,
    ) -> None:
        """
        Publish LLM interaction for complete audit trail.

        This captures the full prompt, response, token usage, and model details
        for compliance and debugging purposes.

        Args:
            interaction: Complete LLM interaction details
        """
        await self._publish_event(
            "agion:events:llm_interactions",
            interaction.model_dump()
        )

    async def publish_mission_event(
        self,
        mission_id: str,
        event_type: str,
        participant_id: str,
        data: Optional[Dict] = None,
    ) -> None:
        """
        Publish a mission event.

        Args:
            mission_id: Mission identifier
            event_type: Type of event (joined, left, state_updated, etc.)
            participant_id: Participant agent identifier
            data: Additional event data
        """
        event = {
            "mission_id": mission_id,
            "event_type": event_type,
            "participant_id": participant_id,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._publish_event("agion:events:missions", event)

    async def send_mission_message(
        self,
        mission_id: str,
        from_participant: str,
        message_type: str,
        content: Dict,
        to_participant: Optional[str] = None,
    ) -> None:
        """
        Send a message to mission participants.

        Args:
            mission_id: Mission identifier
            from_participant: Sender agent identifier
            message_type: Type of message
            content: Message content
            to_participant: Optional recipient (None = broadcast)
        """
        message = MissionMessage(
            mission_id=mission_id,
            from_participant=from_participant,
            to_participant=to_participant,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow(),
        )

        await self._publish_event(
            f"agion:missions:{mission_id}:messages",
            message.model_dump(),
        )

    async def _publish_event(self, stream: str, data: Dict) -> None:
        """
        Publish an event to a Redis Stream.

        Uses buffering for better performance. Events are flushed periodically
        or when buffer is full.
        """
        if not self._running:
            logger.warning("Event client not running, dropping event")
            return

        # Add to buffer
        self._buffer.append((stream, data))

        # Flush if buffer is full
        if len(self._buffer) >= self.config.event_buffer_size:
            asyncio.create_task(self._flush_buffer())

    async def _flush_worker(self) -> None:
        """Background worker to flush events periodically."""
        try:
            while self._running:
                await asyncio.sleep(self.config.event_flush_interval)
                await self._flush_buffer()

        except asyncio.CancelledError:
            logger.info("Flush worker cancelled")
        except Exception as e:
            logger.error(f"Flush worker error: {e}")

    async def _flush_buffer(self) -> None:
        """Flush buffered events to Redis."""
        if not self._buffer:
            return

        # Get events to publish
        events = []
        while self._buffer:
            events.append(self._buffer.popleft())

        # Publish in batch
        try:
            pipe = self._redis.pipeline()

            for stream, data in events:
                # Convert to string values for Redis
                redis_data = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()}
                pipe.xadd(stream, redis_data)

            await pipe.execute()

            self._published_count += len(events)
            logger.debug(f"Published {len(events)} events")

        except Exception as e:
            logger.error(f"Failed to publish events: {e}")
            self._failed_count += len(events)

            # Put events back in buffer for retry (up to buffer limit)
            for event in events[:self.config.event_buffer_size]:
                self._buffer.append(event)

    def get_metrics(self) -> Dict:
        """Get event publishing metrics."""
        return {
            "published": self._published_count,
            "failed": self._failed_count,
            "buffer_size": len(self._buffer),
            "running": self._running,
        }


class MissionClient:
    """Client for mission coordination."""

    def __init__(self, event_client: EventClient, agent_id: str):
        self.event_client = event_client
        self.agent_id = agent_id
        self._active_missions: Dict[str, MissionParticipant] = {}

    async def join_mission(
        self,
        mission_id: str,
        role: str,
        initial_state: Optional[Dict] = None,
    ) -> None:
        """
        Join a mission.

        Args:
            mission_id: Mission identifier
            role: Role in the mission
            initial_state: Initial state data
        """
        participant = MissionParticipant(
            mission_id=mission_id,
            participant_id=self.agent_id,
            role=role,
            state=initial_state or {},
            joined_at=datetime.utcnow(),
        )

        self._active_missions[mission_id] = participant

        await self.event_client.publish_mission_event(
            mission_id=mission_id,
            event_type="joined",
            participant_id=self.agent_id,
            data={"role": role, "state": initial_state},
        )

    async def leave_mission(self, mission_id: str) -> None:
        """
        Leave a mission.

        Args:
            mission_id: Mission identifier
        """
        if mission_id in self._active_missions:
            del self._active_missions[mission_id]

        await self.event_client.publish_mission_event(
            mission_id=mission_id,
            event_type="left",
            participant_id=self.agent_id,
        )

    async def update_state(
        self,
        mission_id: str,
        state: Dict,
    ) -> None:
        """
        Update mission state.

        Args:
            mission_id: Mission identifier
            state: New state data
        """
        if mission_id in self._active_missions:
            self._active_missions[mission_id].state.update(state)

        await self.event_client.publish_mission_event(
            mission_id=mission_id,
            event_type="state_updated",
            participant_id=self.agent_id,
            data={"state": state},
        )

    async def send_message(
        self,
        mission_id: str,
        message_type: str,
        content: Dict,
        to_participant: Optional[str] = None,
    ) -> None:
        """
        Send a message to mission participants.

        Args:
            mission_id: Mission identifier
            message_type: Type of message
            content: Message content
            to_participant: Optional recipient (None = broadcast)
        """
        await self.event_client.send_mission_message(
            mission_id=mission_id,
            from_participant=self.agent_id,
            message_type=message_type,
            content=content,
            to_participant=to_participant,
        )

    def get_active_missions(self) -> List[str]:
        """Get list of active mission IDs."""
        return list(self._active_missions.keys())
