# Agent-Chat LangGraph Architecture Plan

## Executive Summary

This document provides a comprehensive plan to restructure Agent-Chat as a proper LangGraph-based application, replacing the custom agent orchestration system while preserving all existing infrastructure (PostgreSQL, Azure Blob Storage, FastAPI, React frontend).

**Current Status**: Custom agent orchestration with BaseAgent, AgentRegistry, and AgentOrchestrator
**Target**: LangGraph supervisor pattern with proper state management and tool integration
**Timeline**: 4-phase migration (estimate: 2-3 days per phase)
**Risk Level**: Low (incremental migration, backward compatible)

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Target LangGraph Architecture](#target-langgraph-architecture)
3. [Directory Structure](#directory-structure)
4. [Core LangGraph Components](#core-langgraph-components)
5. [Agent Migration Strategy](#agent-migration-strategy)
6. [Integration Layer](#integration-layer)
7. [Migration Phases](#migration-phases)
8. [Agent Creation Guide](#agent-creation-guide)
9. [Testing Strategy](#testing-strategy)
10. [Performance Considerations](#performance-considerations)

---

## 1. Current Architecture Analysis

### 1.1 What Works Well (Keep These)

**Infrastructure Layer:**
- **PostgreSQL Database**: SQLAlchemy models for sessions, messages, files
- **Azure Blob Storage**: Unified storage service with local/cloud switching
- **FastAPI Backend**: RESTful API endpoints at `/api/v1/`
- **React Frontend**: Working chat UI with file upload
- **Service Layer**: `unified_storage.py`, `file_storage.py`, `azure_blob_storage.py`

**Database Models (preserve):**
```python
# models.py
- User
- ChatSession
- ChatMessage
- UploadedFile
- WorksheetData
- DataQuery
- AgentExecution
```

**API Endpoints (preserve):**
```python
# api/
- chat.py: /chat/send, /chat/sessions, /chat/multi-agent
- files.py: /files/upload, /files/list, /files/{file_id}
- health.py: /health, /health/detailed
- charts.py: /charts/{chart_id}
```

### 1.2 What to Replace (Custom Agent System)

**Current Agent Architecture (remove):**
```python
# agents/base.py
class BaseAgent(ABC):
    - execute()
    - validate_input()
    - process()
    - AgentRequest/AgentResponse models

# agents/registry.py
class AgentRegistry:
    - discover_agents()
    - invoke_best_agent()
    - orchestrate_multi_agent()

# agents/orchestrator.py
class AgentOrchestrator:
    - execute_with_streaming()
    - AgentPool coordination
```

**Issues with Current System:**
1. No standard state management
2. Manual agent routing and coordination
3. No built-in memory or context management
4. Limited composability
5. Hard to add new agents (requires base class inheritance)
6. No graph-based workflow support

---

## 2. Target LangGraph Architecture

### 2.1 Architecture Principles

**LangGraph Supervisor Pattern:**
```
User Query → Supervisor Node → Route to Agent Node → Process → Return to Supervisor → Output
                  ↓
            Agent Selection
                  ↓
        [Chart Agent | Data Agent | Anomaly Agent | General Agent]
```

**State Management:**
- Centralized `AgentState` with type safety
- Messages history
- File attachments
- Database session injection
- Storage service injection

**Tool Integration:**
- Database queries as tools
- File operations as tools
- Chart generation as tools
- Azure storage as tools

### 2.2 LangGraph Components

```python
# Core Components
1. StateGraph - Main workflow graph
2. AgentState - Typed state object
3. Supervisor Node - Routes to specialized agents
4. Agent Nodes - Specialized processing (chart, data, anomaly)
5. Tools - Reusable functions (database, storage, charts)
6. Checkpointer - State persistence (optional)
```

---

## 3. Directory Structure

### 3.1 New Directory Layout

```
backend/
├── agents/
│   ├── langgraph/                    # NEW - LangGraph implementation
│   │   ├── __init__.py
│   │   ├── graph.py                  # Main graph definition
│   │   ├── state.py                  # AgentState definition
│   │   ├── supervisor.py             # Supervisor node
│   │   ├── tools/                    # Shared tools
│   │   │   ├── __init__.py
│   │   │   ├── database_tools.py    # DB query tools
│   │   │   ├── storage_tools.py     # File storage tools
│   │   │   ├── chart_tools.py       # Chart generation tools
│   │   │   └── analysis_tools.py    # Data analysis tools
│   │   ├── nodes/                   # Agent nodes
│   │   │   ├── __init__.py
│   │   │   ├── chart_agent.py       # Chart generation node
│   │   │   ├── data_agent.py        # Data analysis node
│   │   │   ├── anomaly_agent.py     # Anomaly detection node
│   │   │   └── general_agent.py     # General chat node
│   │   ├── config.py                # LangGraph configuration
│   │   └── utils.py                 # Helper functions
│   │
│   ├── bp003/                        # Existing (migrate to nodes/)
│   ├── bp004/                        # Existing (migrate to nodes/)
│   ├── base.py                       # DEPRECATED (keep for reference)
│   ├── registry.py                   # DEPRECATED (replaced by graph)
│   └── orchestrator.py               # DEPRECATED (replaced by supervisor)
│
├── api/
│   ├── chat.py                       # MODIFY - use LangGraph
│   ├── files.py                      # KEEP AS-IS
│   ├── charts.py                     # KEEP AS-IS
│   └── health.py                     # KEEP AS-IS
│
├── services/
│   ├── unified_storage.py            # KEEP AS-IS
│   ├── file_storage.py               # KEEP AS-IS
│   └── azure_blob_storage.py         # KEEP AS-IS
│
├── models.py                          # KEEP AS-IS
├── core/
│   ├── config.py                      # KEEP AS-IS
│   └── database.py                    # KEEP AS-IS
│
└── main.py                            # MODIFY - register graph
```

### 3.2 File Purpose

**Core Files:**
- `langgraph/graph.py`: Main entry point, creates and compiles the graph
- `langgraph/state.py`: AgentState TypedDict with all state fields
- `langgraph/supervisor.py`: Routing logic for selecting agents
- `langgraph/config.py`: Configuration for LLM models, settings

**Tools Directory:**
- Reusable functions that agents can call
- Injected with database sessions and storage services
- Type-safe with proper error handling

**Nodes Directory:**
- Individual agent implementations
- Each node is a function: `(state: AgentState) -> AgentState`
- Can use tools and call LLMs

---

## 4. Core LangGraph Components

### 4.1 Agent State Definition

**File: `agents/langgraph/state.py`**

```python
"""
LangGraph State Definition for Agent-Chat
Type-safe state management for agent workflows
"""

from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from operator import add
from sqlalchemy.ext.asyncio import AsyncSession


class AgentState(TypedDict):
    """
    Centralized state for all agent operations.

    This state is passed through the entire graph and modified by each node.
    """

    # Messages & History
    messages: Annotated[Sequence[BaseMessage], add]
    """Chat messages with operator for appending"""

    # User Input
    user_query: str
    """Original user query"""

    context: Dict[str, Any]
    """Additional context from request"""

    # File Management
    uploaded_files: List[str]
    """List of file IDs from database"""

    file_contents: Optional[Dict[str, Any]]
    """Loaded file data (DataFrames, etc.)"""

    # Routing & Control
    next_agent: Optional[str]
    """Which agent to route to next"""

    selected_agent: Optional[str]
    """Current agent handling the request"""

    # Results & Output
    agent_response: Optional[str]
    """Final response to user"""

    intermediate_results: Dict[str, Any]
    """Results from intermediate agents"""

    confidence: float
    """Confidence score of the response"""

    # Services (injected)
    db_session: Optional[AsyncSession]
    """Database session for queries"""

    storage_service: Optional[Any]
    """Storage service instance"""

    # Metadata
    request_id: str
    """Unique request identifier"""

    execution_metadata: Dict[str, Any]
    """Execution timing, agent stats, etc."""

    error: Optional[str]
    """Error message if something failed"""


def create_initial_state(
    user_query: str,
    context: Dict[str, Any],
    uploaded_files: List[str],
    db_session: AsyncSession,
    storage_service: Any,
    request_id: str
) -> AgentState:
    """
    Create initial state for a new request.

    Args:
        user_query: User's natural language query
        context: Additional context (session_id, user preferences, etc.)
        uploaded_files: List of file IDs to process
        db_session: Active database session
        storage_service: Storage service instance
        request_id: Unique request ID

    Returns:
        Initialized AgentState
    """
    from langchain_core.messages import HumanMessage

    return AgentState(
        messages=[HumanMessage(content=user_query)],
        user_query=user_query,
        context=context,
        uploaded_files=uploaded_files,
        file_contents=None,
        next_agent=None,
        selected_agent=None,
        agent_response=None,
        intermediate_results={},
        confidence=0.0,
        db_session=db_session,
        storage_service=storage_service,
        request_id=request_id,
        execution_metadata={
            "start_time": None,
            "end_time": None,
            "agents_invoked": []
        },
        error=None
    )
```

### 4.2 Main Graph Definition

**File: `agents/langgraph/graph.py`**

```python
"""
LangGraph Main Graph for Agent-Chat
Supervisor pattern with specialized agent nodes
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from .state import AgentState, create_initial_state
from .supervisor import supervisor_node
from .nodes.chart_agent import chart_agent_node
from .nodes.data_agent import data_agent_node
from .nodes.anomaly_agent import anomaly_agent_node
from .nodes.general_agent import general_agent_node


def create_agent_graph() -> StateGraph:
    """
    Create the main LangGraph workflow.

    Graph Structure:
        START → Supervisor → [Chart | Data | Anomaly | General] → END

    Returns:
        Compiled StateGraph
    """

    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("chart_agent", chart_agent_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("anomaly_agent", anomaly_agent_node)
    workflow.add_node("general_agent", general_agent_node)

    # Define routing logic
    def route_from_supervisor(state: AgentState) -> Literal["chart_agent", "data_agent", "anomaly_agent", "general_agent", "__end__"]:
        """Route based on supervisor's decision"""
        next_agent = state.get("next_agent")

        if next_agent == "chart_agent":
            return "chart_agent"
        elif next_agent == "data_agent":
            return "data_agent"
        elif next_agent == "anomaly_agent":
            return "anomaly_agent"
        elif next_agent == "general_agent":
            return "general_agent"
        else:
            # No agent selected, end
            return "__end__"

    # Add edges
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "chart_agent": "chart_agent",
            "data_agent": "data_agent",
            "anomaly_agent": "anomaly_agent",
            "general_agent": "general_agent",
            "__end__": END
        }
    )

    # All agents return to END
    workflow.add_edge("chart_agent", END)
    workflow.add_edge("data_agent", END)
    workflow.add_edge("anomaly_agent", END)
    workflow.add_edge("general_agent", END)

    # Compile graph
    return workflow.compile()


# Global compiled graph
compiled_graph = create_agent_graph()


async def run_agent_graph(
    user_query: str,
    context: dict,
    uploaded_files: list,
    db_session,
    storage_service,
    request_id: str
) -> AgentState:
    """
    Execute the agent graph with given inputs.

    Args:
        user_query: User's question
        context: Additional context
        uploaded_files: File IDs
        db_session: Database session
        storage_service: Storage service
        request_id: Unique request ID

    Returns:
        Final AgentState after execution
    """

    # Create initial state
    initial_state = create_initial_state(
        user_query=user_query,
        context=context,
        uploaded_files=uploaded_files,
        db_session=db_session,
        storage_service=storage_service,
        request_id=request_id
    )

    # Run graph
    config = RunnableConfig(recursion_limit=10)
    final_state = await compiled_graph.ainvoke(initial_state, config)

    return final_state
```

### 4.3 Supervisor Node

**File: `agents/langgraph/supervisor.py`**

```python
"""
Supervisor Node - Routes to Specialized Agents
Uses LLM to analyze query and select best agent
"""

from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from .state import AgentState
from .config import get_llm


SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor agent that routes user queries to specialized agents.

Available Agents:
1. **chart_agent**: Creates visualizations, charts, graphs from data
   - Keywords: chart, graph, plot, visualize, show, display

2. **data_agent**: Analyzes data, calculates metrics, performs analysis
   - Keywords: analyze, calculate, metrics, statistics, trends

3. **anomaly_agent**: Detects anomalies, outliers, unusual patterns
   - Keywords: anomaly, outlier, unusual, detect, alert

4. **general_agent**: Handles general questions and conversations
   - Keywords: help, explain, what, how, general queries

Based on the user query, select the MOST APPROPRIATE agent.
Respond with ONLY the agent name (e.g., "chart_agent").
"""


async def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node that routes to appropriate agent.

    Args:
        state: Current agent state

    Returns:
        Updated state with next_agent set
    """

    user_query = state["user_query"]

    # Simple keyword-based routing (fast)
    query_lower = user_query.lower()

    if any(kw in query_lower for kw in ["chart", "graph", "plot", "visualize", "show"]):
        next_agent = "chart_agent"
    elif any(kw in query_lower for kw in ["anomaly", "outlier", "unusual", "detect"]):
        next_agent = "anomaly_agent"
    elif any(kw in query_lower for kw in ["analyze", "calculate", "metrics", "statistics"]):
        next_agent = "data_agent"
    else:
        next_agent = "general_agent"

    # Optional: Use LLM for more sophisticated routing
    # llm = get_llm()
    # response = await llm.ainvoke([
    #     SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
    #     HumanMessage(content=user_query)
    # ])
    # next_agent = response.content.strip()

    state["next_agent"] = next_agent
    state["selected_agent"] = next_agent
    state["execution_metadata"]["agents_invoked"].append(next_agent)

    return state
```

### 4.4 Example Agent Node

**File: `agents/langgraph/nodes/chart_agent.py`**

```python
"""
Chart Agent Node - Generates Charts from Data
"""

import pandas as pd
from langchain_core.messages import AIMessage
from ..state import AgentState
from ..tools.chart_tools import create_chart_from_data
from ..tools.storage_tools import load_file_data


async def chart_agent_node(state: AgentState) -> AgentState:
    """
    Chart generation agent.

    Loads data from uploaded files and creates visualizations.

    Args:
        state: Current agent state

    Returns:
        Updated state with chart and response
    """

    try:
        user_query = state["user_query"]
        uploaded_files = state["uploaded_files"]
        storage_service = state["storage_service"]

        # Load data if not already loaded
        if not state.get("file_contents") and uploaded_files:
            file_data = await load_file_data(
                file_ids=uploaded_files,
                db_session=state["db_session"],
                storage_service=storage_service
            )
            state["file_contents"] = file_data

        # Generate chart
        if state.get("file_contents"):
            chart_result = await create_chart_from_data(
                data=state["file_contents"],
                query=user_query,
                request_id=state["request_id"]
            )

            # Format response
            response_text = f"""
**Chart Generated Successfully**

{chart_result['description']}

**Chart:** ![Chart]({chart_result['chart_url']})

**Insights:**
{chr(10).join(f"- {insight}" for insight in chart_result.get('insights', []))}
"""

            state["agent_response"] = response_text
            state["intermediate_results"]["chart"] = chart_result
            state["confidence"] = 0.95

        else:
            state["agent_response"] = "No data files found. Please upload a file first."
            state["confidence"] = 0.5

        # Add AI message to conversation
        state["messages"].append(AIMessage(content=state["agent_response"]))

    except Exception as e:
        state["error"] = str(e)
        state["agent_response"] = f"Chart generation failed: {str(e)}"
        state["confidence"] = 0.0

    return state
```

### 4.5 Tools Definition

**File: `agents/langgraph/tools/database_tools.py`**

```python
"""
Database Tools for LangGraph Agents
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import UploadedFile, ChatSession, ChatMessage


async def get_uploaded_file(
    file_id: str,
    db_session: AsyncSession
) -> Optional[UploadedFile]:
    """Get uploaded file by ID"""
    result = await db_session.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    return result.scalar_one_or_none()


async def list_session_files(
    session_id: str,
    db_session: AsyncSession
) -> List[UploadedFile]:
    """List all files for a session"""
    # Implementation depends on your file-session relationship
    result = await db_session.execute(
        select(UploadedFile).order_by(UploadedFile.created_at.desc())
    )
    return result.scalars().all()


async def store_agent_execution(
    agent_id: str,
    request_id: str,
    status: str,
    execution_time: float,
    input_data: Dict,
    output_data: Dict,
    db_session: AsyncSession
) -> None:
    """Store agent execution record"""
    from models import AgentExecution
    import uuid

    execution = AgentExecution(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        request_id=request_id,
        status=status,
        execution_time=execution_time,
        input_data=input_data,
        output_data=output_data
    )
    db_session.add(execution)
    await db_session.flush()
```

**File: `agents/langgraph/tools/storage_tools.py`**

```python
"""
Storage Tools for File Operations
"""

import pandas as pd
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from .database_tools import get_uploaded_file


async def load_file_data(
    file_ids: List[str],
    db_session: AsyncSession,
    storage_service: Any
) -> Dict[str, pd.DataFrame]:
    """
    Load data from uploaded files.

    Args:
        file_ids: List of file IDs
        db_session: Database session
        storage_service: Storage service instance

    Returns:
        Dictionary mapping file_id to DataFrame
    """

    file_data = {}

    for file_id in file_ids:
        # Get file record
        file_record = await get_uploaded_file(file_id, db_session)

        if not file_record:
            continue

        # Load file from storage
        file_path = file_record.file_path
        file_bytes = await storage_service.get_file(file_path)

        if not file_bytes:
            continue

        # Parse based on file type
        if file_record.content_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            # Excel file
            from io import BytesIO
            df = pd.read_excel(BytesIO(file_bytes))
            file_data[file_id] = df
        elif file_record.content_type == 'text/csv':
            # CSV file
            from io import StringIO
            df = pd.read_csv(StringIO(file_bytes.decode('utf-8')))
            file_data[file_id] = df

    return file_data
```

**File: `agents/langgraph/tools/chart_tools.py`**

```python
"""
Chart Generation Tools
"""

import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any
import uuid
import os


async def create_chart_from_data(
    data: Dict[str, pd.DataFrame],
    query: str,
    request_id: str
) -> Dict[str, Any]:
    """
    Create chart from data based on query.

    Args:
        data: Dictionary of DataFrames
        query: User query for chart type/style
        request_id: Unique request ID

    Returns:
        Chart result with URL and metadata
    """

    # Get first DataFrame
    df = next(iter(data.values()))

    # Detect chart type from query
    query_lower = query.lower()

    if "trend" in query_lower:
        fig = create_trend_chart(df)
    elif "comparison" in query_lower or "compare" in query_lower:
        fig = create_comparison_chart(df)
    else:
        fig = create_default_chart(df)

    # Save chart
    chart_id = str(uuid.uuid4())
    charts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "charts")
    os.makedirs(charts_dir, exist_ok=True)

    chart_path = os.path.join(charts_dir, f"{chart_id}.png")
    fig.write_image(chart_path)

    # Generate insights
    insights = generate_insights(df)

    return {
        "chart_id": chart_id,
        "chart_url": f"/api/v1/charts/{chart_id}",
        "description": "Chart generated from uploaded data",
        "insights": insights
    }


def create_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Create trend line chart"""
    fig = go.Figure()

    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols[:3]:  # Limit to 3 lines
        fig.add_trace(go.Scatter(
            y=df[col],
            mode='lines+markers',
            name=col
        ))

    fig.update_layout(title="Trend Analysis", template="plotly_white")
    return fig


def create_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create comparison bar chart"""
    fig = go.Figure()

    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) >= 1:
        fig.add_trace(go.Bar(
            y=df[numeric_cols[0]],
            name=numeric_cols[0]
        ))

    fig.update_layout(title="Comparison", template="plotly_white")
    return fig


def create_default_chart(df: pd.DataFrame) -> go.Figure:
    """Create default chart"""
    return create_trend_chart(df)


def generate_insights(df: pd.DataFrame) -> list:
    """Generate insights from data"""
    insights = []

    # Basic statistics
    insights.append(f"Dataset has {len(df)} rows and {len(df.columns)} columns")

    # Numeric insights
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        for col in numeric_cols[:3]:
            mean_val = df[col].mean()
            insights.append(f"{col}: average = {mean_val:.2f}")

    return insights
```

---

## 5. Agent Migration Strategy

### 5.1 Migration Mapping

**Current → LangGraph:**

| Current Agent | LangGraph Node | File Location |
|--------------|----------------|---------------|
| `ChartGenerator` | `chart_agent_node` | `nodes/chart_agent.py` |
| `AIChartGenerator` | `chart_agent_node` (AI version) | `nodes/chart_agent.py` |
| `BP003IntelligentAgent` | `data_agent_node` | `nodes/data_agent.py` |
| `BP004AnomalyDetectionAgent` | `anomaly_agent_node` | `nodes/anomaly_agent.py` |
| `GeneralChatAgent` | `general_agent_node` | `nodes/general_agent.py` |
| `AgentOrchestrator` | `supervisor_node` | `supervisor.py` |

### 5.2 Node Template

**Standard Node Structure:**

```python
"""
[Agent Name] Node
[Description]
"""

from langchain_core.messages import AIMessage
from ..state import AgentState
from ..tools import [required_tools]
from ..config import get_llm


async def [agent_name]_node(state: AgentState) -> AgentState:
    """
    [Agent purpose]

    Args:
        state: Current agent state

    Returns:
        Updated state with response
    """

    try:
        # 1. Extract inputs from state
        user_query = state["user_query"]
        context = state["context"]

        # 2. Load required data/services
        db_session = state["db_session"]
        storage = state["storage_service"]

        # 3. Perform agent-specific processing
        # ... implementation ...

        # 4. Generate response
        response_text = "..."

        # 5. Update state
        state["agent_response"] = response_text
        state["confidence"] = 0.9
        state["messages"].append(AIMessage(content=response_text))

    except Exception as e:
        state["error"] = str(e)
        state["agent_response"] = f"Error: {str(e)}"
        state["confidence"] = 0.0

    return state
```

---

## 6. Integration Layer

### 6.1 FastAPI Integration

**Modified: `api/chat.py`**

```python
"""
Chat API with LangGraph Integration
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agents.langgraph.graph import run_agent_graph
from services.unified_storage import unified_storage
from core.database import get_db
import uuid

router = APIRouter()


@router.post("/chat/send")
async def send_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Send chat message and get AI response using LangGraph"""

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

        # Store in database
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
            agent_id=agent_used,
            meta_data={
                "confidence": confidence,
                "execution_metadata": final_state.get("execution_metadata")
            }
        )
        db.add(assistant_message)
        await db.commit()

        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=response_text,
                agent_id=agent_used,
                metadata={"confidence": confidence}
            ),
            agent_used=agent_used,
            confidence=confidence,
            session_id=session_id
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

### 6.2 Streaming Support

**Streaming with LangGraph:**

```python
@router.post("/chat/stream")
async def stream_chat_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream chat responses in real-time"""

    from fastapi.responses import StreamingResponse
    import json

    async def event_generator():
        try:
            # Create initial state
            initial_state = create_initial_state(...)

            # Stream graph execution
            async for event in compiled_graph.astream(initial_state):
                # Send updates to client
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 7. Migration Phases

### Phase 1: Setup LangGraph Infrastructure (Day 1-2)

**Tasks:**
1. ✓ Add LangGraph dependencies to requirements.txt
2. ✓ Create directory structure (`agents/langgraph/`)
3. ✓ Implement `state.py` with AgentState
4. ✓ Implement `graph.py` with basic graph
5. ✓ Implement `supervisor.py` with routing
6. ✓ Implement tools (`database_tools.py`, `storage_tools.py`)
7. ✓ Test basic graph execution

**Verification:**
- Graph can be instantiated without errors
- State flows through supervisor
- Tools can access database and storage

### Phase 2: Migrate Chart Generator (Day 3-4)

**Tasks:**
1. ✓ Create `nodes/chart_agent.py`
2. ✓ Implement `chart_tools.py`
3. ✓ Port ChartGenerator logic to chart_agent_node
4. ✓ Test chart generation through graph
5. ✓ Update API endpoint to use graph
6. ✓ Verify frontend still works

**Verification:**
- Chart requests route to chart_agent
- Charts are generated and displayed
- Files are loaded correctly
- No regressions in frontend

### Phase 3: Migrate Other Agents (Day 5-6)

**Tasks:**
1. ✓ Create `nodes/data_agent.py`
2. ✓ Create `nodes/anomaly_agent.py`
3. ✓ Create `nodes/general_agent.py`
4. ✓ Port BP003 logic to data_agent
5. ✓ Port BP004 logic to anomaly_agent
6. ✓ Port GeneralChatAgent logic to general_agent
7. ✓ Test all agent types

**Verification:**
- All query types route correctly
- Each agent produces expected outputs
- Confidence scores are reasonable

### Phase 4: Cleanup & Documentation (Day 7-8)

**Tasks:**
1. ✓ Remove deprecated files (base.py, registry.py, orchestrator.py)
2. ✓ Update main.py to only use graph
3. ✓ Add comprehensive logging
4. ✓ Write agent creation guide
5. ✓ Add integration tests
6. ✓ Update deployment scripts
7. ✓ Document new architecture

**Verification:**
- No references to old agent system
- All tests pass
- Documentation is complete
- Deployment works

---

## 8. Agent Creation Guide

### 8.1 Adding a New Agent (5-10 Minutes)

**Step 1: Create Node File**

Create `agents/langgraph/nodes/my_new_agent.py`:

```python
"""
My New Agent - [Description]
"""

from langchain_core.messages import AIMessage
from ..state import AgentState
from ..config import get_llm


async def my_new_agent_node(state: AgentState) -> AgentState:
    """
    [Purpose]

    Args:
        state: Current agent state

    Returns:
        Updated state
    """

    # Your implementation here
    user_query = state["user_query"]

    # Process query
    response_text = f"Processed: {user_query}"

    # Update state
    state["agent_response"] = response_text
    state["confidence"] = 0.9
    state["messages"].append(AIMessage(content=response_text))

    return state
```

**Step 2: Register in Graph**

Edit `agents/langgraph/graph.py`:

```python
# Import your node
from .nodes.my_new_agent import my_new_agent_node

# Add to graph
workflow.add_node("my_new_agent", my_new_agent_node)

# Update routing
def route_from_supervisor(state: AgentState):
    next_agent = state.get("next_agent")

    if next_agent == "my_new_agent":
        return "my_new_agent"
    # ... other agents ...

# Add conditional edge
workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "my_new_agent": "my_new_agent",
        # ... other agents ...
    }
)

# Add end edge
workflow.add_edge("my_new_agent", END)
```

**Step 3: Update Supervisor**

Edit `agents/langgraph/supervisor.py`:

```python
SUPERVISOR_SYSTEM_PROMPT = """...
5. **my_new_agent**: [Description]
   - Keywords: [keywords]
...
"""

# Add routing logic
if any(kw in query_lower for kw in ["keyword1", "keyword2"]):
    next_agent = "my_new_agent"
```

**Step 4: Test**

```python
# Test your agent
final_state = await run_agent_graph(
    user_query="keyword1 test query",
    context={},
    uploaded_files=[],
    db_session=db,
    storage_service=storage,
    request_id="test-123"
)

assert final_state["selected_agent"] == "my_new_agent"
assert final_state["agent_response"] is not None
```

**Done!** Your agent is now integrated.

### 8.2 Agent Development Checklist

- [ ] Create node file in `nodes/` directory
- [ ] Implement node function with signature: `async def node(state: AgentState) -> AgentState`
- [ ] Update graph.py with node registration
- [ ] Update supervisor.py with routing logic
- [ ] Add keywords/patterns for routing
- [ ] Create any required tools
- [ ] Write unit tests
- [ ] Test through API
- [ ] Document agent behavior

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Test File: `tests/test_langgraph_agents.py`**

```python
import pytest
from agents.langgraph.graph import run_agent_graph
from agents.langgraph.state import create_initial_state


@pytest.mark.asyncio
async def test_supervisor_routing(db_session, storage_service):
    """Test supervisor routes to correct agent"""

    test_cases = [
        ("create a chart", "chart_agent"),
        ("detect anomalies", "anomaly_agent"),
        ("analyze data", "data_agent"),
        ("hello", "general_agent"),
    ]

    for query, expected_agent in test_cases:
        state = await run_agent_graph(
            user_query=query,
            context={},
            uploaded_files=[],
            db_session=db_session,
            storage_service=storage_service,
            request_id="test"
        )

        assert state["selected_agent"] == expected_agent


@pytest.mark.asyncio
async def test_chart_agent(db_session, storage_service):
    """Test chart agent generates charts"""

    # Upload test file first
    file_id = await upload_test_file(db_session, storage_service)

    state = await run_agent_graph(
        user_query="create a trend chart",
        context={},
        uploaded_files=[file_id],
        db_session=db_session,
        storage_service=storage_service,
        request_id="test"
    )

    assert state["selected_agent"] == "chart_agent"
    assert "chart_url" in state.get("intermediate_results", {}).get("chart", {})
    assert state["confidence"] > 0.5
```

### 9.2 Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow(client, db_session):
    """Test full API workflow"""

    # Upload file
    response = await client.post("/api/v1/files/upload", files={"file": test_file})
    file_id = response.json()["file_id"]

    # Send chat message
    response = await client.post("/api/v1/chat/send", json={
        "message": "create a chart from my data",
        "files": [file_id]
    })

    assert response.status_code == 200
    data = response.json()
    assert "chart" in data["message"]["content"].lower()
```

---

## 10. Performance Considerations

### 10.1 Optimization Tips

**1. State Size Management:**
- Don't store large DataFrames in state
- Use file references, load data on-demand
- Clear intermediate results after use

**2. Async Operations:**
- All database queries use async
- File loading is async
- LLM calls are async

**3. Caching:**
- Cache file data within a session
- Cache LLM responses for similar queries
- Use Redis for cross-request caching

**4. Parallel Execution:**
- Run independent agents in parallel
- Use `asyncio.gather()` for multiple file loads
- Batch database queries

### 10.2 Monitoring

**Add metrics collection:**

```python
# In each node
import time

async def agent_node(state: AgentState) -> AgentState:
    start = time.time()

    # ... processing ...

    duration = time.time() - start
    state["execution_metadata"]["node_times"] = state["execution_metadata"].get("node_times", {})
    state["execution_metadata"]["node_times"]["agent_node"] = duration

    return state
```

---

## Appendix

### A. Dependencies to Add

**requirements.txt additions:**

```
# LangGraph & LangChain
langgraph==0.2.77
langchain==0.3.14
langchain-openai==0.2.14
langchain-core==0.3.44
langchain-community==0.3.14

# LLM Providers (choose one or more)
openai==1.59.9
anthropic==0.41.1

# Optional: LangSmith for debugging
langsmith==0.2.11
```

### B. Configuration

**Add to .env:**

```bash
# LangGraph Configuration
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Optional: LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=agent-chat
```

### C. Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python -m alembic upgrade head

# 3. Start server
python main.py

# 4. Test LangGraph
python -m pytest tests/test_langgraph_agents.py -v
```

### D. Troubleshooting

**Common Issues:**

1. **Graph not compiling:**
   - Check all node functions have correct signature
   - Verify edges are properly defined
   - Ensure END node is reachable

2. **State not updating:**
   - Nodes must return modified state
   - Check TypedDict field names match
   - Use annotated types for list operations

3. **Tools not working:**
   - Verify services are injected in initial state
   - Check async/await syntax
   - Test tools independently first

---

## Summary

This architecture plan provides:

1. **Complete LangGraph structure** with supervisor pattern
2. **Preservation of all existing infrastructure** (DB, storage, API)
3. **Clear migration path** in 4 phases
4. **Easy agent addition** (5-10 minutes per agent)
5. **Production-ready patterns** with error handling, logging, metrics
6. **Comprehensive testing strategy**

**Next Steps:**
1. Review this plan with team
2. Begin Phase 1 (LangGraph setup)
3. Migrate one agent as proof of concept
4. Complete full migration
5. Cleanup old code

**Estimated Timeline:** 7-8 days for complete migration
**Risk:** Low (incremental, backward compatible)
**Benefit:** Standard architecture, easier maintenance, better composability