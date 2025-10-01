"""
Supervisor Node - Smart routing to specialized agents

The supervisor analyzes user queries and determines which agent should handle them.
Uses GPT-5 for intelligent routing decisions.

Routing Logic:
- Chart/visualization requests → Chart Agent
- Brand performance & KPI analysis → Brand Performance Agent
- Forecasting & predictions → Forecasting Agent
- Anomaly detection & outliers → Anomaly Detection Agent
- General questions → General Agent
"""

import time
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph_agents.state import AgentState, add_execution_step
from langgraph_agents.governance_wrapper import governed_node
from langgraph_agents.metrics_reporter import metrics_reporter
from core.config import settings


@governed_node("supervisor", "route_query")
async def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node that routes queries to appropriate agents.

    Args:
        state: Current agent state with user query

    Returns:
        AgentState: Updated state with selected_agent set
    """
    query = state["query"]
    uploaded_files = state.get("uploaded_files", [])

    # Initialize GPT-5 via Requesty for routing
    llm = ChatOpenAI(
        model="openai/gpt-5-chat-latest",
        api_key=settings.REQUESTY_AI_API_KEY,
        base_url=settings.REQUESTY_AI_API_BASE,
        temperature=0.1,
    )

    # Build routing prompt
    system_prompt = """You are a supervisor routing assistant for an AI analytics platform. Route queries to the most appropriate specialized agent.

Available agents:

1. **chart_generator** - Data visualization and chart creation
   - Triggers: "chart", "graph", "plot", "visualize", "show", "display"
   - Requires: Uploaded data file
   - Creates: PNG charts using Plotly

2. **brand_performance** - Brand/product performance analysis and KPIs
   - Triggers: "performance", "KPI", "growth rate", "market share", "analyze performance", "brand metrics", "data quality"
   - Requires: Uploaded data file with numeric metrics
   - Provides: Growth analysis, market share, performance benchmarking, data quality assessment

3. **forecasting** - Time series forecasting and predictions
   - Triggers: "forecast", "predict", "projection", "future", "trend", "next month", "next year", "what will"
   - Requires: Uploaded data file with time series data
   - Provides: Prophet-based forecasts, trend analysis, confidence intervals

4. **anomaly_detection** - Outlier detection and anomaly analysis
   - Triggers: "anomaly", "outlier", "unusual", "abnormal", "detect issues", "quality control", "fraud"
   - Requires: Uploaded data file with numeric data
   - Provides: Statistical + ML-based anomaly detection (IQR, Z-score, Isolation Forest, LOF)

5. **general_chat** - General conversation and Q&A (fallback)
   - Triggers: General questions, greetings, help requests
   - No file requirements
   - Default agent when no specialized agent fits

**Routing Priority**:
1. If query mentions visualization → chart_generator
2. If query mentions forecasting/prediction → forecasting
3. If query mentions anomalies/outliers → anomaly_detection
4. If query mentions performance/KPIs → brand_performance
5. Otherwise → general_chat

**Important**: Agents requiring files will gracefully handle missing data.

Respond with ONLY the agent name: chart_generator, brand_performance, forecasting, anomaly_detection, or general_chat."""

    user_prompt = f"""User query: "{query}"

Uploaded files: {len(uploaded_files)} file(s)

Which agent should handle this?"""

    # Call GPT-5 for routing
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        llm_start_time = time.time()
        response = await llm.ainvoke(messages)
        llm_latency_ms = (time.time() - llm_start_time) * 1000

        selected_agent = response.content.strip().lower()

        # Log LLM interaction for audit trail
        execution_id = state.get("execution_id")
        if execution_id:
            await metrics_reporter.report_llm_interaction(
                execution_id=execution_id,
                agent_id="langgraph-v2:supervisor",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response.content,
                model="openai/gpt-5-chat-latest",
                provider="requesty",
                temperature=0.1,
                latency_ms=llm_latency_ms,
                user_id=state.get("user_id"),
                finish_reason=getattr(response.response_metadata, "finish_reason", None) if hasattr(response, "response_metadata") else None,
                prompt_tokens=getattr(response.response_metadata, "prompt_tokens", None) if hasattr(response, "response_metadata") else None,
                completion_tokens=getattr(response.response_metadata, "completion_tokens", None) if hasattr(response, "response_metadata") else None,
                total_tokens=getattr(response.response_metadata, "total_tokens", None) if hasattr(response, "response_metadata") else None,
            )

        # Validate agent selection
        valid_agents = ["chart_generator", "brand_performance", "forecasting", "anomaly_detection", "general_chat"]
        if selected_agent not in valid_agents:
            # Default to general chat
            selected_agent = "general_chat"

        # Data-dependent agents will handle missing files gracefully
        # No need to override here

        # Update state
        return {
            **state,
            "selected_agent": selected_agent,
            "execution_path": state.get("execution_path", []) + ["supervisor"],
            "metadata": {
                **state.get("metadata", {}),
                "routing_decision": selected_agent,
            },
        }

    except Exception as e:
        # Error in routing, default to general chat
        return {
            **state,
            "selected_agent": "general_chat",
            "execution_path": state.get("execution_path", []) + ["supervisor"],
            "error": f"Supervisor routing error: {str(e)}",
            "metadata": {
                **state.get("metadata", {}),
                "routing_error": str(e),
            },
        }