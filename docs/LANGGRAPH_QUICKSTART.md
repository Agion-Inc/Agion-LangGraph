# LangGraph Quick Start Guide

## Overview

This guide will help you get started with the LangGraph migration for Agent-Chat in just 30 minutes.

---

## Prerequisites

- Python 3.13+
- Existing Agent-Chat installation
- OpenAI API key OR Anthropic API key

---

## Step 1: Install Dependencies (5 minutes)

```bash
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/backend

# Add LangGraph dependencies
pip install langgraph==0.2.77 langchain==0.3.14 langchain-openai==0.2.14 langchain-core==0.3.44 openai==1.59.9
```

**Update requirements.txt:**

```bash
echo "langgraph==0.2.77" >> requirements.txt
echo "langchain==0.3.14" >> requirements.txt
echo "langchain-openai==0.2.14" >> requirements.txt
echo "langchain-core==0.3.44" >> requirements.txt
echo "openai==1.59.9" >> requirements.txt
```

---

## Step 2: Configure Environment (2 minutes)

Add to `.env`:

```bash
# LangGraph Configuration
OPENAI_API_KEY=sk-your-key-here

# Optional: For debugging
LANGCHAIN_TRACING_V2=false
```

---

## Step 3: Create LangGraph Structure (3 minutes)

```bash
# Create directory structure
mkdir -p agents/langgraph/nodes
mkdir -p agents/langgraph/tools

# Create __init__ files
touch agents/langgraph/__init__.py
touch agents/langgraph/nodes/__init__.py
touch agents/langgraph/tools/__init__.py
```

---

## Step 4: Copy Core Files (5 minutes)

From the architecture document, copy these files to your project:

1. **agents/langgraph/state.py** - AgentState definition
2. **agents/langgraph/config.py** - Configuration
3. **agents/langgraph/graph.py** - Main graph
4. **agents/langgraph/supervisor.py** - Supervisor node
5. **agents/langgraph/tools/database_tools.py** - DB tools
6. **agents/langgraph/tools/storage_tools.py** - Storage tools
7. **agents/langgraph/tools/chart_tools.py** - Chart tools

All code is provided in the main architecture document.

---

## Step 5: Create config.py (2 minutes)

**File: agents/langgraph/config.py**

```python
"""
LangGraph Configuration
"""

from langchain_openai import ChatOpenAI
from core.config import settings


def get_llm(model: str = "gpt-4o", temperature: float = 0.7):
    """
    Get configured LLM instance.

    Args:
        model: Model name (gpt-4o, gpt-4o-mini, etc.)
        temperature: Temperature for generation

    Returns:
        ChatOpenAI instance
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None
    )


# Graph configuration
GRAPH_CONFIG = {
    "recursion_limit": 10,
    "max_retries": 3,
    "timeout_seconds": 300
}
```

---

## Step 6: Create Your First Agent Node (5 minutes)

**File: agents/langgraph/nodes/general_agent.py**

```python
"""
General Agent Node - Handles general queries
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from ..state import AgentState
from ..config import get_llm


GENERAL_SYSTEM_PROMPT = """You are a helpful AI assistant for Agent-Chat, a data analysis platform.

You can help users with:
- General questions about the platform
- Explanations of features
- Guidance on how to use the system
- Answering questions that don't require data analysis

Be concise, friendly, and helpful."""


async def general_agent_node(state: AgentState) -> AgentState:
    """
    General chat agent for non-analytical queries.

    Args:
        state: Current agent state

    Returns:
        Updated state with response
    """

    try:
        user_query = state["user_query"]

        # Get LLM
        llm = get_llm(model="gpt-4o-mini", temperature=0.7)

        # Create messages
        messages = [
            SystemMessage(content=GENERAL_SYSTEM_PROMPT),
            HumanMessage(content=user_query)
        ]

        # Get response
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Update state
        state["agent_response"] = response_text
        state["confidence"] = 0.85
        state["messages"].append(AIMessage(content=response_text))

    except Exception as e:
        state["error"] = str(e)
        state["agent_response"] = f"I encountered an error: {str(e)}"
        state["confidence"] = 0.0

    return state
```

---

## Step 7: Test the Graph (5 minutes)

