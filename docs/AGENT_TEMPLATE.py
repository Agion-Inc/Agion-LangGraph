"""
Agent Template for Agent-Chat LangGraph
Copy this template to create new agents quickly
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from ..state import AgentState
from ..config import get_llm
from ..tools.database_tools import get_uploaded_file
from ..tools.storage_tools import load_file_data


# ============================================================================
# CONFIGURATION - Customize these for your agent
# ============================================================================

AGENT_NAME = "my_agent"  # Change this to your agent name (snake_case)
AGENT_DESCRIPTION = "Describe what your agent does"
AGENT_KEYWORDS = ["keyword1", "keyword2", "keyword3"]  # For routing

SYSTEM_PROMPT = """You are a specialized AI agent for [PURPOSE].

Your responsibilities:
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

Guidelines:
- [Guideline 1]
- [Guideline 2]
"""


# ============================================================================
# AGENT NODE FUNCTION - Main implementation
# ============================================================================

async def my_agent_node(state: AgentState) -> AgentState:
    """
    [Agent Name] - [Brief description]

    This agent handles: [list what it handles]

    Args:
        state: Current agent state containing:
            - user_query: User's question
            - context: Additional context
            - uploaded_files: List of file IDs
            - db_session: Database session
            - storage_service: Storage service
            - messages: Conversation history

    Returns:
        Updated AgentState with:
            - agent_response: Generated response
            - confidence: Confidence score (0.0-1.0)
            - intermediate_results: Any intermediate data
            - messages: Updated conversation
    """

    try:
        # ====================================================================
        # STEP 1: Extract inputs from state
        # ====================================================================
        user_query = state["user_query"]
        context = state["context"]
        uploaded_files = state["uploaded_files"]
        db_session = state["db_session"]
        storage_service = state["storage_service"]

        print(f"[{AGENT_NAME}] Processing query: {user_query[:100]}...")

        # ====================================================================
        # STEP 2: Load required data (if needed)
        # ====================================================================
        file_data = None
        if uploaded_files:
            # Load file data if files are provided
            file_data = await load_file_data(
                file_ids=uploaded_files,
                db_session=db_session,
                storage_service=storage_service
            )
            print(f"[{AGENT_NAME}] Loaded {len(file_data)} files")

        # ====================================================================
        # STEP 3: Perform agent-specific processing
        # ====================================================================

        # Option A: Use LLM for generation
        llm = get_llm(model="gpt-4o-mini", temperature=0.7)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_query)
        ]

        # Add file context if available
        if file_data:
            context_msg = "Available data:\n"
            for file_id, df in file_data.items():
                context_msg += f"- File {file_id}: {len(df)} rows, {len(df.columns)} columns\n"
                context_msg += f"  Columns: {', '.join(df.columns[:5])}\n"
            messages.insert(1, SystemMessage(content=context_msg))

        # Get LLM response
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Option B: Custom processing without LLM
        # result = await your_custom_function(user_query, file_data)
        # response_text = format_response(result)

        # ====================================================================
        # STEP 4: Store intermediate results (optional)
        # ====================================================================
        state["intermediate_results"][AGENT_NAME] = {
            "processed_files": len(file_data) if file_data else 0,
            "query_type": "custom",
            # Add any other useful data
        }

        # ====================================================================
        # STEP 5: Update state with response
        # ====================================================================
        state["agent_response"] = response_text
        state["confidence"] = 0.90  # Adjust based on your confidence
        state["messages"].append(AIMessage(content=response_text))

        print(f"[{AGENT_NAME}] Response generated successfully")

    except Exception as e:
        # ====================================================================
        # ERROR HANDLING
        # ====================================================================
        print(f"[{AGENT_NAME}] Error: {str(e)}")

        state["error"] = str(e)
        state["agent_response"] = f"I encountered an error while processing: {str(e)}"
        state["confidence"] = 0.0
        state["messages"].append(AIMessage(content=state["agent_response"]))

    return state


# ============================================================================
# HELPER FUNCTIONS (optional)
# ============================================================================

def format_response(data: dict) -> str:
    """Format data into readable response"""
    # Implement your formatting logic
    return f"Result: {data}"


async def custom_processing(query: str, data: dict) -> dict:
    """Perform custom processing logic"""
    # Implement your processing logic
    return {"processed": True}


# ============================================================================
# REGISTRATION INSTRUCTIONS
# ============================================================================

"""
To register this agent:

1. Add to graph.py:

    from .nodes.my_agent import my_agent_node

    workflow.add_node("my_agent", my_agent_node)
    workflow.add_edge("my_agent", END)

2. Update supervisor.py routing:

    if any(kw in query_lower for kw in ["keyword1", "keyword2"]):
        next_agent = "my_agent"

3. Update conditional edges in graph.py:

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "my_agent": "my_agent",
            # ... other agents
        }
    )

4. Test:

    final_state = await run_agent_graph(
        user_query="keyword1 test",
        context={},
        uploaded_files=[],
        db_session=db,
        storage_service=storage,
        request_id="test"
    )

    assert final_state["selected_agent"] == "my_agent"
"""


# ============================================================================
# TESTING TEMPLATE
# ============================================================================

"""
Add to tests/test_agents.py:

@pytest.mark.asyncio
async def test_my_agent(db_session, storage_service):
    '''Test my_agent node'''

    state = create_initial_state(
        user_query="keyword1 test query",
        context={},
        uploaded_files=[],
        db_session=db_session,
        storage_service=storage_service,
        request_id="test-123"
    )

    # Run node
    result = await my_agent_node(state)

    # Assertions
    assert result["agent_response"] is not None
    assert result["confidence"] > 0.5
    assert "error" not in result or result["error"] is None
    print(f"Response: {result['agent_response']}")
"""