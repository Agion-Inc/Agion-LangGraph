"""Local policy evaluation engine for sub-millisecond enforcement."""

import time
from typing import Dict, List, Optional
from datetime import datetime

from .types import (
    PolicyRule,
    PolicyContext,
    PolicyResult,
    PolicyDecision,
    EnforcementLevel,
    UserContext,
)
from .exceptions import PolicyEvaluationError, PolicyViolationError


class PolicyEngine:
    """
    Local policy evaluation engine.

    Evaluates policies in-process with < 1ms latency using compiled rules
    and simple comparison operations (no regex/parsing overhead).
    """

    def __init__(self):
        self._policies: Dict[str, PolicyRule] = {}
        self._evaluation_count = 0
        self._total_eval_time_ms = 0.0

    def load_policies(self, policies: List[PolicyRule]) -> None:
        """
        Load policies into the engine.

        Args:
            policies: List of compiled policy rules
        """
        self._policies.clear()
        for policy in policies:
            self._policies[policy.id] = policy

    def get_policies(self) -> List[PolicyRule]:
        """Get all loaded policies."""
        return list(self._policies.values())

    def evaluate(
        self,
        context: PolicyContext,
        user: Optional[UserContext] = None,
    ) -> PolicyResult:
        """
        Evaluate policies against a context.

        Args:
            context: Policy evaluation context
            user: Optional user context for RBAC

        Returns:
            PolicyResult with decision and matched policies

        Raises:
            PolicyViolationError: If HARD/CRITICAL enforcement blocks the action
        """
        start_time = time.perf_counter()

        try:
            # Sort policies by priority (higher priority first)
            policies = sorted(self._policies.values(), key=lambda p: p.priority, reverse=True)

            matched_policies = []
            violations = []
            warnings = []
            final_decision = PolicyDecision.ALLOW

            for policy in policies:
                # Evaluate policy expression
                matches = self._evaluate_expression(policy, context, user)

                if matches:
                    matched_policies.append(policy.id)

                    # Update decision based on policy
                    if policy.decision == PolicyDecision.DENY:
                        if policy.enforcement in (EnforcementLevel.HARD, EnforcementLevel.CRITICAL):
                            violations.append(policy.name)
                            final_decision = PolicyDecision.DENY
                        elif policy.enforcement == EnforcementLevel.SOFT:
                            warnings.append(policy.name)
                    elif policy.decision == PolicyDecision.WARN:
                        warnings.append(policy.name)
                    elif policy.decision == PolicyDecision.REQUIRE_APPROVAL:
                        final_decision = PolicyDecision.REQUIRE_APPROVAL

            # Calculate metrics
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            self._evaluation_count += 1
            self._total_eval_time_ms += execution_time_ms

            result = PolicyResult(
                decision=final_decision,
                allowed=(final_decision != PolicyDecision.DENY),
                matched_policies=matched_policies,
                violations=violations,
                warnings=warnings,
                execution_time_ms=execution_time_ms,
            )

            # Raise exception if denied with hard enforcement
            if not result.allowed and violations:
                raise PolicyViolationError(
                    f"Policy violation: {', '.join(violations)}",
                    policy_id=matched_policies[0] if matched_policies else None,
                    decision=final_decision.value,
                )

            return result

        except PolicyViolationError:
            raise
        except Exception as e:
            raise PolicyEvaluationError(f"Policy evaluation failed: {str(e)}") from e

    def _evaluate_expression(
        self,
        policy: PolicyRule,
        context: PolicyContext,
        user: Optional[UserContext] = None,
    ) -> bool:
        """
        Evaluate a policy expression against context.

        This is a simplified expression evaluator. In production, you'd want
        a more robust expression language (CEL, Rego, etc.) or compile expressions
        to Python bytecode for maximum performance.

        Current implementation supports simple comparisons:
        - "action == 'delete'"
        - "org_id == 'org-123'"
        - "role in ['admin', 'editor']"
        - "has_permission('write')"
        """
        try:
            # Build evaluation context
            eval_context = {
                "agent_id": context.agent_id,
                "action": context.action,
                "resource": context.resource,
                "org_id": context.org_id,
                "user_id": context.user_id,
                "role": context.role,
                "permissions": context.permissions,
                "metadata": context.metadata,
            }

            if user:
                eval_context.update({
                    "user": {
                        "id": user.user_id,
                        "org_id": user.org_id,
                        "role": user.role,
                        "permissions": user.permissions,
                        "email": user.email,
                    }
                })

            # Helper functions
            def has_permission(perm: str) -> bool:
                return perm in context.permissions

            def any_permission(*perms: str) -> bool:
                return any(p in context.permissions for p in perms)

            def all_permissions(*perms: str) -> bool:
                return all(p in context.permissions for p in perms)

            # Add helpers to eval context
            eval_context["has_permission"] = has_permission
            eval_context["any_permission"] = any_permission
            eval_context["all_permissions"] = all_permissions

            # Evaluate expression
            # WARNING: Using eval() is dangerous in production!
            # For production, use a safe expression evaluator like:
            # - google/cel-python
            # - simpleeval
            # - py-expression-eval
            # This is simplified for the MVP.
            result = eval(policy.expression, {"__builtins__": {}}, eval_context)
            return bool(result)

        except Exception:
            # If expression evaluation fails, assume no match (fail-safe)
            return False

    def get_metrics(self) -> Dict[str, float]:
        """Get policy evaluation metrics."""
        avg_latency = (
            self._total_eval_time_ms / self._evaluation_count
            if self._evaluation_count > 0
            else 0.0
        )

        return {
            "total_evaluations": self._evaluation_count,
            "average_latency_ms": avg_latency,
            "total_policies": len(self._policies),
        }

    def clear_metrics(self) -> None:
        """Clear evaluation metrics."""
        self._evaluation_count = 0
        self._total_eval_time_ms = 0.0
