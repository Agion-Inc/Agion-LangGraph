# Agent Registry Integration - LangGraph Container

## Overview

This document describes how the LangGraph multi-agent container integrates with the Agion AI Platform's agent registry, governance, and mission management system.

## Architecture

### Agion Platform Services (agion-core namespace)

- **registry-service**: Agent registration, discovery, and metadata management (port 8085, metrics 9090)
- **governance-service**: Policy enforcement, trust scoring, compliance (port 8080, gRPC 50053)
- **coordination-service**: Agent orchestration, task routing (port 8082, gRPC 50051)
- **execution-service**: Mission execution, workflow management (port 8083, gRPC 50052)

### LangGraph Container (agion-langgraph namespace)

- **Container ID**: `langgraph-v2`
- **Agents**: 6 specialized LangGraph agents (supervisor, chart, brand_performance, forecasting, anomaly_detection, general)
- **Framework**: LangGraph 0.6.8 with state graph orchestration
- **Model**: GPT-5 via Requesty AI

## Agent Registration Schema

### Agent Metadata Structure

```json
{
  "agent_id": "langgraph-v2:chart_generator",
  "container_id": "langgraph-v2",
  "name": "Chart Generator Agent",
  "type": "visualization",
  "version": "2.0.0",
  "framework": "langgraph-0.6.8",
  "model": "openai/gpt-5-chat-latest",

  "capabilities": [
    "data_visualization",
    "plotly_charts",
    "time_series_plotting",
    "categorical_analysis",
    "chart_export_png"
  ],

  "input_schema": {
    "required": ["query", "file_data"],
    "properties": {
      "query": {"type": "string", "description": "User visualization request"},
      "file_data": {"type": "object", "description": "DataFrame or parsed data"}
    }
  },

  "output_schema": {
    "properties": {
      "response": {"type": "string", "description": "Chart description"},
      "chart_url": {"type": "string", "format": "uri", "description": "PNG chart URL"},
      "chart_code": {"type": "string", "description": "Generated Plotly code"}
    }
  },

  "performance_metrics": {
    "avg_response_time_ms": 2500,
    "success_rate": 0.97,
    "deterministic": true,
    "temperature": 0.0,
    "seed": 42
  },

  "resource_requirements": {
    "memory_mb": 512,
    "cpu_cores": 0.5,
    "gpu_required": false
  },

  "trust_score": {
    "initial": 0.4,
    "current": 0.4,
    "graduation_threshold": 0.6,
    "total_executions": 0,
    "successful_executions": 0,
    "factors": {
      "code_safety": 0.0,
      "output_reliability": 0.0,
      "performance_consistency": 0.0,
      "user_feedback": 0.0
    },
    "increment_per_success": 0.02,
    "max_score": 1.0
  },

  "governance": {
    "compliance_level": "enterprise",
    "data_handling": "in_memory_only",
    "external_calls": ["requesty_ai_api", "azure_blob_storage"],
    "audit_logging": true,
    "pii_handling": "none"
  },

  "endpoints": {
    "invoke": "http://langgraph-backend-service.agion-langgraph.svc.cluster.local:8000/api/v1/agents/chart",
    "health": "http://langgraph-backend-service.agion-langgraph.svc.cluster.local:8000/health"
  }
}
```

## Six LangGraph Agents Registration

### 1. Supervisor Agent
- **ID**: `langgraph-v2:supervisor`
- **Type**: `routing`
- **Capabilities**: `agent_routing`, `query_analysis`, `task_delegation`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 successful routings)

### 2. Chart Generator Agent
- **ID**: `langgraph-v2:chart_generator`
- **Type**: `visualization`
- **Capabilities**: `data_visualization`, `plotly_charts`, `png_export`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 successful charts)

### 3. Brand Performance Agent
- **ID**: `langgraph-v2:brand_performance`
- **Type**: `analytics`
- **Capabilities**: `kpi_analysis`, `data_quality_checks`, `business_insights`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 successful analyses)

