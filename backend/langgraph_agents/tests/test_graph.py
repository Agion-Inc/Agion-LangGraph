"""
Tests for LangGraph graph execution and routing
"""

import pytest
from unittest.mock import AsyncMock, patch

from langgraph_agents.graph import create_agent_graph, route_to_agent
from langgraph_agents.state import create_initial_state


def test_create_agent_graph():
    """Test creating agent graph."""
    graph = create_agent_graph()

    assert graph is not None
    # Graph should be compiled and ready to run


def test_route_to_agent_chart():
    """Test routing to chart agent."""
    state = create_initial_state("Create chart", "test-123")
    state["selected_agent"] = "chart_generator"

    next_node = route_to_agent(state)

    assert next_node == "chart_agent"


def test_route_to_agent_general():
    """Test routing to general agent."""
    state = create_initial_state("Hello", "test-123")
    state["selected_agent"] = "general_chat"

    next_node = route_to_agent(state)

    assert next_node == "general_agent"


def test_route_to_agent_no_selection():
    """Test routing when no agent selected (error case)."""
    state = create_initial_state("Test", "test-123")
    # Don't set selected_agent

    next_node = route_to_agent(state)

    assert next_node == "end"


def test_route_to_agent_invalid_agent():
    """Test routing with invalid agent name."""
    state = create_initial_state("Test", "test-123")
    state["selected_agent"] = "invalid_agent"

    next_node = route_to_agent(state)

    # Should default to general agent
    assert next_node == "general_agent"


@pytest.mark.asyncio
async def test_graph_execution_with_mocked_nodes():
    """Test full graph execution with mocked nodes."""
    # Mock the supervisor to select general agent
    async def mock_supervisor(state):
        return {
            **state,
            "selected_agent": "general_chat",
            "execution_path": state.get("execution_path", []) + ["supervisor"],
        }

    # Mock the general agent
    async def mock_general_agent(state):
        return {
            **state,
            "agent_response": "Hello! I'm the general agent.",
            "confidence": 1.0,
            "execution_path": state.get("execution_path", []) + ["general_agent"],
        }

    with patch("langgraph_agents.nodes.supervisor.supervisor_node", mock_supervisor):
        with patch("langgraph_agents.nodes.general_agent.general_agent_node", mock_general_agent):
            graph = create_agent_graph()

            initial_state = create_initial_state("Hello", "test-123")

            # Execute graph
            result = await graph.ainvoke(initial_state)

            assert result["agent_response"] == "Hello! I'm the general agent."
            assert result["selected_agent"] == "general_chat"
            assert "supervisor" in result["execution_path"]
            assert "general_agent" in result["execution_path"]