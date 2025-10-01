# Governance Injection Architecture - First Principles Design

## Core Philosophy

**The LangGraph container should be a "dumb" execution engine.** All governance intelligence lives in the Agion platform's governance service. The container merely:
1. Reports what it's about to do
2. Waits for permission
3. Executes if allowed
4. Reports what it did
5. Receives feedback

This creates a clean separation: **execution logic in container, governance logic in platform.**

## First Principles

### 1. Governance as a Gate, Not a Guard

Instead of embedding governance rules in the LangGraph container, we treat governance as **checkpoints** that must be passed:

```
Agent wants to act → Ask platform "May I?" → Platform decides → Agent acts (or doesn't)
                                                            ↓
                                              User sees platform's decision
```

### 2. Three Governance Checkpoints

#### Checkpoint A: Pre-Execution (Permission)
**"May I execute this action?"**
- Agent describes what it wants to do
- Platform checks policies, trust scores, user permissions
- Platform responds: ALLOW / DENY / REQUIRE_APPROVAL

#### Checkpoint B: Post-Execution (Validation)
**"Did I do this correctly?"**
- Agent reports what it did and the result
- Platform validates output quality, safety, compliance
- Platform responds: ACCEPT / REJECT / FLAG_FOR_REVIEW

#### Checkpoint C: User Feedback (Trust Update)
**"What did the user think?"**
- User provides feedback (like/dislike, rating, comment)
- Platform updates agent trust score
- Platform may trigger retraining, quarantine, or promotion

### 3. Governance is Transparent to Users

Users should see governance in action:
- **Blocked actions**: "This agent (trust: 0.42) cannot access external APIs. Requesting approval..."
- **Approved actions**: "✓ Governance check passed. Generating chart..."
- **Rejected results**: "⚠ Result rejected by governance: Output contains PII. Regenerating..."
- **User feedback**: "Rate this response: 👍 👎" → Updates trust score in real-time

## Architecture Design

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  - Shows governance decisions                                    │
│  - Provides feedback controls (like/dislike, approve/reject)     │
│  - Displays agent trust scores                                   │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────────┐
│              LangGraph Container (agion-langgraph)               │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Governance Middleware (Interceptor Pattern)              │   │
│  │  - Wraps every agent node execution                       │   │
│  │  - Calls platform before/after execution                  │   │
│  │  - Handles governance responses                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                       │
│  ┌────────────────────────┼────────────────────────────────┐   │
│  │  Agent Nodes           │                                  │   │
│  │  - Supervisor          │                                  │   │
│  │  - Chart Generator ────┤                                  │   │
│  │  - Forecasting         │                                  │   │
│  │  - etc.                │                                  │   │
│  └────────────────────────┼────────────────────────────────┘   │
│                           │                                       │
│  ┌────────────────────────↓────────────────────────────────┐   │
│  │  Governance Client Library                               │   │
│  │  - check_permission()                                     │   │
│  │  - validate_result()                                      │   │
│  │  - report_execution()                                     │   │
│  │  - submit_feedback()                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ↓ HTTP/gRPC
┌─────────────────────────────────────────────────────────────────┐
│         Agion Platform (agion-core namespace)                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Governance Service                                       │   │
│  │  - Policy Engine (rules, permissions)                     │   │
│  │  - Trust Score Manager                                    │   │
│  │  - Compliance Checker                                     │   │
│  │  - Audit Logger                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Registry Service                                         │   │
│  │  - Agent metadata                                         │   │
│  │  - Capability definitions                                 │   │
│  │  - Trust scores (current values)                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Mission Service                                          │   │
│  │  - Workflow orchestration                                 │   │
│  │  - Multi-agent coordination                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Code in LangGraph Repository

### 1. Governance Client Library

**File: `backend/core/governance_client.py`**

This is the ONLY governance code needed locally. It's a thin client that talks to the platform.