### 4. Forecasting Agent
- **ID**: `langgraph-v2:forecasting`
- **Type**: `prediction`
- **Capabilities**: `time_series_forecasting`, `prophet_models`, `trend_analysis`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 accurate forecasts)

### 5. Anomaly Detection Agent
- **ID**: `langgraph-v2:anomaly_detection`
- **Type**: `security`
- **Capabilities**: `outlier_detection`, `statistical_analysis`, `ml_based_detection`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 successful detections)

### 6. General Chat Agent
- **ID**: `langgraph-v2:general_chat`
- **Type**: `conversational`
- **Capabilities**: `qa`, `general_conversation`, `information_retrieval`
- **Initial Trust Score**: 0.4 (graduates at 0.6 after 10 helpful responses)

## Implementation: Agent Registration Service

### File: `backend/services/agent_registry.py`

```python
"""
Agent Registry Integration Service
Registers LangGraph agents with Agion Platform registry
"""

import httpx
import os
from typing import Dict, Any, List
from datetime import datetime

class AgentRegistryService:
    """Service for registering and managing agents with Agion registry"""

    def __init__(self):
        self.registry_url = os.getenv("AGION_REGISTRY_URL", "http://registry-service.agion-core.svc.cluster.local:8085")
        self.container_id = os.getenv("AGION_AGENT_CONTAINER_ID", "langgraph-v2")
        self.backend_service_url = "http://langgraph-backend-service.agion-langgraph.svc.cluster.local:8000"

    async def register_all_agents(self) -> Dict[str, Any]:
        """Register all 6 LangGraph agents with the platform"""
        agents = [
            self._supervisor_metadata(),
            self._chart_agent_metadata(),
            self._brand_performance_metadata(),
            self._forecasting_metadata(),
            self._anomaly_detection_metadata(),
            self._general_agent_metadata(),
        ]

        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for agent in agents:
                try:
                    response = await client.post(
                        f"{self.registry_url}/api/v1/agents/register",
                        json=agent
                    )
                    response.raise_for_status()
                    results.append({
                        "agent_id": agent["agent_id"],
                        "status": "registered",
                        "response": response.json()
                    })
                except Exception as e:
                    results.append({
                        "agent_id": agent["agent_id"],
                        "status": "failed",
                        "error": str(e)
                    })

        return {
            "container_id": self.container_id,
            "timestamp": datetime.utcnow().isoformat(),
            "agents_registered": len([r for r in results if r["status"] == "registered"]),
            "total_agents": len(agents),
            "details": results
        }

    def _supervisor_metadata(self) -> Dict[str, Any]:
        """Supervisor agent metadata"""
        return {
            "agent_id": f"{self.container_id}:supervisor",
            "container_id": self.container_id,
            "name": "Supervisor Agent",
            "type": "routing",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "agent_routing",
                "query_analysis",
                "task_delegation",
                "intelligent_dispatch"
            ],
            "trust_score": {
                "initial": 0.4,
                "current": 0.4,
                "graduation_threshold": 0.6,
                "total_executions": 0,
                "successful_executions": 0
            },
            "governance": {
                "compliance_level": "enterprise",
                "audit_logging": True
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    def _chart_agent_metadata(self) -> Dict[str, Any]:
        """Chart generator agent metadata"""
        return {
            "agent_id": f"{self.container_id}:chart_generator",
            "container_id": self.container_id,
            "name": "Chart Generator Agent",
            "type": "visualization",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "data_visualization",
                "plotly_charts",
                "time_series_plotting",
                "categorical_analysis",
                "chart_export_png",
                "azure_blob_storage"
            ],
            "performance_metrics": {
                "avg_response_time_ms": 2500,
                "success_rate": 0.97,
                "deterministic": True
            },
            "trust_score": {
                "initial": 0.0,
                "current": 0.0,
                "total_executions": 0,
                "successful_executions": 0,
                "factors": {
                    "code_safety": 0.0,
                    "output_reliability": 0.0,
                    "performance_consistency": 0.0,
                    "user_feedback": 0.0
                }
            },
            "governance": {
                "compliance_level": "enterprise",
                "data_handling": "in_memory_only",
                "external_calls": ["requesty_ai_api", "azure_blob_storage"],
                "audit_logging": True,
                "code_execution": "sandboxed"
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    def _brand_performance_metadata(self) -> Dict[str, Any]:
        """Brand performance agent metadata"""
        return {
            "agent_id": f"{self.container_id}:brand_performance",
            "container_id": self.container_id,
            "name": "Brand Performance Agent",
            "type": "analytics",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "kpi_analysis",
                "data_quality_checks",
                "business_insights",
                "trend_identification",
                "comparative_analysis"
            ],
            "trust_score": {
                "initial": 0.4,
                "current": 0.4,
                "graduation_threshold": 0.6,
                "total_executions": 0,
                "successful_executions": 0
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    def _forecasting_metadata(self) -> Dict[str, Any]:
        """Forecasting agent metadata"""
        return {
            "agent_id": f"{self.container_id}:forecasting",
            "container_id": self.container_id,
            "name": "Forecasting Agent",
            "type": "prediction",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "time_series_forecasting",
                "prophet_models",
                "trend_analysis",
                "seasonality_detection",
                "confidence_intervals"
            ],
            "libraries": ["prophet", "pandas", "numpy"],
            "trust_score": {
                "initial": 0.4,
                "current": 0.4,
                "graduation_threshold": 0.6,
                "total_executions": 0,
                "successful_executions": 0
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    def _anomaly_detection_metadata(self) -> Dict[str, Any]:
        """Anomaly detection agent metadata"""
        return {
            "agent_id": f"{self.container_id}:anomaly_detection",
            "container_id": self.container_id,
            "name": "Anomaly Detection Agent",
            "type": "security",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "outlier_detection",
                "statistical_analysis",
                "ml_based_detection",
                "zscore_analysis",
                "isolation_forest"
            ],
            "libraries": ["scikit-learn", "scipy", "numpy"],
            "trust_score": {
                "initial": 0.4,
                "current": 0.4,
                "graduation_threshold": 0.6,
                "total_executions": 0,
                "successful_executions": 0
            },
            "governance": {
                "compliance_level": "enterprise",
                "security_focused": True
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    def _general_agent_metadata(self) -> Dict[str, Any]:
        """General chat agent metadata"""
        return {
            "agent_id": f"{self.container_id}:general_chat",
            "container_id": self.container_id,
            "name": "General Chat Agent",
            "type": "conversational",
            "version": "2.0.0",
            "framework": "langgraph-0.6.8",
            "model": "openai/gpt-5-chat-latest",
            "capabilities": [
                "qa",
                "general_conversation",
                "information_retrieval",
                "context_understanding"
            ],
            "trust_score": {
                "initial": 0.4,
                "current": 0.4,
                "graduation_threshold": 0.6,
                "total_executions": 0,
                "successful_executions": 0
            },
            "endpoints": {
                "invoke": f"{self.backend_service_url}/api/v1/chat",
                "health": f"{self.backend_service_url}/health"
            }
        }

    async def update_trust_score(self, agent_id: str, new_score: float, factors: Dict[str, float]) -> Dict[str, Any]:
        """Update agent trust score"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                f"{self.registry_url}/api/v1/agents/{agent_id}/trust-score",
                json={
                    "score": new_score,
                    "factors": factors,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            response.raise_for_status()
            return response.json()

    async def report_execution(self, agent_id: str, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Report agent execution metrics to governance service"""
        governance_url = os.getenv("AGION_GOVERNANCE_URL", "http://governance-service.agion-core.svc.cluster.local:8080")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{governance_url}/api/v1/executions",
                json={
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **execution_data
                }
            )
            response.raise_for_status()
            return response.json()

# Singleton instance
agent_registry_service = AgentRegistryService()
```

