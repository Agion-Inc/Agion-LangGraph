"""
Tests for AgentState and state management functions
"""

import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from langgraph_agents.state import (
    create_initial_state,
    add_message,
    add_execution_step,
    set_agent_response,
    set_error,
)


def test_create_initial_state():
    """Test creating initial state."""
    state = create_initial_state(
        query="Hello world",
        session_id="test-123",
        uploaded_files=["file-1", "file-2"],
    )

    assert state["query"] == "Hello world"
    assert state["session_id"] == "test-123"
    assert state["uploaded_files"] == ["file-1", "file-2"]
    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], HumanMessage)
    assert state["messages"][0].content == "Hello world"
    assert state["selected_agent"] is None
    assert state["confidence"] == 0.0
    assert state["error"] is None


def test_create_initial_state_no_files():
    """Test creating initial state without files."""
    state = create_initial_state(
        query="Test query",
        session_id="test-456",
    )

    assert state["uploaded_files"] == []


def test_add_message_user():
    """Test adding user message to state."""
    initial_state = create_initial_state("Hello", "test-123")

    updated_state = add_message(initial_state, "user", "How are you?")

    assert len(updated_state["messages"]) == 2
    assert isinstance(updated_state["messages"][1], HumanMessage)
    assert updated_state["messages"][1].content == "How are you?"


def test_add_message_assistant():
    """Test adding assistant message to state."""
    initial_state = create_initial_state("Hello", "test-123")

    updated_state = add_message(initial_state, "assistant", "I'm doing well!")

    assert len(updated_state["messages"]) == 2
    assert isinstance(updated_state["messages"][1], AIMessage)
    assert updated_state["messages"][1].content == "I'm doing well!"


def test_add_execution_step():
    """Test adding execution step to state."""
    initial_state = create_initial_state("Test", "test-123")

    updated_state = add_execution_step(initial_state, "supervisor")
    assert updated_state["execution_path"] == ["supervisor"]

    updated_state = add_execution_step(updated_state, "chart_agent")
    assert updated_state["execution_path"] == ["supervisor", "chart_agent"]


def test_set_agent_response():
    """Test setting agent response in state."""
    initial_state = create_initial_state("Create chart", "test-123")

    updated_state = set_agent_response(
        initial_state,
        response="Here's your chart!",
        agent_name="chart_generator",
        confidence=0.95,
        data={"chart_html": "<div>Chart</div>"},
    )

    assert updated_state["agent_response"] == "Here's your chart!"
    assert updated_state["selected_agent"] == "chart_generator"
    assert updated_state["confidence"] == 0.95
    assert updated_state["agent_data"]["chart_html"] == "<div>Chart</div>"
    assert len(updated_state["messages"]) == 2
    assert isinstance(updated_state["messages"][1], AIMessage)


def test_set_error():
    """Test setting error in state."""
    initial_state = create_initial_state("Test", "test-123")

    updated_state = set_error(
        initial_state,
        error="Something went wrong",
        details={"traceback": "Error traceback here"},
    )

    assert updated_state["error"] == "Something went wrong"
    assert updated_state["error_details"]["traceback"] == "Error traceback here"


def test_state_immutability():
    """Test that state updates don't mutate original state."""
    initial_state = create_initial_state("Test", "test-123")
    original_message_count = len(initial_state["messages"])

    updated_state = add_message(initial_state, "user", "Another message")

    # Original state should be unchanged
    assert len(initial_state["messages"]) == original_message_count
    # Updated state should have new message
    assert len(updated_state["messages"]) == original_message_count + 1