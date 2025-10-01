"""Governance decorators for agent functions."""

import functools
import logging
import time
from typing import Any, Callable, Optional
from datetime import datetime

from .types import (
    PolicyContext,
    UserContext,
    ExecutionContext,
    EventType,
    EventSeverity,
)
from .exceptions import PolicyViolationError

logger = logging.getLogger(__name__)


class GovernanceDecorator:
    """
    Decorator for applying governance to agent functions.

    Usage:
        @sdk.governed("agent_name", "action_name")
        async def my_agent_function(state):
            # Your agent logic
            return result
    """

    def __init__(self, sdk: "AgionSDK"):  # type: ignore
        self.sdk = sdk

    def __call__(
        self,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> Callable:
        """
        Create a governance decorator.

        Args:
            agent_id: Agent identifier (defaults to SDK agent_id)
            action: Action being performed (defaults to function name)
            resource: Optional resource being accessed

        Returns:
            Decorated function with governance enforcement
        """

        def decorator(func: Callable) -> Callable:
            # Determine action name
            action_name = action or func.__name__

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                return await self._execute_with_governance(
                    func,
                    agent_id or self.sdk.config.agent_id,
                    action_name,
                    resource,
                    args,
                    kwargs,
                )

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                # For sync functions, we can't use async governance
                # Just log a warning and execute
                logger.warning(
                    f"Governance decorator applied to sync function {func.__name__}. "
                    "Use async functions for full governance support."
                )
                return func(*args, **kwargs)

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    async def _execute_with_governance(
        self,
        func: Callable,
        agent_id: str,
        action: str,
        resource: Optional[str],
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """
        Execute function with governance enforcement.

        1. Check policies before execution
        2. Execute function
        3. Track execution time and result
        4. Publish trust events
        5. Update execution context
        """
        start_time = time.perf_counter()
        execution_id = f"exec-{int(time.time() * 1000)}"

        # Extract user context from kwargs if available
        user: Optional[UserContext] = kwargs.pop("_agion_user", None)

        # Create execution context
        execution = ExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            user=user,
            session_id=kwargs.pop("_agion_session_id", None),
            parent_execution_id=kwargs.pop("_agion_parent_execution_id", None),
            mission_id=kwargs.pop("_agion_mission_id", None),
        )

        try:
            # 1. Check policies
            policy_context = PolicyContext(
                user_id=user.user_id if user else None,
                org_id=user.org_id if user else None,
                role=user.role if user else None,
                permissions=user.permissions if user else [],
                agent_id=agent_id,
                action=action,
                resource=resource,
                metadata=execution.metadata,
            )

            policy_result = self.sdk.policy_engine.evaluate(policy_context, user)

            # Log warnings
            if policy_result.warnings:
                logger.warning(
                    f"Policy warnings for {agent_id}.{action}: {', '.join(policy_result.warnings)}"
                )

            # 2. Execute function
            result = await func(*args, **kwargs)

            # 3. Track execution time
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # 4. Publish success event
            await self.sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_COMPLETED,
                severity=EventSeverity.POSITIVE,
                impact=0.01,  # Small positive impact for successful execution
                confidence=0.95,
                context={
                    "execution_id": execution_id,
                    "action": action,
                    "execution_time_ms": execution_time_ms,
                    "policy_checks": len(policy_result.matched_policies),
                },
            )

            logger.info(
                f"Successfully executed {agent_id}.{action} "
                f"in {execution_time_ms:.2f}ms"
            )

            return result

        except PolicyViolationError as e:
            # Policy violation - publish critical event
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            await self.sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.POLICY_VIOLATION,
                severity=EventSeverity.CRITICAL,
                impact=-0.1,  # Significant negative impact
                confidence=1.0,
                context={
                    "execution_id": execution_id,
                    "action": action,
                    "error": str(e),
                    "policy_id": e.policy_id,
                },
            )

            logger.error(f"Policy violation in {agent_id}.{action}: {e}")
            raise

        except Exception as e:
            # Execution failure - publish negative event
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            await self.sdk.event_client.publish_trust_event(
                agent_id=agent_id,
                event_type=EventType.TASK_FAILED,
                severity=EventSeverity.NEGATIVE,
                impact=-0.05,  # Moderate negative impact
                confidence=0.9,
                context={
                    "execution_id": execution_id,
                    "action": action,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_time_ms": execution_time_ms,
                },
            )

            logger.error(f"Execution failed for {agent_id}.{action}: {e}")
            raise


# Need to import asyncio at the end to avoid circular imports
import asyncio