```python
"""
Governance Client - Interface to Agion Platform Governance
Pure client library with no governance logic - all decisions from platform
"""

import httpx
from typing import Dict, Any, Literal, Optional
from datetime import datetime
import os

GovernanceDecision = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL", "ACCEPT", "REJECT", "FLAG_FOR_REVIEW"]

class GovernanceClient:
    """Client for communicating with Agion platform governance service"""

    def __init__(self):
        self.governance_url = os.getenv(
            "AGION_GOVERNANCE_URL",
            "http://governance-service.agion-core.svc.cluster.local:8080"
        )
        self.container_id = os.getenv("AGION_AGENT_CONTAINER_ID", "langgraph-v2")
        self.timeout = 5.0  # 5 second timeout for governance checks

    async def check_permission(
        self,
        agent_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checkpoint A: Ask platform for permission to execute an action.

        Args:
            agent_id: Full agent identifier (e.g., "langgraph-v2:chart_generator")
            action: What the agent wants to do (e.g., "generate_plotly_chart")
            context: Action context (query, file_data, user_id, etc.)

        Returns:
            {
                "decision": "ALLOW" | "DENY" | "REQUIRE_APPROVAL",
                "reason": "Low trust score" | "Policy violation" | etc,
                "metadata": {...},
                "user_message": "This agent requires approval because..."
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.governance_url}/api/v1/governance/permission",
                    json={
                        "agent_id": agent_id,
                        "container_id": self.container_id,
                        "action": action,
                        "context": context,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                # Fail-safe: if governance is down, deny by default
                return {
                    "decision": "DENY",
                    "reason": "Governance service timeout",
                    "user_message": "Unable to verify governance. Action blocked for safety."
                }
            except Exception as e:
                return {
                    "decision": "DENY",
                    "reason": f"Governance check failed: {str(e)}",
                    "user_message": "Governance verification failed. Action blocked."
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
                "should_retry": bool
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.governance_url}/api/v1/governance/validate",
                    json={
                        "agent_id": agent_id,
                        "container_id": self.container_id,
                        "action": action,
                        "result": result,
                        "context": context,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                # Fail-safe: if validation fails, flag for review
                return {
                    "decision": "FLAG_FOR_REVIEW",
                    "reason": f"Validation check failed: {str(e)}",
                    "user_message": "Unable to validate result. Flagged for review.",
                    "should_retry": False
                }

    async def report_execution(
        self,
        agent_id: str,
        execution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Report execution metrics to platform (for trust score updates, auditing).

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
                "trust_score_updated": bool,
                "new_trust_score": float
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.governance_url}/api/v1/governance/execution",
                    json={
                        "agent_id": agent_id,
                        "container_id": self.container_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        **execution_data
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                # Non-critical: log but don't block
                print(f"Failed to report execution: {str(e)}")
                return {"recorded": False}

    async def submit_user_feedback(
        self,
        agent_id: str,
        execution_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checkpoint C: Submit user feedback to platform.

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
                "trust_score_updated": bool,
                "new_trust_score": float,
                "user_message": "Thank you for your feedback. Agent trust updated."
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.governance_url}/api/v1/governance/feedback",
                    json={
                        "agent_id": agent_id,
                        "container_id": self.container_id,
                        "execution_id": execution_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        **feedback
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Failed to submit feedback: {str(e)}")
                return {"recorded": False}

    async def get_agent_policies(self, agent_id: str) -> Dict[str, Any]:
        """
        Fetch current governance policies for an agent.

        Returns:
            {
                "allowed_actions": [...],
                "forbidden_actions": [...],
                "requires_approval": [...],
                "trust_requirements": {...},
                "rate_limits": {...}
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.governance_url}/api/v1/governance/policies/{agent_id}"
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Failed to fetch policies: {str(e)}")
                return {"allowed_actions": []}


# Singleton instance
governance_client = GovernanceClient()
```

### 2. Governance Middleware (Interceptor Pattern)

**File: `backend/core/governance_middleware.py`**

This wraps every agent node execution with governance checks.

