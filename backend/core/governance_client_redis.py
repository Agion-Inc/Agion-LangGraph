"""
Governance Client - Redis Streams Implementation
Ultra-fast governance communication (<5ms) using Redis Streams

This will eventually move to agion-sdk package for reuse across all agent containers.
"""

import asyncio
import redis.asyncio as redis
import json
import uuid
import time
from typing import Dict, Any, Literal, Optional
from datetime import datetime
import os

GovernanceDecision = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL", "ACCEPT", "REJECT", "FLAG_FOR_REVIEW"]


class GovernanceClientRedis:
    """
    Fast governance client using Redis Streams.

    Performance: <5ms for permission/validation checks

    Architecture:
    - Agent sends request to governance:requests stream
    - Governance service processes and responds to governance:responses:{container_id} stream
    - Agent blocks on XREAD with correlation ID matching
    - Non-blocking execution reports and feedback submissions
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis-simple.agion-data.svc.cluster.local:6379")
        self.container_id = os.getenv("AGION_AGENT_CONTAINER_ID", "langgraph-v2")

        # Stream names
        self.request_stream = "governance:requests"
        self.response_stream = f"governance:responses:{self.container_id}"
        self.execution_stream = "executions:reports"
        self.feedback_stream = "feedback:submissions"

        # Timeouts
        self.governance_timeout_ms = int(os.getenv("GOVERNANCE_TIMEOUT_MS", "5000"))  # 5 seconds
        self.max_retry_attempts = 2

        # Redis client (lazy initialization)
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_keepalive=True
            )
        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID for request/response matching"""
        return f"{self.container_id}:{uuid.uuid4().hex[:12]}:{int(time.time() * 1000)}"

    async def check_permission(
        self,
        agent_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checkpoint A: Ask platform for permission to execute an action.

        Performance: <5ms typical, 5s timeout

        Args:
            agent_id: Full agent identifier (e.g., "langgraph-v2:chart_generator")
            action: What the agent wants to do (e.g., "generate_plotly_chart")
            context: Action context (query, file_data, user_id, etc.)

        Returns:
            {
                "decision": "ALLOW" | "DENY" | "REQUIRE_APPROVAL",
                "reason": "Low trust score" | "Policy violation" | etc,
                "metadata": {...},
                "user_message": "This agent requires approval because...",
                "latency_ms": 3.2
            }
        """
        correlation_id = self._generate_correlation_id()
        start_time = time.time()

        try:
            r = await self._get_redis()

            # Build request payload
            request = {
                "type": "permission_check",
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "container_id": self.container_id,
                "action": action,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to request stream (non-blocking, <1ms)
            await r.xadd(
                self.request_stream,
                {"payload": json.dumps(request)},
                maxlen=10000  # Keep last 10k requests for debugging
            )

            # Wait for response with correlation ID matching
            response = await self._wait_for_response(correlation_id, timeout_ms=self.governance_timeout_ms)

            latency_ms = (time.time() - start_time) * 1000

            if response:
                response["latency_ms"] = round(latency_ms, 2)
                return response
            else:
                # Timeout: fail-safe to DENY
                return {
                    "decision": "DENY",
                    "reason": "Governance timeout",
                    "user_message": "Unable to verify governance. Action blocked for safety.",
                    "latency_ms": round(latency_ms, 2)
                }

        except redis.ConnectionError as e:
            # Redis unavailable: fail-safe to DENY
            return {
                "decision": "DENY",
                "reason": f"Governance unavailable: {str(e)}",
                "user_message": "Governance service unavailable. Action blocked for safety.",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            return {
                "decision": "DENY",
                "reason": f"Governance check failed: {str(e)}",
                "user_message": "Governance verification failed. Action blocked.",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

    async def validate_result(
        self,
        agent_id: str,
        action: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checkpoint B: Ask platform to validate the result of an action.

        Performance: <5ms typical, 5s timeout

        Args:
            agent_id: Full agent identifier
            action: What the agent did
            result: The output produced
            context: Execution context

        Returns:
            {
                "decision": "ACCEPT" | "REJECT" | "FLAG_FOR_REVIEW",
                "reason": "Contains PII" | "Invalid format" | etc,
                "user_message": "Result rejected because...",
                "should_retry": bool,
                "latency_ms": 2.8
            }
        """
        correlation_id = self._generate_correlation_id()
        start_time = time.time()

        try:
            r = await self._get_redis()

            # Build validation request
            request = {
                "type": "result_validation",
                "correlation_id": correlation_id,
                "agent_id": agent_id,
                "container_id": self.container_id,
                "action": action,
                "result": result,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to request stream
            await r.xadd(
                self.request_stream,
                {"payload": json.dumps(request)},
                maxlen=10000
            )

            # Wait for response
            response = await self._wait_for_response(correlation_id, timeout_ms=self.governance_timeout_ms)

            latency_ms = (time.time() - start_time) * 1000

            if response:
                response["latency_ms"] = round(latency_ms, 2)
                return response
            else:
                # Timeout: fail-safe to FLAG_FOR_REVIEW
                return {
                    "decision": "FLAG_FOR_REVIEW",
                    "reason": "Validation timeout",
                    "user_message": "Unable to validate result. Flagged for review.",
                    "should_retry": False,
                    "latency_ms": round(latency_ms, 2)
                }

        except Exception as e:
            return {
                "decision": "FLAG_FOR_REVIEW",
                "reason": f"Validation check failed: {str(e)}",
                "user_message": "Unable to validate result. Flagged for review.",
                "should_retry": False,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

    async def _wait_for_response(self, correlation_id: str, timeout_ms: int) -> Optional[Dict[str, Any]]:
        """
        Wait for governance response using XREAD with blocking.

        Uses Redis XREAD with BLOCK parameter for efficient waiting.
        Polls every 100ms to check for matching correlation ID.

        Args:
            correlation_id: Unique ID to match request with response
            timeout_ms: Maximum time to wait

        Returns:
            Response dict or None if timeout
        """
        r = await self._get_redis()

        # Create consumer group if not exists (idempotent)
        try:
            await r.xgroup_create(
                self.response_stream,
                self.container_id,
                id='0',
                mkstream=True
            )
        except redis.ResponseError:
            # Group already exists, continue
            pass

        start_time = time.time()
        last_id = '>'  # Read only new messages

        while (time.time() - start_time) * 1000 < timeout_ms:
            remaining_ms = timeout_ms - int((time.time() - start_time) * 1000)
            if remaining_ms <= 0:
                break

            # XREADGROUP with blocking (efficient, no CPU spinning)
            try:
                messages = await r.xreadgroup(
                    groupname=self.container_id,
                    consumername=f"consumer-{correlation_id}",
                    streams={self.response_stream: last_id},
                    count=10,
                    block=min(100, remaining_ms)  # Block up to 100ms
                )

                if messages:
                    for stream, entries in messages:
                        for message_id, data in entries:
                            payload = json.loads(data.get("payload", "{}"))

                            # Check if this response matches our correlation ID
                            if payload.get("correlation_id") == correlation_id:
                                # ACK the message
                                await r.xack(self.response_stream, self.container_id, message_id)
                                return payload

                            # ACK unmatched messages (probably from another request)
                            await r.xack(self.response_stream, self.container_id, message_id)

            except redis.RedisError as e:
                print(f"Redis error waiting for response: {e}")
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Unexpected error waiting for response: {e}")
                await asyncio.sleep(0.1)

        # Timeout
        return None

    async def report_execution(
        self,
        agent_id: str,
        execution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Report execution metrics to platform (non-blocking, fire-and-forget).

        Performance: <1ms (no waiting for response)

        Args:
            agent_id: Full agent identifier
            execution_data: Execution details
                - status: "success" | "failure" | "error"
                - duration_ms: Execution time
                - action: What was executed
                - governance_decision: Permission decision that was made
                - validation_decision: Validation decision

        Returns:
            {
                "recorded": bool,
                "stream_id": str
            }
        """
        try:
            r = await self._get_redis()

            report = {
                "agent_id": agent_id,
                "container_id": self.container_id,
                "timestamp": datetime.utcnow().isoformat(),
                **execution_data
            }

            # Fire and forget (no response needed)
            stream_id = await r.xadd(
                self.execution_stream,
                {"payload": json.dumps(report)},
                maxlen=50000  # Keep last 50k execution reports
            )

            return {
                "recorded": True,
                "stream_id": stream_id
            }

        except Exception as e:
            print(f"Failed to report execution: {str(e)}")
            return {"recorded": False, "error": str(e)}

    async def submit_user_feedback(
        self,
        agent_id: str,
        execution_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checkpoint C: Submit user feedback to platform (non-blocking).

        Performance: <1ms (no waiting for response)

        Args:
            agent_id: Full agent identifier
            execution_id: Unique execution ID
            feedback: User feedback
                - rating: 1-5 stars
                - sentiment: "positive" | "negative" | "neutral"
                - comment: Optional text
                - action: "like" | "dislike" | "approve" | "reject"

        Returns:
            {
                "recorded": bool,
                "stream_id": str
            }
        """
        try:
            r = await self._get_redis()

            feedback_data = {
                "agent_id": agent_id,
                "container_id": self.container_id,
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat(),
                **feedback
            }

            # Fire and forget
            stream_id = await r.xadd(
                self.feedback_stream,
                {"payload": json.dumps(feedback_data)},
                maxlen=50000
            )

            return {
                "recorded": True,
                "stream_id": stream_id
            }

        except Exception as e:
            print(f"Failed to submit feedback: {str(e)}")
            return {"recorded": False, "error": str(e)}

    async def get_agent_trust_score(self, agent_id: str) -> float:
        """
        Get current trust score from Redis cache (ultra-fast, <1ms).

        Trust scores are cached in Redis and updated by governance service
        after each execution report.

        Args:
            agent_id: Full agent identifier

        Returns:
            float: Trust score (0.0-1.0)
        """
        try:
            r = await self._get_redis()
            score = await r.get(f"agent:{agent_id}:trust_score")
            return float(score) if score else 0.4  # Default starting trust
        except Exception as e:
            print(f"Failed to get trust score: {str(e)}")
            return 0.4

    async def get_agent_policies(self, agent_id: str) -> Dict[str, Any]:
        """
        Fetch current governance policies for an agent from Redis cache (<1ms).

        Policies are cached and updated by governance service when rules change.

        Returns:
            {
                "allowed_actions": [...],
                "forbidden_actions": [...],
                "requires_approval": [...],
                "trust_requirements": {...},
                "rate_limits": {...}
            }
        """
        try:
            r = await self._get_redis()
            policies = await r.get(f"agent:{agent_id}:policies")
            if policies:
                return json.loads(policies)
            else:
                # Default policies
                return {
                    "allowed_actions": [],
                    "forbidden_actions": [],
                    "requires_approval": [],
                    "trust_requirements": {},
                    "rate_limits": {}
                }
        except Exception as e:
            print(f"Failed to get policies: {str(e)}")
            return {}


# Singleton instance
governance_client = GovernanceClientRedis()


# Context manager for clean shutdown
class GovernanceClientContext:
    """Context manager for governance client lifecycle"""

    async def __aenter__(self):
        return governance_client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await governance_client.close()
