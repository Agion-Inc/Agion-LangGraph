# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agion-LangGraph is a production-ready LangGraph-based multi-agent orchestration platform powered by GPT-5 via Requesty AI. The platform uses LangGraph 0.6.8 for state graph-based agent coordination with supervisor routing.

**Stack:**
- Backend: Python 3.13, FastAPI, PostgreSQL, SQLAlchemy (async), Azure Blob Storage
- Frontend: React 19, TypeScript, TailwindCSS
- AI Framework: LangGraph 0.6.8, LangChain, OpenAI GPT-5 (via Requesty AI)
- Deployment: Azure Kubernetes Service (AKS)

## Development Commands

### Backend

```bash
cd backend

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize database
python init_database.py

# Run development server
python start_server.py  # Handles Pydantic plugin issues

# Run tests
pytest

# Database migrations (if using Alembic)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm start

# Production build
npm run build

# Run tests
npm test

# Linting
npm run lint
npm run lint:fix

# Formatting
npm run format
```

## LangGraph Architecture

The platform uses a **supervisor routing pattern** where queries flow through a state graph:

1. **Entry Point**: User query → `supervisor_node`
2. **Routing**: Supervisor analyzes query and selects specialized agent
3. **Execution**: Selected agent processes query
4. **Exit**: Agent response → END

### State Management

All agents share `AgentState` (defined in `backend/langgraph_agents/state.py`):
- **Immutable state**: Nodes return new state dicts, not mutations
- **Annotated fields**: `messages` and `execution_path` use `operator.add` for append-only behavior
- **Type safety**: Uses TypedDict for compile-time validation

Key state fields:
- `messages`: LangChain message history
- `query`: Current user query
- `session_id`: Database session reference
- `uploaded_files`: File IDs from user uploads
- `file_data`: Loaded DataFrames/parsed content
- `selected_agent`: Routing decision from supervisor
- `agent_response`: Final response text
- `agent_data`: Additional data (charts, analysis)
- `error`: Error tracking

### Agent Nodes

Located in `backend/langgraph_agents/nodes/`:

1. **supervisor.py**: Routes queries to specialized agents using GPT-5
2. **chart_agent.py**: Generates Plotly visualizations, exports to PNG via Kaleido
3. **brand_performance_agent.py**: KPI analysis, data quality checks, business insights
4. **forecasting_agent.py**: Time series forecasting using Facebook Prophet
5. **anomaly_detection_agent.py**: Statistical outlier detection with scikit-learn
6. **general_agent.py**: Conversational AI for general queries

Each node:
- Receives `AgentState` as input
- Returns updated `AgentState` (not mutations)
- Adds execution tracking via `add_execution_step()`
- Handles errors via `set_error()`

### Tools

Located in `backend/langgraph_agents/tools/`:
- **chart_tools.py**: Plotly chart generation, safe code execution
- **analytics_tools.py**: Prophet forecasting, anomaly detection, statistical analysis
- **database_tools.py**: PostgreSQL queries via async SQLAlchemy
- **storage_tools.py**: Azure Blob Storage file operations

### Graph Definition

`backend/langgraph_agents/graph.py`:
- Creates `StateGraph(AgentState)`
- Adds all agent nodes
- Sets `supervisor` as entry point
- Uses `add_conditional_edges()` for routing
- Compiles graph with `graph.compile()`

**Critical**: The `route_to_agent()` function maps supervisor decisions to node names. If adding new agents, update this mapping.

## Key Technical Patterns

### 1. Deterministic AI Responses
All LLM calls use:
```python
temperature=0.0  # Deterministic
seed=42          # Reproducible
```

### 2. Chart Generation Pipeline
- User uploads CSV/Excel → stored in Azure Blob
- Chart Agent generates Plotly Python code via GPT-5
- Code executes in isolated namespace (safe eval)
- Exports to PNG using Kaleido (no CDN dependencies)
- PNG stored in Azure Blob with permanent URL

### 3. Async Throughout
- All database operations use `async`/`await`
- SQLAlchemy with `asyncpg` driver
- FastAPI endpoints are `async def`
- Azure Blob operations are async

### 4. File Upload Flow
1. Frontend → `POST /api/v1/files/upload`
2. Backend validates file (CSV/Excel only)
3. Saves to Azure Blob Storage
4. Creates database record
5. Returns file ID to frontend
6. User query includes file ID
7. Agent loads file data on demand

### 5. Password Protection
- Backend: `ACCESS_PASSWORD` env var
- Frontend: `REACT_APP_PASSWORD` env var
- Simple password check, not JWT/sessions

## Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER_NAME=agent-chat

# Requesty AI (GPT-5)
REQUESTY_AI_API_KEY=your_key
REQUESTY_AI_API_BASE=https://api.requesty.ai/v1

# Auth
ACCESS_PASSWORD=your_password
```

### Frontend (.env)

```bash
REACT_APP_API_URL=https://backend-url.com
REACT_APP_PASSWORD=your_password
```

## Common Tasks

### Adding a New Agent

1. Create node file in `backend/langgraph_agents/nodes/new_agent.py`
2. Define node function: `def new_agent_node(state: AgentState) -> AgentState`
3. Add node to graph in `backend/langgraph_agents/graph.py`:
   - Import node function
   - `graph.add_node("new_agent", new_agent_node)`
   - Add edge: `graph.add_edge("new_agent", END)`
   - Update `route_to_agent()` mapping
4. Update supervisor prompt to include new agent capability

### Modifying Agent State

1. Edit `backend/langgraph_agents/state.py`
2. Add field to `AgentState` TypedDict
3. Use `Annotated[Type, operator.add]` for append-only fields
4. Update `create_initial_state()` with default value
5. Test all existing nodes for compatibility

### Debugging LangGraph Execution

Check `state["execution_path"]` to see which nodes executed:
```python
print(f"Execution path: {state['execution_path']}")
# Output: ['supervisor', 'chart_agent']
```

### Running Single Tests

Backend:
```bash
cd backend
pytest tests/test_specific.py::test_function_name -v
```

Frontend:
```bash
cd frontend
npm test -- --testNamePattern="test name"
```

## Production Deployment

### Docker Build

```bash
# Backend
docker build -f Dockerfile.backend.prod -t agent-chat-backend:latest .

# Frontend
docker build -f Dockerfile.frontend.prod -t agent-chat-frontend:latest .
```

### Kubernetes Deployment

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -n agion-airgb
kubectl logs -f <pod-name> -n agion-airgb
```

## Agion Platform Integration

This LangGraph container operates as part of the Agion AI platform deployed on the same AKS cluster.

### Agent Registry
- **Namespace**: `agion-langgraph` (agent container)
- **Container ID**: `langgraph-v2`
- **Registry Service**: `registry-service.agion-core.svc.cluster.local:8085`
- **Governance Service**: `governance-service.agion-core.svc.cluster.local:8080`

### Trust Score Philosophy
**All agents start at 0.4 trust (40%) and graduate at 0.6 (60%) after 10 successful executions.**

- **Starting trust**: 0.4 (baseline competence assumed)
- **Graduation threshold**: 0.6 (proven reliability)
- **Increment per success**: +2% (moderate strategy, 10 successes to graduate)
- **Decrement per failure**: -2%
- **Decrement per error**: -3%
- **User feedback bonus**: +0.5% for ratings ≥4
- **Governance violation**: -5%

Trust Score Milestones:
- 0.40: Starting (baseline trust)
- 0.40-0.50: Learning (1-5 successes)
- 0.50-0.60: Developing (5-10 successes)
- 0.60: **Graduated** (10 successes - proven reliability)
- 0.60-0.80: Trusted (most tasks)
- 0.80-1.00: Expert (critical tasks)

### Agent Registration
On startup, all 6 agents register with platform:
- Capabilities, input/output schemas
- Performance metrics tracking
- Trust score initialization (0.0)
- Governance policies
- Endpoints for invocation

After each execution, agents report metrics to governance service and trust scores update dynamically.

## Important Notes

- **Never mutate state**: Always return new state dicts from nodes
- **Supervisor is critical**: All routing decisions go through supervisor
- **File data loading**: Files are loaded lazily when agents need them, not on upload
- **PNG generation**: Charts must be PNG (not HTML) for security/CSP compliance
- **Async DB**: Always use async SQLAlchemy operations, never sync
- **Error handling**: Use `set_error()` helper, don't raise exceptions from nodes
- **Pydantic plugins**: Disabled in `start_server.py` to avoid network timeouts
- **Trust scores**: Start at 0.4, graduate at 0.6 (10 successes), report after each execution
- **Governance**: Container is "dumb" execution engine; platform provides all governance intelligence

## Documentation

Additional docs in `docs/` directory:
- `LANGGRAPH_ARCHITECTURE.md`: Detailed LangGraph design
- `QUICK_START.md`: Getting started guide
- `API.md`: API endpoint reference
- `DEVELOPMENT.md`: Development best practices
