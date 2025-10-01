"""
Example: LangGraph integration with Agion SDK

This example shows how to build a LangGraph agent with:
- Governance enforcement on each node
- Dynamic prompt/model configuration
- Trust event publishing
- Mission coordination
"""

import asyncio
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agion_sdk import AgionSDK, UserContext


# Define agent state
class AgentState(TypedDict):
    """State for our LangGraph agent."""
    messages: Annotated[list, operator.add]
    user_query: str
    analysis_result: str
    chart_data: dict
    final_response: str


# Initialize SDK
sdk = AgionSDK(
    agent_id="langgraph-v2:chart_generator",
    agent_version="1.0.0",
    gateway_url="http://localhost:8080",
    redis_url="redis://localhost:6379",
)


# Define agent nodes with governance


@sdk.governed("chart_generator", "analyze_query")
async def analyze_query_node(state: AgentState) -> AgentState:
    """
    Analyze user query to determine chart requirements.

    This node is governed - policies are checked before execution.
    """
    # Fetch dynamic prompt from registry
    prompt_config = await sdk.get_prompt(location="chart_analysis")

    # Fetch dynamic model configuration
    model_config = await sdk.get_model(purpose="analysis")

    # Create LLM with dynamic config
    llm = ChatOpenAI(
        model=model_config.model_name,
        temperature=model_config.parameters.get("temperature", 0.7),
        api_key=model_config.credentials.get("api_key"),
    )

    # Build prompt with dynamic template
    messages = [
        SystemMessage(content=prompt_config.content),
        HumanMessage(content=state["user_query"]),
    ]

    # Call LLM
    response = await llm.ainvoke(messages)

    return {
        "messages": [response],
        "analysis_result": response.content,
    }


@sdk.governed("chart_generator", "generate_chart")
async def generate_chart_node(state: AgentState) -> AgentState:
    """
    Generate chart based on analysis.

    This node is governed - policies are checked before execution.
    """
    # Fetch dynamic prompt
    prompt_config = await sdk.get_prompt(location="chart_generation")

    # Fetch model config
    model_config = await sdk.get_model(purpose="chart_generation")

    # Create LLM
    llm = ChatOpenAI(
        model=model_config.model_name,
        temperature=model_config.parameters.get("temperature", 0.3),
        api_key=model_config.credentials.get("api_key"),
    )

    # Build prompt
    messages = [
        SystemMessage(content=prompt_config.content),
        HumanMessage(content=f"Analysis: {state['analysis_result']}"),
    ]

    # Call LLM
    response = await llm.ainvoke(messages)

    return {
        "messages": [response],
        "chart_data": {"type": "bar", "data": []},  # Simplified
    }


@sdk.governed("chart_generator", "format_response")
async def format_response_node(state: AgentState) -> AgentState:
    """
    Format final response for user.

    This node is governed - policies are checked before execution.
    """
    # Fetch dynamic prompt
    prompt_config = await sdk.get_prompt(location="response_formatting")

    # Simple formatting (could use LLM)
    response = f"Analysis: {state['analysis_result']}\n\nChart: {state['chart_data']}"

    return {
        "final_response": response,
    }


# Build LangGraph workflow
def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("analyze", analyze_query_node)
    workflow.add_node("generate", generate_chart_node)
    workflow.add_node("format", format_response_node)

    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_edge("generate", "format")
    workflow.add_edge("format", END)

    return workflow.compile()


# Main execution
async def main():
    """Main execution example."""
    # Initialize SDK
    await sdk.initialize()

    try:
        # Create user context (from JWT in real application)
        user = UserContext(
            user_id="user-123",
            org_id="org-456",
            role="analyst",
            permissions=["read", "write", "execute_agents"],
            email="analyst@example.com",
        )

        # Build graph
        graph = build_graph()

        # Execute workflow
        initial_state = {
            "messages": [],
            "user_query": "Generate a bar chart showing sales by region",
            "analysis_result": "",
            "chart_data": {},
            "final_response": "",
            # Pass user context to all nodes
            "_agion_user": user,
            "_agion_session_id": "session-789",
        }

        print("Executing LangGraph workflow with Agion governance...")
        result = await graph.ainvoke(initial_state)

        print(f"\nFinal Response:\n{result['final_response']}")

        # Report user feedback (from chat UI)
        await sdk.report_user_feedback(
            execution_id="exec-123",
            user_id=user.user_id,
            feedback_type="thumbs_up",
            rating=5,
            comment="Great chart!",
        )

        # Get metrics
        metrics = sdk.get_metrics()
        print(f"\nSDK Metrics:\n{metrics}")

    finally:
        # Disconnect SDK
        await sdk.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