## Mission Integration

### Mission Schema for LangGraph Agents

```json
{
  "mission_id": "mission-123",
  "title": "Analyze Q4 Sales Performance and Generate Forecast",
  "description": "Analyze sales data, identify trends, and generate 30-day forecast",
  "requester": "user@agion.com",
  "priority": "high",

  "workflow": [
    {
      "step": 1,
      "agent_id": "langgraph-v2:supervisor",
      "action": "route_query",
      "input": {"query": "Analyze Q4 sales and forecast next 30 days"}
    },
    {
      "step": 2,
      "agent_id": "langgraph-v2:brand_performance",
      "action": "analyze_kpis",
      "input": {"file_id": "sales_q4.csv"},
      "depends_on": [1]
    },
    {
      "step": 3,
      "agent_id": "langgraph-v2:forecasting",
      "action": "generate_forecast",
      "input": {"periods": 30},
      "depends_on": [2]
    },
    {
      "step": 4,
      "agent_id": "langgraph-v2:chart_generator",
      "action": "visualize_results",
      "input": {"chart_types": ["line", "bar"]},
      "depends_on": [3]
    }
  ],

  "governance_policies": [
    "data_retention_30_days",
    "audit_all_steps",
    "require_user_approval_for_external_calls"
  ],

  "success_criteria": {
    "all_steps_completed": true,
    "trust_score_minimum": 0.50,  # Moderate trust required
    "execution_time_max_seconds": 30
  },

  "trust_requirements": {
    "supervisor": 0.40,  # Lower requirement for routing
    "brand_performance": 0.50,
    "forecasting": 0.50,
    "chart_generator": 0.50
  }
}
```