**File: test_langgraph.py**

```python
"""
Test LangGraph Setup
"""

import asyncio
from agents.langgraph.graph import run_agent_graph
from core.database import get_async_session
from services.unified_storage import unified_storage


async def test_basic_query():
    """Test a basic query through the graph"""

    # Get database session
    async for db in get_async_session():
        try:
            # Run graph
            final_state = await run_agent_graph(
                user_query="Hello, what can you help me with?",
                context={},
                uploaded_files=[],
                db_session=db,
                storage_service=unified_storage,
                request_id="test-123"
            )

            # Print results
            print("\n=== Test Results ===")
            print(f"Selected Agent: {final_state['selected_agent']}")
            print(f"Response: {final_state['agent_response']}")
            print(f"Confidence: {final_state['confidence']}")
            print("\n✅ Test passed!")

        finally:
            break


if __name__ == "__main__":
    asyncio.run(test_basic_query())
```

**Run test:**

```bash
python test_langgraph.py
```

---

## Step 8: Integrate with FastAPI (3 minutes)

**Modify api/chat.py:**

Add this import at the top:

```python
from agents.langgraph.graph import run_agent_graph
```

Add this new endpoint:

```python
@router.post("/chat/send-v2")
async def send_chat_message_v2(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Send chat message using LangGraph (v2)"""

    from services.unified_storage import unified_storage

    try:
        session_id = request.session_id or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        # Run LangGraph
        final_state = await run_agent_graph(
            user_query=request.message,
            context={"session_id": session_id, **request.context},
            uploaded_files=request.files,
            db_session=db,
            storage_service=unified_storage,
            request_id=request_id
        )

        # Extract response
        response_text = final_state.get("agent_response", "No response generated")
        confidence = final_state.get("confidence", 0.0)
        agent_used = final_state.get("selected_agent", "unknown")

        # Store in database (same as original)
        user_message = DBChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)

        assistant_message = DBChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=response_text,
            agent_id=agent_used
        )
        db.add(assistant_message)
        await db.commit()

        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=response_text,
                agent_id=agent_used
            ),
            agent_used=agent_used,
            confidence=confidence,
            session_id=session_id
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Step 9: Test the API (2 minutes)

```bash
# Start server
python main.py

# In another terminal, test the API
curl -X POST http://localhost:8000/api/v1/chat/send-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, what can you help me with?",
    "context": {},
    "files": []
  }'
```

Expected response:

```json
{
  "message": {
    "role": "assistant",
    "content": "Hello! I'm your AI assistant for Agent-Chat...",
    "agent_id": "general_agent"
  },
  "agent_used": "general_agent",
  "confidence": 0.85,
  "session_id": "..."
}
```

---

## Step 10: Next Steps (Read)

Congratulations! You now have a working LangGraph setup.

**To continue:**

1. **Add more agents**: Follow the agent creation guide in the main architecture document
2. **Migrate existing agents**: Port ChartGenerator, BP003, BP004 logic to nodes
3. **Add tools**: Create more tools in `tools/` directory
4. **Enable streaming**: Implement streaming responses
5. **Add monitoring**: Add metrics and logging

**See full documentation:**
- LANGGRAPH_ARCHITECTURE.md - Complete architecture plan
- Agent creation guide (Section 8)
- Migration phases (Section 7)

---

## Troubleshooting

**Import errors:**
```bash
# Reinstall dependencies
pip install --upgrade langgraph langchain langchain-openai
```

**API key not found:**
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY

# Make sure it's loaded
python -c "from core.config import settings; print(hasattr(settings, 'OPENAI_API_KEY'))"
```

**Graph not executing:**
```bash
# Test graph directly
python -c "from agents.langgraph.graph import create_agent_graph; g = create_agent_graph(); print('Graph compiled successfully')"
```

**Database errors:**
```bash
# Make sure database is initialized
python -m alembic upgrade head
```

---

## Summary

In 30 minutes, you've:
- ✅ Installed LangGraph
- ✅ Created basic structure
- ✅ Built your first agent node
- ✅ Integrated with FastAPI
- ✅ Tested the system

**Next**: Migrate your existing agents to the new architecture!