```python
"""
Governance Middleware - Intercepts agent executions for governance checks
Uses decorator pattern to wrap agent nodes
"""

from functools import wraps
from typing import Callable, Any
from datetime import datetime
import time

from langgraph_agents.state import AgentState, set_error
from core.governance_client import governance_client

def with_governance(agent_name: str, action_name: str):
    """
    Decorator that wraps agent nodes with governance checkpoints.

    Usage:
        @with_governance("chart_generator", "generate_chart")
        def chart_agent_node(state: AgentState) -> AgentState:
            # Agent logic here
            pass
    """
    def decorator(agent_func: Callable[[AgentState], AgentState]):
        @wraps(agent_func)
        async def wrapper(state: AgentState) -> AgentState:
            container_id = "langgraph-v2"  # Could be from env
            agent_id = f"{container_id}:{agent_name}"
            execution_id = f"{agent_id}:{int(time.time() * 1000)}"

            # Extract context from state
            context = {
                "query": state.get("query"),
                "session_id": state.get("session_id"),
                "uploaded_files": state.get("uploaded_files", []),
                "user_id": state.get("metadata", {}).get("user_id"),
            }

            # ============================================
            # CHECKPOINT A: Pre-Execution Permission
            # ============================================
            permission = await governance_client.check_permission(
                agent_id=agent_id,
                action=action_name,
                context=context
            )

            # Add governance decision to state for transparency
            state = {
                **state,
                "metadata": {
                    **state.get("metadata", {}),
                    "governance": {
                        "permission_decision": permission["decision"],
                        "permission_reason": permission.get("reason"),
                        "execution_id": execution_id
                    }
                }
            }

            if permission["decision"] == "DENY":
                # Blocked by governance
                return set_error(
                    state,
                    f"Governance blocked action: {permission.get('reason')}",
                    {
                        "governance_decision": permission,
                        "user_message": permission.get("user_message")
                    }
                )

            if permission["decision"] == "REQUIRE_APPROVAL":
                # Requires user approval - pause execution
                return {
                    **state,
                    "agent_response": None,
                    "awaiting_approval": True,
                    "approval_request": permission.get("user_message"),
                    "execution_id": execution_id
                }

            # ============================================
            # EXECUTE AGENT (if allowed)
            # ============================================
            start_time = time.time()
            try:
                # Call the actual agent function
                result_state = await agent_func(state)
                duration_ms = (time.time() - start_time) * 1000
                execution_status = "success"
                error = None
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                execution_status = "error"
                error = str(e)
                result_state = set_error(state, f"Agent execution failed: {str(e)}")

            # ============================================
            # CHECKPOINT B: Post-Execution Validation
            # ============================================
            if execution_status == "success":
                validation = await governance_client.validate_result(
                    agent_id=agent_id,
                    action=action_name,
                    result=result_state.get("agent_response"),
                    context={
                        **context,
                        "duration_ms": duration_ms,
                        "agent_data": result_state.get("agent_data")
                    }
                )

                # Update state with validation decision
                result_state = {
                    **result_state,
                    "metadata": {
                        **result_state.get("metadata", {}),
                        "governance": {
                            **result_state.get("metadata", {}).get("governance", {}),
                            "validation_decision": validation["decision"],
                            "validation_reason": validation.get("reason")
                        }
                    }
                }

                if validation["decision"] == "REJECT":
                    # Result rejected by governance
                    result_state = set_error(
                        result_state,
                        f"Result rejected by governance: {validation.get('reason')}",
                        {
                            "governance_validation": validation,
                            "user_message": validation.get("user_message"),
                            "should_retry": validation.get("should_retry", False)
                        }
                    )
                    execution_status = "rejected"

            # ============================================
            # Report Execution to Platform
            # ============================================
            await governance_client.report_execution(
                agent_id=agent_id,
                execution_data={
                    "execution_id": execution_id,
                    "action": action_name,
                    "status": execution_status,
                    "duration_ms": duration_ms,
                    "governance_permission": permission["decision"],
                    "governance_validation": validation["decision"] if execution_status == "success" else None,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            return result_state

        return wrapper
    return decorator
```

### 3. Apply Middleware to Agent Nodes

**Example: `backend/langgraph_agents/nodes/chart_agent.py`**

```python
from core.governance_middleware import with_governance

@with_governance("chart_generator", "generate_chart")
async def chart_agent_node(state: AgentState) -> AgentState:
    """
    Chart generation agent with governance enforcement.
    Governance middleware handles all permission/validation checks.
    """
    query = state["query"]
    file_data = state.get("file_data")

    # Agent logic (no governance code here!)
    chart_url = generate_plotly_chart(file_data, query)

    return set_agent_response(
        state,
        response=f"Chart generated successfully: {chart_url}",
        agent_name="chart_generator",
        data={"chart_url": chart_url}
    )
```

## User Communication of Governance Actions

### Frontend Integration

**File: `frontend/src/services/governance.ts`**

