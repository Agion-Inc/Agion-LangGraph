"""
Governance Wrapper - Wrap LangGraph nodes with governance and metrics reporting

This module provides a decorator to wrap agent nodes with:
- Policy enforcement (pre-execution)
- Metrics reporting (post-execution)
- Trust score updates
- Error tracking
"""

import logging
import uuid
from typing import Callable, Any
from functools import wraps

from langgraph_agents.state import AgentState
from langgraph_agents.metrics_reporter import metrics_reporter
from core.agion import get_agion_sdk

logger = logging.getLogger(__name__)


def governed_node(agent_name: str, action: str):
    """
    Decorator to wrap LangGraph nodes with governance and metrics.

    Args:
        agent_name: Short agent name (e.g., "chart_agent")
        action: Action being performed (e.g., "generate_chart")

    Example:
        @governed_node("chart_agent", "generate_chart")
        async def chart_agent_node(state: AgentState) -> AgentState:
            # Agent logic here
            return state

    The decorator will:
    1. Generate execution ID
    2. Check governance policies (if SDK available)
    3. Report execution start
    4. Execute agent node
    5. Report success/failure/error
    6. Update trust scores
    """

    def decorator(func: Callable[[AgentState], Any]):
        @wraps(func)
        async def wrapper(state: AgentState) -> AgentState:
            # Generate execution ID
            execution_id = str(uuid.uuid4())

            # Get full agent ID
            full_agent_id = f"langgraph-v2:{agent_name}"

            # Get user ID from state (if available)
            user_id = state.get("user_id")

            # Get query for logging
            query = state.get("query", "")

            logger.info(
                f"▶️ Executing {full_agent_id}.{action} "
                f"(execution_id: {execution_id[:8]}...)"
            )

            # Check governance policies
            try:
                sdk = await get_agion_sdk()
                if sdk:
                    # Check policies before execution
                    from agion_sdk.types import UserContext

                    user_context = None
                    if user_id:
                        user_context = UserContext(
                            user_id=user_id,
                            org_id=state.get("org_id"),
                            role=state.get("user_role", "user"),
                            permissions=state.get("user_permissions", []),
                            email=state.get("user_email"),
                        )

                    policy_result = await sdk.check_policy(
                        action=action,
                        user=user_context,
                        resource=agent_name,
                        metadata={
                            "query": query[:200],
                            "execution_id": execution_id,
                        },
                    )

                    if policy_result.decision == "deny":
                        # Policy violation - report and block
                        await metrics_reporter.report_governance_violation(
                            agent_id=full_agent_id,
                            execution_id=execution_id,
                            policy_id=policy_result.matched_policies[0].id
                            if policy_result.matched_policies
                            else "unknown",
                            violation=f"Policy denied action '{action}' for user {user_id}",
                            user_id=user_id,
                        )

                        # Return error state
                        return {
                            **state,
                            "agent_response": "❌ Access denied by governance policy",
                            "error": f"Governance policy denied action: {action}",
                            "confidence": 0.0,
                            "execution_path": state.get("execution_path", [])
                            + [agent_name],
                        }

            except Exception as e:
                logger.warning(f"Policy check failed: {e}, allowing execution")

            # Report execution start
            start_time = await metrics_reporter.report_execution_start(
                agent_id=full_agent_id,
                execution_id=execution_id,
                query=query,
                user_id=user_id,
            )

            try:
                # Add execution_id to state for LLM interaction logging
                state_with_execution_id = {**state, "execution_id": execution_id}

                # Execute agent node
                result_state = await func(state_with_execution_id)

                # Check if execution was successful
                error = result_state.get("error")

                if error:
                    # Execution failed
                    await metrics_reporter.report_execution_failure(
                        agent_id=full_agent_id,
                        execution_id=execution_id,
                        start_time=start_time,
                        error=error,
                        user_id=user_id,
                    )
                else:
                    # Execution succeeded
                    await metrics_reporter.report_execution_success(
                        agent_id=full_agent_id,
                        execution_id=execution_id,
                        start_time=start_time,
                        result=result_state.get("agent_data", {}),
                        user_id=user_id,
                    )

                # Add execution ID to result state
                result_state["execution_id"] = execution_id

                return result_state

            except Exception as e:
                # Execution error (exception)
                logger.error(f"Agent execution error: {e}")

                await metrics_reporter.report_execution_error(
                    agent_id=full_agent_id,
                    execution_id=execution_id,
                    start_time=start_time,
                    error=e,
                    user_id=user_id,
                )

                # Return error state
                return {
                    **state,
                    "agent_response": f"❌ Agent execution failed: {str(e)}",
                    "error": str(e),
                    "execution_id": execution_id,
                    "confidence": 0.0,
                    "execution_path": state.get("execution_path", []) + [agent_name],
                }

        return wrapper

    return decorator
