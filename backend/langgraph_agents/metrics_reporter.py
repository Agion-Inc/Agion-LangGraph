"""
Metrics Reporter - Report agent execution metrics to Agion Platform

This module handles reporting agent execution results to the platform for:
- Trust score updates
- Performance tracking
- Error monitoring
- Success rate calculation
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.agion import get_agion_sdk
from agion_sdk.types import EventType, EventSeverity, LLMInteraction

logger = logging.getLogger(__name__)


class MetricsReporter:
    """
    Reports agent execution metrics to Agion platform.

    Trust Score Philosophy:
    - All agents start at 0.4 trust (40% baseline)
    - Graduate at 0.6 (60% proven reliability) after 10 successes
    - +2% per success (moderate strategy)
    - -2% per failure
    - -3% per error
    - +0.5% for user ratings ≥4
    - -5% for governance violations
    """

    @staticmethod
    async def report_execution_start(
        agent_id: str,
        execution_id: str,
        query: str,
        user_id: Optional[str] = None,
    ) -> float:
        """
        Report agent execution start.

        Args:
            agent_id: Full agent ID (e.g., "langgraph-v2:chart_agent")
            execution_id: Unique execution ID
            query: User query
            user_id: Optional user ID

        Returns:
            Start time (for latency calculation)
        """
        start_time = time.time()

        # Note: We don't report execution start as trust events
        # Only completion, failure, or errors affect trust scores
        logger.debug(f"🚀 {agent_id} execution started (id: {execution_id})")

        return start_time

    @staticmethod
    async def report_execution_success(
        agent_id: str,
        execution_id: str,
        start_time: float,
        result: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> None:
        """
        Report successful agent execution.

        Args:
            agent_id: Full agent ID
            execution_id: Unique execution ID
            start_time: Execution start time
            result: Execution result
            user_id: Optional user ID
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Publish success event with +2% trust impact
            await sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_COMPLETED,
                severity=EventSeverity.POSITIVE,
                impact=0.02,  # +2% trust per success
                confidence=1.0,
                context={
                    "execution_id": execution_id,
                    "latency_ms": latency_ms,
                    "user_id": user_id,
                    "result_keys": list(result.keys()) if result else [],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.info(
                f"✅ {agent_id} execution succeeded "
                f"(latency: {latency_ms:.0f}ms, trust impact: +2%)"
            )

        except Exception as e:
            logger.error(f"Failed to report execution success: {e}")

    @staticmethod
    async def report_execution_failure(
        agent_id: str,
        execution_id: str,
        start_time: float,
        error: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Report failed agent execution.

        Args:
            agent_id: Full agent ID
            execution_id: Unique execution ID
            start_time: Execution start time
            error: Error message
            user_id: Optional user ID
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Publish failure event with -2% trust impact
            await sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_FAILED,
                severity=EventSeverity.NEGATIVE,
                impact=-0.02,  # -2% trust per failure
                confidence=1.0,
                context={
                    "execution_id": execution_id,
                    "latency_ms": latency_ms,
                    "error": error[:500],  # Truncate long errors
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.warning(
                f"❌ {agent_id} execution failed "
                f"(latency: {latency_ms:.0f}ms, trust impact: -2%): {error[:100]}"
            )

        except Exception as e:
            logger.error(f"Failed to report execution failure: {e}")

    @staticmethod
    async def report_execution_error(
        agent_id: str,
        execution_id: str,
        start_time: float,
        error: Exception,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Report agent execution error (exception).

        Args:
            agent_id: Full agent ID
            execution_id: Unique execution ID
            start_time: Execution start time
            error: Exception object
            user_id: Optional user ID
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Publish error event with -3% trust impact
            await sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_FAILED,
                severity=EventSeverity.CRITICAL,
                impact=-0.03,  # -3% trust per error
                confidence=1.0,
                context={
                    "execution_id": execution_id,
                    "latency_ms": latency_ms,
                    "error_type": type(error).__name__,
                    "error_message": str(error)[:500],
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.error(
                f"💥 {agent_id} execution error "
                f"(latency: {latency_ms:.0f}ms, trust impact: -3%): {error}"
            )

        except Exception as e:
            logger.error(f"Failed to report execution error: {e}")

    @staticmethod
    async def report_governance_violation(
        agent_id: str,
        execution_id: str,
        policy_id: str,
        violation: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Report governance policy violation.

        Args:
            agent_id: Full agent ID
            execution_id: Unique execution ID
            policy_id: Policy that was violated
            violation: Violation description
            user_id: Optional user ID
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            # Publish governance violation with -5% trust impact
            await sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.POLICY_VIOLATION,
                severity=EventSeverity.CRITICAL,
                impact=-0.05,  # -5% trust per governance violation
                confidence=1.0,
                context={
                    "execution_id": execution_id,
                    "policy_id": policy_id,
                    "violation": violation[:500],
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            logger.critical(
                f"🚨 {agent_id} governance violation "
                f"(policy: {policy_id}, trust impact: -5%): {violation[:100]}"
            )

        except Exception as e:
            logger.error(f"Failed to report governance violation: {e}")

    @staticmethod
    async def report_user_feedback(
        agent_id: str,
        execution_id: str,
        user_id: str,
        rating: int,
        feedback_type: str,
        comment: Optional[str] = None,
    ) -> None:
        """
        Report user feedback.

        Args:
            agent_id: Full agent ID
            execution_id: Unique execution ID
            user_id: User who provided feedback
            rating: Rating (1-5)
            feedback_type: "thumbs_up" or "thumbs_down"
            comment: Optional comment
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            # Publish user feedback event
            await sdk.event_client.publish_user_feedback(
                execution_id=execution_id,
                user_id=user_id,
                feedback_type=feedback_type,
                rating=rating,
                comment=comment,
            )

            # If rating >= 4, also publish positive trust event (+0.5%)
            if rating >= 4:
                await sdk.event_client.publish_trust_event(
                    agent_id=agent_id,
                    event_type=EventType.USER_FEEDBACK,
                    severity=EventSeverity.POSITIVE,
                    impact=0.005,  # +0.5% trust for good ratings
                    confidence=1.0,
                    context={
                        "execution_id": execution_id,
                        "user_id": user_id,
                        "rating": rating,
                        "comment": comment[:200] if comment else None,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                logger.info(
                    f"👍 {agent_id} received positive feedback "
                    f"(rating: {rating}, trust impact: +0.5%)"
                )
            else:
                logger.info(
                    f"👎 {agent_id} received feedback "
                    f"(rating: {rating}, no trust impact)"
                )

        except Exception as e:
            logger.error(f"Failed to report user feedback: {e}")

    @staticmethod
    async def report_llm_interaction(
        execution_id: str,
        agent_id: str,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        model: str,
        provider: str = "requesty",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        seed: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        finish_reason: Optional[str] = None,
        cost_estimate: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Report LLM interaction for audit trail.

        Args:
            execution_id: Agent execution ID
            agent_id: Full agent ID
            system_prompt: System prompt sent to LLM
            user_prompt: User prompt sent to LLM
            response_text: LLM response text
            model: Model name (e.g., "openai/gpt-5-chat-latest")
            provider: Provider name (e.g., "requesty", "openai", "anthropic")
            conversation_history: Previous messages in conversation
            temperature: Model temperature
            max_tokens: Max tokens parameter
            seed: Random seed
            prompt_tokens: Input token count
            completion_tokens: Output token count
            total_tokens: Total token count
            latency_ms: LLM call latency in milliseconds
            user_id: Optional user ID
            finish_reason: Completion finish reason
            cost_estimate: Estimated cost in USD
            metadata: Additional metadata
        """
        try:
            sdk = await get_agion_sdk()
            if not sdk:
                return

            interaction = LLMInteraction(
                execution_id=execution_id,
                agent_id=agent_id,
                interaction_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                conversation_history=conversation_history,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                other_params=metadata or {},
                response_text=response_text,
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms or 0.0,
                user_id=user_id,
                cost_estimate=cost_estimate,
                metadata=metadata or {},
            )

            await sdk.event_client.publish_llm_interaction(interaction)

            logger.debug(
                f"📝 LLM interaction logged for {agent_id} "
                f"(tokens: {total_tokens}, latency: {latency_ms:.0f}ms)"
            )

        except Exception as e:
            logger.error(f"Failed to report LLM interaction: {e}")


# Singleton instance
metrics_reporter = MetricsReporter()