```typescript
export interface GovernanceStatus {
  permissionDecision: 'ALLOW' | 'DENY' | 'REQUIRE_APPROVAL';
  validationDecision?: 'ACCEPT' | 'REJECT' | 'FLAG_FOR_REVIEW';
  reason?: string;
  userMessage?: string;
  executionId?: string;
  awaitingApproval?: boolean;
}

export interface AgentMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  governance?: GovernanceStatus;
  trustScore?: number;
  feedbackEnabled?: boolean;
  executionId?: string;
}
```

### UI Components for Governance Transparency

**1. Governance Status Badge**

```tsx
// frontend/src/components/GovernanceBadge.tsx
import { ShieldCheckIcon, ShieldExclamationIcon } from '@heroicons/react/24/outline';

interface GovernanceBadgeProps {
  status: GovernanceStatus;
  trustScore?: number;
}

export function GovernanceBadge({ status, trustScore }: GovernanceBadgeProps) {
  if (status.permissionDecision === 'DENY') {
    return (
      <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
        <ShieldExclamationIcon className="w-5 h-5 text-red-600" />
        <div>
          <p className="text-sm font-medium text-red-900">Action Blocked</p>
          <p className="text-xs text-red-700">{status.userMessage}</p>
        </div>
      </div>
    );
  }

  if (status.validationDecision === 'REJECT') {
    return (
      <div className="flex items-center gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg">
        <ShieldExclamationIcon className="w-5 h-5 text-orange-600" />
        <div>
          <p className="text-sm font-medium text-orange-900">Result Rejected</p>
          <p className="text-xs text-orange-700">{status.userMessage}</p>
        </div>
      </div>
    );
  }

  if (status.permissionDecision === 'ALLOW') {
    return (
      <div className="flex items-center gap-2 px-2 py-1 bg-green-50 border border-green-200 rounded text-xs">
        <ShieldCheckIcon className="w-4 h-4 text-green-600" />
        <span className="text-green-900">
          Governance ✓ {trustScore && `(Trust: ${(trustScore * 100).toFixed(0)}%)`}
        </span>
      </div>
    );
  }

  return null;
}
```

**2. Approval Request Dialog**

```tsx
// frontend/src/components/ApprovalRequest.tsx
import { useState } from 'react';

interface ApprovalRequestProps {
  message: string;
  executionId: string;
  onApprove: () => void;
  onReject: () => void;
}

export function ApprovalRequest({ message, executionId, onApprove, onReject }: ApprovalRequestProps) {
  const [loading, setLoading] = useState(false);

  return (
    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
      <h3 className="text-sm font-semibold text-yellow-900 mb-2">
        🔐 Approval Required
      </h3>
      <p className="text-sm text-yellow-800 mb-4">{message}</p>
      <div className="flex gap-2">
        <button
          onClick={async () => {
            setLoading(true);
            await onApprove();
            setLoading(false);
          }}
          disabled={loading}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Approve
        </button>
        <button
          onClick={async () => {
            setLoading(true);
            await onReject();
            setLoading(false);
          }}
          disabled={loading}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
```

**3. Feedback Controls**

```tsx
// frontend/src/components/MessageFeedback.tsx
import { HandThumbUpIcon, HandThumbDownIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';

interface MessageFeedbackProps {
  executionId: string;
  agentId: string;
  onFeedback: (rating: 'like' | 'dislike') => Promise<void>;
}

export function MessageFeedback({ executionId, agentId, onFeedback }: MessageFeedbackProps) {
  const [selected, setSelected] = useState<'like' | 'dislike' | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFeedback = async (rating: 'like' | 'dislike') => {
    setLoading(true);
    setSelected(rating);
    await onFeedback(rating);
    setLoading(false);
  };

  return (
    <div className="flex items-center gap-2 mt-2">
      <span className="text-xs text-gray-500">Rate this response:</span>
      <button
        onClick={() => handleFeedback('like')}
        disabled={loading || selected !== null}
        className={`p-1 rounded hover:bg-gray-100 ${selected === 'like' ? 'text-green-600' : 'text-gray-400'}`}
      >
        <HandThumbUpIcon className="w-4 h-4" />
      </button>
      <button
        onClick={() => handleFeedback('dislike')}
        disabled={loading || selected !== null}
        className={`p-1 rounded hover:bg-gray-100 ${selected === 'dislike' ? 'text-red-600' : 'text-gray-400'}`}
      >
        <HandThumbDownIcon className="w-4 h-4" />
      </button>
      {selected && (
        <span className="text-xs text-gray-600 ml-2">
          Thank you! Trust score updated.
        </span>
      )}
    </div>
  );
}
```

