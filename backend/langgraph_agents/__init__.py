"""
LangGraph Agents - Agent-Chat Multi-Agent System

This package contains the LangGraph-based agent orchestration system for Agent-Chat.
Agents are implemented as nodes in a state graph with type-safe state management.

Architecture:
- state.py: AgentState definition (type-safe state)
- graph.py: Main graph definition and supervisor
- nodes/: Individual agent implementations
- tools/: Shared tools (database, storage, charts)
- tests/: Comprehensive test suite

Usage:
    from langgraph_agents import create_agent_graph

    graph = create_agent_graph()
    result = await graph.ainvoke({"messages": [{"role": "user", "content": "Hello"}]})
"""

__version__ = "2.0.0"
__author__ = "Agent-Chat Team"

from langgraph_agents.graph import create_agent_graph
from langgraph_agents.state import AgentState

__all__ = ["create_agent_graph", "AgentState"]