## Trust Score Calculation - Earn Through Performance

### Core Principle
**All agents start at 0.4 trust (40%) and graduate at 0.6 trust (60%) after 10 successful executions.**

Trust is earned through performance. Each agent must demonstrate:
1. **Reliability**: Completing tasks successfully without errors
2. **Consistency**: Maintaining stable performance over time
3. **Quality**: Producing outputs that meet user expectations
4. **Safety**: Operating within governance boundaries

### Trust Score Incrementation Logic

```python
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta

class TrustScoreManager:
    """Manages trust score calculation and incrementation for agents"""

    # Trust score configuration
    INITIAL_TRUST = 0.4           # Starting trust score (40%)
    GRADUATION_THRESHOLD = 0.6    # Graduate after reaching 60%

    # Trust score increment strategies
    INCREMENT_STRATEGIES = {
        "conservative": 0.01,   # +1% per success (20 successes to graduate)
        "moderate": 0.02,       # +2% per success (10 successes to graduate)
        "aggressive": 0.04      # +4% per success (5 successes to graduate)
    }

    # Decrement for failures
    DECREMENT_ON_FAILURE = 0.02  # -2% per failure
    DECREMENT_ON_TIMEOUT = 0.01  # -1% per timeout
    DECREMENT_ON_ERROR = 0.03    # -3% per critical error

    def __init__(self, strategy: str = "moderate"):
        self.increment = self.INCREMENT_STRATEGIES.get(strategy, 0.01)

    def calculate_trust_score(
        self,
        agent_id: str,
        execution_history: List[Dict[str, Any]],
        current_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate trust score based on execution history.

        Score increases with:
        - Successful completions
        - Positive user feedback
        - Consistent performance
        - Meeting SLA targets

        Score decreases with:
        - Failures and errors
        - Timeouts
        - Negative user feedback
        - Governance violations
        """

        if not execution_history:
            return {
                "score": 0.0,
                "total_executions": 0,
                "successful_executions": 0,
                "factors": {}
            }

        # Base calculations
        total = len(execution_history)
        successful = len([e for e in execution_history if e.get("status") == "success"])
        failed = len([e for e in execution_history if e.get("status") == "failure"])
        errors = len([e for e in execution_history if e.get("status") == "error"])
        timeouts = len([e for e in execution_history if e.get("status") == "timeout"])

        # Factor 1: Success Rate (40% weight)
        success_rate = successful / total if total > 0 else 0.0

        # Factor 2: Performance Consistency (20% weight)
        response_times = [e.get("response_time_ms", 0) for e in execution_history if e.get("response_time_ms")]
        if len(response_times) > 1:
            avg_time = sum(response_times) / len(response_times)
            std_time = statistics.stdev(response_times)
            # Lower coefficient of variation = higher consistency
            consistency = 1.0 - min(std_time / avg_time if avg_time > 0 else 1.0, 1.0)
        else:
            consistency = 0.0

        # Factor 3: User Feedback (20% weight)
        user_ratings = [e.get("user_rating", 0) for e in execution_history if "user_rating" in e]
        if user_ratings:
            avg_rating = sum(user_ratings) / len(user_ratings) / 5.0  # Normalize to 0-1
        else:
            avg_rating = 0.0  # No ratings = 0 trust from users

        # Factor 4: Code Safety & Compliance (20% weight)
        # Check for governance violations
        violations = len([e for e in execution_history if e.get("governance_violation", False)])
        safety_score = max(0.0, 1.0 - (violations / total if total > 0 else 0))

        # Calculate composite score
        composite_score = (
            success_rate * 0.4 +
            consistency * 0.2 +
            avg_rating * 0.2 +
            safety_score * 0.2
        )

        # Calculate incremental score based on recent performance
        new_score = current_score

        # Increment for successes
        new_score += successful * self.increment

        # Decrement for failures
        new_score -= failed * self.DECREMENT_ON_FAILURE
        new_score -= errors * self.DECREMENT_ON_ERROR
        new_score -= timeouts * self.DECREMENT_ON_TIMEOUT

        # Ensure score stays within bounds [0.0, 1.0]
        new_score = max(0.0, min(1.0, new_score))

        return {
            "score": round(new_score, 3),
            "composite_score": round(composite_score, 3),
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "error_executions": errors,
            "timeout_executions": timeouts,
            "factors": {
                "success_rate": round(success_rate, 3),
                "performance_consistency": round(consistency, 3),
                "user_feedback": round(avg_rating, 3),
                "code_safety": round(safety_score, 3)
            },
            "increments_applied": successful,
            "decrements_applied": failed + errors + timeouts
        }

    async def update_agent_trust_score(
        self,
        agent_id: str,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update trust score after a single execution.

        Args:
            agent_id: Agent identifier
            execution_result: Results from agent execution
                - status: "success" | "failure" | "error" | "timeout"
                - response_time_ms: Response time
                - user_rating: Optional user rating (1-5)
                - governance_violation: Boolean
        """

        # Fetch current trust score from registry
        current_score = await self.get_current_trust_score(agent_id)

        status = execution_result.get("status")
        score_delta = 0.0

        if status == "success":
            score_delta = self.increment
        elif status == "failure":
            score_delta = -self.DECREMENT_ON_FAILURE
        elif status == "error":
            score_delta = -self.DECREMENT_ON_ERROR
        elif status == "timeout":
            score_delta = -self.DECREMENT_ON_TIMEOUT

        # Apply governance penalty
        if execution_result.get("governance_violation", False):
            score_delta -= 0.05  # -5% for violations

        # Apply user feedback bonus/penalty
        if "user_rating" in execution_result:
            rating = execution_result["user_rating"]
            if rating >= 4:
                score_delta += 0.005  # +0.5% bonus for high ratings
            elif rating <= 2:
                score_delta -= 0.005  # -0.5% penalty for low ratings

        new_score = max(0.0, min(1.0, current_score + score_delta))

        # Update registry
        await self.update_registry_trust_score(agent_id, new_score, execution_result)

        return {
            "agent_id": agent_id,
            "previous_score": current_score,
            "new_score": round(new_score, 3),
            "delta": round(score_delta, 3),
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_current_trust_score(self, agent_id: str) -> float:
        """Fetch current trust score from registry"""
        # Implementation: HTTP call to registry service
        pass

    async def update_registry_trust_score(
        self,
        agent_id: str,
        new_score: float,
        execution_context: Dict[str, Any]
    ):
        """Update trust score in registry service"""
        # Implementation: HTTP PUT to registry service
        pass
```

