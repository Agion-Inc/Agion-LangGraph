"""
AgentState - Type-safe state management for Agent-Chat agents

This module defines the state schema that flows through the LangGraph.
All nodes receive and return AgentState, ensuring type safety and consistency.
"""

from typing import List, Dict, Any, Optional, Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from datetime import datetime
import operator


class AgentState(TypedDict):
    """
    State that flows through the LangGraph.

    This state is shared across all agent nodes and contains:
    - Conversation messages
    - Uploaded file information
    - Agent routing decisions
    - Execution metadata
    - Error handling

    The state is immutable - nodes return new state dicts rather than modifying in place.
    """

    # Core conversation
    messages: Annotated[List[BaseMessage], operator.add]  # Append-only message list
    """Conversation history using LangChain message types"""

    # User query context
    query: str
    """Current user query being processed"""

    session_id: str
    """Chat session ID for database persistence"""

    # File handling
    uploaded_files: List[str]
    """List of file IDs that user has uploaded"""

    file_data: Optional[Dict[str, Any]]
    """Loaded file data (DataFrames, parsed content, etc.)"""

    # Agent routing
    selected_agent: Optional[str]
    """Which agent has been selected to handle this query"""

    agent_capabilities: Dict[str, List[str]]
    """Map of agent names to their capabilities"""

    # Execution metadata
    execution_path: Annotated[List[str], operator.add]  # Track which nodes executed
    """Path of nodes that have executed (for debugging)"""

    timestamp: str
    """ISO timestamp of query initiation"""

    # Results and responses
    agent_response: Optional[str]
    """Final response from the selected agent"""

    agent_data: Optional[Dict[str, Any]]
    """Additional data from agent (charts, analysis results, etc.)"""

    confidence: float
    """Agent confidence score (0.0-1.0)"""

    # Error handling
    error: Optional[str]
    """Error message if something went wrong"""

    error_details: Optional[Dict[str, Any]]
    """Detailed error information for debugging"""

    # Metadata
    metadata: Dict[str, Any]
    """Additional metadata (execution time, model used, etc.)"""


def create_initial_state(
    query: str,
    session_id: str,
    uploaded_files: Optional[List[str]] = None,
) -> AgentState:
    """
    Create initial state for a new query.

    Args:
        query: User query string
        session_id: Chat session ID
        uploaded_files: Optional list of uploaded file IDs

    Returns:
        AgentState: Initial state ready for graph execution
    """
    return AgentState(
        messages=[HumanMessage(content=query)],
        query=query,
        session_id=session_id,
        uploaded_files=uploaded_files or [],
        file_data=None,
        selected_agent=None,
        agent_capabilities={},
        execution_path=[],
        timestamp=datetime.utcnow().isoformat(),
        agent_response=None,
        agent_data=None,
        confidence=0.0,
        error=None,
        error_details=None,
        metadata={}
    )


def add_message(state: AgentState, role: Literal["user", "assistant"], content: str) -> AgentState:
    """
    Add a message to the state.

    Args:
        state: Current state
        role: Message role ("user" or "assistant")
        content: Message content

    Returns:
        AgentState: Updated state with new message
    """
    message = HumanMessage(content=content) if role == "user" else AIMessage(content=content)
    return {
        **state,
        "messages": state["messages"] + [message]
    }


def add_execution_step(state: AgentState, step_name: str) -> AgentState:
    """
    Add an execution step to the path (for debugging).

    Args:
        state: Current state
        step_name: Name of the step/node that executed

    Returns:
        AgentState: Updated state with execution step added
    """
    return {
        **state,
        "execution_path": state["execution_path"] + [step_name]
    }


def set_agent_response(
    state: AgentState,
    response: str,
    agent_name: str,
    confidence: float = 1.0,
    data: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    Set the agent response in state.

    Args:
        state: Current state
        response: Agent response text
        agent_name: Name of responding agent
        confidence: Confidence score (0.0-1.0)
        data: Additional data (charts, analysis, etc.)

    Returns:
        AgentState: Updated state with response
    """
    return {
        **state,
        "agent_response": response,
        "selected_agent": agent_name,
        "confidence": confidence,
        "agent_data": data or {},
        "messages": state["messages"] + [AIMessage(content=response)]
    }


def set_error(state: AgentState, error: str, details: Optional[Dict[str, Any]] = None) -> AgentState:
    """
    Set error state.

    Args:
        state: Current state
        error: Error message
        details: Detailed error information

    Returns:
        AgentState: Updated state with error
    """
    return {
        **state,
        "error": error,
        "error_details": details or {}
    }