**4. Chat Message with Governance**

```tsx
// frontend/src/components/ChatMessage.tsx
import { GovernanceBadge } from './GovernanceBadge';
import { MessageFeedback } from './MessageFeedback';
import { ApprovalRequest } from './ApprovalRequest';

interface ChatMessageProps {
  message: AgentMessage;
  onApprove?: () => void;
  onReject?: () => void;
  onFeedback?: (rating: 'like' | 'dislike') => Promise<void>;
}

export function ChatMessage({ message, onApprove, onReject, onFeedback }: ChatMessageProps) {
  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className="max-w-3xl">
        {/* Governance Status */}
        {message.governance && (
          <GovernanceBadge
            status={message.governance}
            trustScore={message.trustScore}
          />
        )}

        {/* Approval Request */}
        {message.governance?.awaitingApproval && onApprove && onReject && (
          <ApprovalRequest
            message={message.governance.userMessage || 'Approval required'}
            executionId={message.executionId!}
            onApprove={onApprove}
            onReject={onReject}
          />
        )}

        {/* Message Content */}
        <div className="p-4 rounded-lg bg-white border">
          <p>{message.content}</p>
        </div>

        {/* Feedback Controls */}
        {message.feedbackEnabled && message.executionId && onFeedback && (
          <MessageFeedback
            executionId={message.executionId}
            agentId={message.governance?.agentId || 'unknown'}
            onFeedback={onFeedback}
          />
        )}
      </div>
    </div>
  );
}
```

## Trust Score Starting Point: 0.4

All agents start at **0.4 trust (40%)**, requiring **10 successful executions** to reach **0.6 (graduated)**.

### Trust Score Calculation Updated

```python
# Trust score increments
INITIAL_TRUST = 0.4
GRADUATION_THRESHOLD = 0.6
INCREMENT_PER_SUCCESS = 0.02  # 2% per success = 10 successes to graduate
```

### Trust Score Milestones (Updated)

| Score | Status | Executions Needed | Description |
|-------|--------|-------------------|-------------|
| 0.40 | **Starting** | 0 | Fresh agent, baseline trust |
| 0.50 | **Learning** | 5 | Gaining experience |
| 0.60 | **Graduated** | 10 | Proven basic competence |
| 0.70 | **Trusted** | 15 | High confidence |
| 0.80 | **Expert** | 20 | Very reliable |
| 0.90 | **Master** | 25 | Elite performance |
| 1.00 | **Perfect** | 30 | Theoretical maximum |

## Summary: What Goes in This Repository

### Minimal Governance Code (Thin Client)

1. **`backend/core/governance_client.py`**: Platform API client (check permission, validate, report, feedback)
2. **`backend/core/governance_middleware.py`**: Decorator to wrap agent nodes with governance
3. **`frontend/src/services/governance.ts`**: Frontend governance types and API calls
4. **`frontend/src/components/GovernanceBadge.tsx`**: Show governance decisions to users
5. **`frontend/src/components/ApprovalRequest.tsx`**: Handle approval workflows
6. **`frontend/src/components/MessageFeedback.tsx`**: User feedback controls

### What DOESN'T Go Here

- ❌ Policy rules (lives in platform governance service)
- ❌ Trust score calculation (lives in platform)
- ❌ Compliance checking (lives in platform)
- ❌ Audit logging (lives in platform)

### What the Platform Provides

The governance service in `agion-core` namespace provides:
- **Policy engine**: Rules about what agents can/cannot do
- **Trust manager**: Calculates and updates trust scores
- **Compliance checker**: Validates outputs for PII, safety, etc.
- **Audit logger**: Records all governance decisions
- **Approval workflows**: Manages human-in-the-loop approvals

## Result

**Clean separation of concerns:**
- LangGraph container = Execution engine (dumb)
- Platform governance = Decision engine (smart)
- User interface = Transparency layer (shows what's happening)

Users see governance in action, agents execute only when allowed, and all intelligence centralizes in the platform.