### Trust Score Milestones

| Score Range | Agent Status | Successes Needed | Description |
|-------------|--------------|------------------|-------------|
| 0.40 | **Starting** | 0 | Fresh agent with baseline trust |
| 0.40 - 0.50 | **Learning** | 1-5 | Gaining initial experience |
| 0.50 - 0.60 | **Developing** | 5-10 | Building competence |
| **0.60** | **Graduated** | **10** | **Proven basic reliability** |
| 0.60 - 0.80 | **Trusted** | 10-20 | High confidence, most tasks |
| 0.80 - 1.00 | **Expert** | 20-30 | Elite performance, critical tasks |
| 1.00 | **Perfect** | 30+ | Theoretical maximum (rare) |

### Trust Decay (Optional)

To ensure agents maintain quality over time:

```python
def apply_trust_decay(current_score: float, days_since_last_use: int) -> float:
    """
    Apply trust decay for inactive agents.
    Agents must stay active to maintain trust.
    """
    if days_since_last_use <= 7:
        return current_score  # No decay for active agents

    # Decay rate: -1% per week of inactivity
    decay_rate = 0.01
    weeks_inactive = (days_since_last_use - 7) / 7
    decay_amount = decay_rate * weeks_inactive

    return max(0.0, current_score - decay_amount)
```

