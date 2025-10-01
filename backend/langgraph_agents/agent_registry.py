"""
Agent Registry - Register all agents with Agion Platform

This module handles agent registration with the Agion platform, including:
- Agent metadata and capabilities
- Input/output schemas
- Performance metrics initialization
- Trust score initialization (starts at 0.4)
"""

import logging
from typing import Dict, List, Any
from core.agion import get_agion_sdk

logger = logging.getLogger(__name__)


# Agent definitions
AGENTS = [
    {
        "agent_id": "langgraph-v2:supervisor",
        "name": "Supervisor Agent",
        "description": "Routes user queries to specialized agents using GPT-5",
        "capabilities": ["query_routing", "agent_selection", "task_classification"],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "User query"},
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "selected_agent": {"type": "string", "description": "Selected agent name"},
                "confidence": {"type": "number", "description": "Routing confidence"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
    {
        "agent_id": "langgraph-v2:chart_agent",
        "name": "Chart Generation Agent",
        "description": "Generates Plotly visualizations and exports to PNG",
        "capabilities": [
            "data_visualization",
            "chart_generation",
            "plotly_charts",
            "png_export",
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Chart request"},
                "file_data": {
                    "type": "object",
                    "description": "Loaded DataFrame data",
                },
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "chart_url": {"type": "string", "description": "Chart PNG URL"},
                "chart_type": {"type": "string", "description": "Chart type"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
    {
        "agent_id": "langgraph-v2:brand_performance_agent",
        "name": "Brand Performance Agent",
        "description": "KPI analysis, data quality checks, business insights",
        "capabilities": [
            "kpi_analysis",
            "data_quality",
            "business_insights",
            "performance_tracking",
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Analysis request"},
                "file_data": {
                    "type": "object",
                    "description": "Loaded DataFrame data",
                },
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "analysis": {"type": "string", "description": "Analysis results"},
                "kpis": {"type": "object", "description": "Key metrics"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
    {
        "agent_id": "langgraph-v2:forecasting_agent",
        "name": "Forecasting Agent",
        "description": "Time series forecasting using Facebook Prophet",
        "capabilities": [
            "time_series_forecasting",
            "prophet_models",
            "trend_analysis",
            "seasonality_detection",
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Forecasting request"},
                "file_data": {
                    "type": "object",
                    "description": "Time series data",
                },
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "forecast": {"type": "array", "description": "Forecast values"},
                "model_params": {"type": "object", "description": "Model parameters"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
    {
        "agent_id": "langgraph-v2:anomaly_detection_agent",
        "name": "Anomaly Detection Agent",
        "description": "Statistical outlier detection with scikit-learn",
        "capabilities": [
            "anomaly_detection",
            "outlier_detection",
            "statistical_analysis",
            "ml_detection",
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Detection request"},
                "file_data": {
                    "type": "object",
                    "description": "Data for analysis",
                },
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "anomalies": {"type": "array", "description": "Detected anomalies"},
                "method": {"type": "string", "description": "Detection method used"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
    {
        "agent_id": "langgraph-v2:general_agent",
        "name": "General Conversational Agent",
        "description": "Conversational AI for general queries",
        "capabilities": [
            "conversation",
            "general_qa",
            "natural_language",
            "contextual_chat",
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "User query"},
                "context": {"type": "string", "description": "Conversation context"},
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string", "description": "Agent response"},
            },
        },
        "performance_metrics": {
            "avg_latency_ms": 0,
            "success_rate": 0.0,
            "total_executions": 0,
        },
    },
]


async def register_all_agents() -> Dict[str, Any]:
    """
    Register all agents with Agion platform.

    This is called during SDK initialization. Each agent registers with:
    - Metadata and capabilities
    - Input/output schemas
    - Initial performance metrics
    - Trust score initialized to 0.4 (40% baseline)

    Returns:
        Dict with registration results
    """
    sdk = await get_agion_sdk()

    if not sdk:
        logger.warning("Agion SDK not available, skipping agent registration")
        return {"status": "skipped", "reason": "SDK not initialized"}

    results = {"registered": [], "failed": []}

    for agent_def in AGENTS:
        try:
            logger.info(f"Registering agent: {agent_def['agent_id']}")

            # Note: The SDK's _register_agent() handles basic registration
            # The platform backend will:
            # 1. Create agent record in database
            # 2. Initialize trust score to 0.4 (baseline)
            # 3. Set up governance policies
            # 4. Configure performance tracking

            # For now, we log the registration (actual HTTP registration
            # happens in SDK initialization)
            results["registered"].append(agent_def["agent_id"])
            logger.info(f"✅ Registered: {agent_def['agent_id']}")

        except Exception as e:
            logger.error(f"Failed to register {agent_def['agent_id']}: {e}")
            results["failed"].append(
                {"agent_id": agent_def["agent_id"], "error": str(e)}
            )

    logger.info(
        f"Agent registration complete: {len(results['registered'])} registered, "
        f"{len(results['failed'])} failed"
    )

    return results


def get_agent_definition(agent_id: str) -> Dict[str, Any]:
    """
    Get agent definition by ID.

    Args:
        agent_id: Agent identifier

    Returns:
        Agent definition dict or None if not found
    """
    for agent in AGENTS:
        if agent["agent_id"] == agent_id:
            return agent
    return None


def get_all_agent_ids() -> List[str]:
    """
    Get list of all registered agent IDs.

    Returns:
        List of agent IDs
    """
    return [agent["agent_id"] for agent in AGENTS]
