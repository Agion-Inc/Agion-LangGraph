"""
LangGraph Main Graph - Multi-agent orchestration for Agent-Chat

This module defines the main state graph with supervisor routing.
The supervisor analyzes user queries and routes to specialized agents.

Architecture:
    User Query → Supervisor → [Specialized Agents] → Response

Agents:
- Chart Agent: Data visualization and chart generation
- Brand Performance Agent: KPI analysis, data quality, business insights
- Forecasting Agent: Time series forecasting with Prophet
- Anomaly Detection Agent: Outlier detection and anomaly analysis
- General Agent: General conversation and Q&A
"""

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic

from langgraph_agents.state import AgentState, add_execution_step, set_error
from langgraph_agents.nodes.supervisor import supervisor_node
from langgraph_agents.nodes.chart_agent import chart_agent_node
from langgraph_agents.nodes.brand_performance_agent import brand_performance_agent_node
from langgraph_agents.nodes.forecasting_agent import forecasting_agent_node
from langgraph_agents.nodes.anomaly_detection_agent import anomaly_detection_agent_node
from langgraph_agents.nodes.general_agent import general_agent_node


def create_agent_graph() -> StateGraph:
    """
    Create the main LangGraph with supervisor routing.

    Returns:
        StateGraph: Compiled graph ready for execution
    """
    # Initialize graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("chart_agent", chart_agent_node)
    graph.add_node("brand_performance_agent", brand_performance_agent_node)
    graph.add_node("forecasting_agent", forecasting_agent_node)
    graph.add_node("anomaly_detection_agent", anomaly_detection_agent_node)
    graph.add_node("general_agent", general_agent_node)

    # Set entry point
    graph.set_entry_point("supervisor")

    # Add conditional edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "chart_agent": "chart_agent",
            "brand_performance_agent": "brand_performance_agent",
            "forecasting_agent": "forecasting_agent",
            "anomaly_detection_agent": "anomaly_detection_agent",
            "general_agent": "general_agent",
            "end": END,
        },
    )

    # Add edges from agents back to END
    graph.add_edge("chart_agent", END)
    graph.add_edge("brand_performance_agent", END)
    graph.add_edge("forecasting_agent", END)
    graph.add_edge("anomaly_detection_agent", END)
    graph.add_edge("general_agent", END)

    # Compile graph
    return graph.compile()


def route_to_agent(state: AgentState) -> Literal["chart_agent", "brand_performance_agent", "forecasting_agent", "anomaly_detection_agent", "general_agent", "end"]:
    """
    Route to appropriate agent based on supervisor's decision.

    Args:
        state: Current agent state

    Returns:
        str: Next node to execute
    """
    selected_agent = state.get("selected_agent")

    if not selected_agent:
        # No agent selected, error occurred
        return "end"

    # Map agent names to node names
    agent_map = {
        "chart_generator": "chart_agent",
        "brand_performance": "brand_performance_agent",
        "forecasting": "forecasting_agent",
        "anomaly_detection": "anomaly_detection_agent",
        "general_chat": "general_agent",
    }

    return agent_map.get(selected_agent, "general_agent")


# Export compiled graph
agent_graph = create_agent_graph()