## Startup Registration Flow

### File: `backend/main.py` (Updated)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting LangGraph Agent Container...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Register agents with Agion platform
    try:
        from services.agent_registry import agent_registry_service
        registration_result = await agent_registry_service.register_all_agents()

        if registration_result["agents_registered"] == registration_result["total_agents"]:
            print(f"✅ All {registration_result['agents_registered']} agents registered with Agion platform")
        else:
            print(f"⚠️ Partial registration: {registration_result['agents_registered']}/{registration_result['total_agents']}")
            print(f"Details: {registration_result['details']}")
    except Exception as e:
        print(f"❌ Failed to register agents: {str(e)}")
        print("⚠️ Continuing without registry integration")

    print("🎯 LangGraph Agent Container ready!")
    yield

    # Shutdown
    print("🛑 Shutting down LangGraph Agent Container...")
    await close_db()
```

## API Endpoints for Platform Integration

### New Endpoints in `backend/api/agents.py`

```python
from fastapi import APIRouter, HTTPException
from services.agent_registry import agent_registry_service

router = APIRouter()

@router.post("/register-all")
async def register_all_agents():
    """Register all agents with Agion platform"""
    result = await agent_registry_service.register_all_agents()
    return result

@router.put("/agents/{agent_id}/trust-score")
async def update_trust_score(agent_id: str, score: float):
    """Update agent trust score"""
    result = await agent_registry_service.update_trust_score(agent_id, score, {})
    return result

@router.post("/agents/{agent_id}/execution")
async def report_execution(agent_id: str, execution_data: dict):
    """Report agent execution to governance"""
    result = await agent_registry_service.report_execution(agent_id, execution_data)
    return result
```

## Monitoring and Metrics

### Prometheus Metrics Export

Add to backend for Agion monitoring integration:

```python
from prometheus_client import Counter, Histogram, Gauge

# Agent execution metrics
agent_executions = Counter(
    'langgraph_agent_executions_total',
    'Total agent executions',
    ['agent_id', 'status']
)

agent_response_time = Histogram(
    'langgraph_agent_response_seconds',
    'Agent response time',
    ['agent_id']
)

agent_trust_score = Gauge(
    'langgraph_agent_trust_score',
    'Current agent trust score',
    ['agent_id']
)
```

## Next Steps

1. ✅ Update Kubernetes namespace to `agion-langgraph`
2. ✅ Add environment variables for registry integration
3. 🔄 Implement `backend/services/agent_registry.py`
4. 🔄 Update `backend/main.py` with registration on startup
5. 🔄 Add new API endpoints for agent management
6. 🔄 Implement trust score calculation and updates
7. 🔄 Add Prometheus metrics export
8. 🔄 Test registration with Agion platform registry
9. 🔄 Implement mission workflow support
10. 🔄 Document governance policies for each agent
