# Agent-Chat Architecture Diagrams

## System Architecture Diagrams

### 1. Current Architecture (To Be Replaced)

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Chat   │  │  Files   │  │  Agents  │  │  Charts  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              API Layer (chat, files, etc.)             │ │
│  └─────────────────────────┬──────────────────────────────┘ │
│                            │                                 │
│  ┌─────────────────────────▼──────────────────────────────┐ │
│  │              Agent Registry (keyword matching)         │ │
│  └─────────────────────────┬──────────────────────────────┘ │
│                            │                                 │
│  ┌─────────────────────────▼──────────────────────────────┐ │
│  │                    Agents (mixed implementations)       │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ General  │  │  Chart   │  │ Anomaly  │  ...       │ │
│  │  │   Chat   │  │Generator │  │ Detector │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  │       ↓              ↓              ↓                   │ │
│  │  [Different implementations, tight coupling]           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

Issues:
❌ Tight coupling between orchestrator and specific agents
❌ Inconsistent agent interfaces
❌ No clear separation of concerns
❌ Hard to add new agents
❌ Database imports scattered everywhere
```

---

### 2. Proposed Architecture (Clean, Modular)

```
┌───────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │   Chat   │  │  Files   │  │  Agents  │  │  Charts  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└────────────────────────┬──────────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Chat API  │  │  Files API  │  │ Agents API  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼─────────────────┼─────────────────┼────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Framework Layer (Stable)                       │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Agent Router (Smart Routing)                             │   │
│  │  - Keyword matching                                       │   │
│  │  - Trigger detection                                      │   │
│  │  - Capability matching                                    │   │
│  │  - Confidence scoring                                     │   │
│  └────────────────────────┬──────────────────────────────────┘   │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────────┐   │
│  │  Agent Registry (Discovery & Management)                  │   │
│  │  - Auto-discovery from manifest files                     │   │
│  │  - Lifecycle management                                   │   │
│  │  - Health checks                                          │   │
│  └────────────────────────┬──────────────────────────────────┘   │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────────┐   │
│  │  Agent Executor (Execution & Metrics)                     │   │
│  │  - Timeout management                                     │   │
│  │  - Error handling                                         │   │
│  │  - Metrics collection                                     │   │
│  │  - Logging                                                │   │
│  └────────────────────────┬──────────────────────────────────┘   │
│                           │                                       │
│  ┌────────────────────────▼──────────────────────────────────┐   │
│  │  Agent Orchestrator (Multi-Agent Coordination)            │   │
│  │  - Sequential workflows                                   │   │
│  │  - Parallel execution                                     │   │
│  │  - DAG-based workflows                                    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Agent Services (Dependency Injection)                    │   │
│  │  - Database (AsyncSession)                                │   │
│  │  - Storage (File operations)                              │   │
│  │  - Cache (Redis/Memory)                                   │   │
│  │  - LLM (OpenAI/Anthropic)                                 │   │
│  │  - Config (Environment)                                   │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Agent Implementations (Extensible)             │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  General Chat    │  │  Chart Generator │  │ Anomaly Detect │ │
│  │                  │  │                  │  │                │ │
│  │  manifest.yaml   │  │  manifest.yaml   │  │ manifest.yaml  │ │
│  │  agent.py        │  │  agent.py        │  │ agent.py       │ │
│  │  prompts.py      │  │  templates/      │  │ models.py      │ │
│  │  tests/          │  │  tests/          │  │ tests/         │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  Brand Analyzer  │  │  SQL Generator   │  │  (Your Agent)  │ │
│  │  manifest.yaml   │  │  manifest.yaml   │  │ manifest.yaml  │ │
│  │  agent.py        │  │  agent.py        │  │ agent.py       │ │
│  │  tests/          │  │  tests/          │  │ tests/         │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                   │
│  All agents implement:                                            │
│  - BaseAgent interface                                            │
│  - execute(request) -> response                                   │
│  - validate(request) -> bool                                      │
│  - stream(request) -> AsyncIterator                               │
└───────────────────────────────────────────────────────────────────┘

Benefits:
✅ Loose coupling via dependency injection
✅ Consistent agent interface
✅ Clear separation: Framework / Agents / API
✅ Easy to add/remove agents
✅ Services injected cleanly
```

---

### 3. Agent Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  1. Application Startup                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Framework Initialization                                 │
│     - Initialize database pool                               │
│     - Initialize cache (Redis)                               │
│     - Initialize LLM clients                                 │
│     - Create AgentServices container                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Agent Discovery                                          │
│     - Scan agents/ directory                                 │
│     - Load manifest.yaml files                               │
│     - Validate agent structure                               │
│     - Import agent classes                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Agent Registration                                       │
│     - Instantiate agents with services                       │
│     - Register in AgentRegistry                              │
│     - Build routing indices                                  │
│     - Health check                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. API Ready                                                │
│     - FastAPI server starts                                  │
│     - WebSocket connections accepted                         │
│     - System ready for requests                              │
└─────────────────────────────────────────────────────────────┘


Request Handling Flow:

User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  1. API Endpoint Receives Request                            │
│     POST /api/v1/chat                                        │
│     { "message": "Create a chart", "files": [...] }          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Router Scores Agents                                     │
│     AgentRouter.route(query, context)                        │
│     │                                                         │
│     ├─ Keyword matching                                      │
│     ├─ Trigger detection                                     │
│     ├─ File requirement check                                │
│     ├─ Agent validation                                      │
│     └─ Score & rank agents                                   │
│                                                               │
│     Returns: [                                               │
│       {agent: "chart-generator", score: 24.5, conf: 0.92},  │
│       {agent: "general-chat", score: 2.0, conf: 0.3}        │
│     ]                                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Select Best Agent                                        │
│     agent_id = scores[0].agent_id                            │
│     agent = registry.get(agent_id)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Prepare Agent Request                                    │
│     request = AgentRequest(                                  │
│       query="Create a chart",                                │
│       context={},                                            │
│       files=["file-id-123"]                                  │
│     )                                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Agent Executor Wraps Execution                           │
│     try:                                                     │
│       start_time = time()                                    │
│       response = await agent.execute(request)                │
│       execution_time = time() - start_time                   │
│       log_metrics(agent_id, execution_time)                  │
│     except TimeoutError:                                     │
│       return error_response()                                │
│     except Exception as e:                                   │
│       log_error(e)                                           │
│       return error_response()                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Agent Executes                                           │
│     ChartGeneratorAgent.execute(request):                    │
│       1. Load files using services.storage                   │
│       2. Analyze data                                        │
│       3. Call LLM via services.llm                           │
│       4. Generate chart                                      │
│       5. Save chart using services.storage                   │
│       6. Return response                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Response Formatted & Returned                            │
│     {                                                         │
│       "message": "Chart created!",                           │
│       "agent_used": "chart-generator",                       │
│       "data": {"chart_url": "/charts/abc123"},               │
│       "confidence": 0.95                                     │
│     }                                                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                    User sees chart
```

---

### 4. Routing Decision Tree

```
User Query: "Create a line chart showing sales trends"
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step 1: Keyword Extraction                 │
│  Words: [create, line, chart, showing,      │
│          sales, trends]                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 2: Agent Keyword Matching             │
│                                              │
│  Chart Generator:                           │
│    ✓ "chart" → +2.0                         │
│    ✓ "line" → +2.0                          │
│    ✓ "trends" → +2.0                        │
│    Score: 6.0                                │
│                                              │
│  Anomaly Detector:                          │
│    ✗ No matches                             │
│    Score: 0.0                                │
│                                              │
│  General Chat:                              │
│    ✓ "showing" → +0.5 (weak)                │
│    Score: 0.5                                │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 3: Trigger Detection                  │
│                                              │
│  Chart Generator:                           │
│    ✓ "create a...chart" → +20.0            │
│    Score: 26.0                               │
│                                              │
│  Others: No trigger matches                 │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 4: Context Validation                 │
│                                              │
│  Chart Generator:                           │
│    requires_files: true                     │
│    files_present: ? (check context)         │
│                                              │
│    If files present: +5.0                   │
│    If files missing: -10.0                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 5: Priority Boost                     │
│                                              │
│  Chart Generator:                           │
│    priority: 8/10                           │
│    boost: 0.8                                │
│    final_score: 26.0 * 0.8 = 20.8           │
│                                              │
│  General Chat:                              │
│    priority: 5/10                           │
│    boost: 0.5                                │
│    final_score: 0.5 * 0.5 = 0.25            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Step 6: Ranking                            │
│                                              │
│  1. Chart Generator:                        │
│     score: 20.8                              │
│     confidence: 0.92 ✅                      │
│                                              │
│  2. General Chat:                           │
│     score: 0.25                              │
│     confidence: 0.1                          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Decision: Use Chart Generator              │
│  Confidence: 92%                             │
└─────────────────────────────────────────────┘
```

---

### 5. Multi-Agent Orchestration

#### Sequential Workflow

```
User: "Analyze sales data and create a report with charts"

┌─────────────────────────────────────────────────────────────┐
│  Step 1: Query Classification                                │
│  Router detects: Data analysis + Visualization + Reporting   │
│                                                               │
│  Agents needed:                                              │
│    1. Data Analyzer (analyze data)                           │
│    2. Chart Generator (create visualizations)                │
│    3. Report Generator (compile report)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Task 1: Data Analyzer                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Input:                                               │    │
│  │   - User query                                       │    │
│  │   - Files: [sales_data.csv]                         │    │
│  │                                                       │    │
│  │ Processing:                                          │    │
│  │   - Load CSV                                         │    │
│  │   - Calculate metrics                                │    │
│  │   - Identify trends                                  │    │
│  │   - Detect anomalies                                 │    │
│  │                                                       │    │
│  │ Output:                                              │    │
│  │   {                                                  │    │
│  │     "total_sales": 1500000,                          │    │
│  │     "growth_rate": 15.2,                             │    │
│  │     "trends": ["upward", "seasonal"],                │    │
│  │     "top_products": [...],                           │    │
│  │     "data_summary": {...}                            │    │
│  │   }                                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ Pass results to next agent
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Task 2: Chart Generator                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Input:                                               │    │
│  │   - Previous results (data_summary)                  │    │
│  │   - Files: [sales_data.csv]                         │    │
│  │                                                       │    │
│  │ Processing:                                          │    │
│  │   - Use data_summary for context                     │    │
│  │   - Create trend chart                               │    │
│  │   - Create product comparison chart                  │    │
│  │   - Create growth chart                              │    │
│  │                                                       │    │
│  │ Output:                                              │    │
│  │   {                                                  │    │
│  │     "charts": [                                      │    │
│  │       {"type": "line", "url": "/charts/abc"},        │    │
│  │       {"type": "bar", "url": "/charts/def"},         │    │
│  │       {"type": "area", "url": "/charts/ghi"}         │    │
│  │     ]                                                 │    │
│  │   }                                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ Pass all results to final agent
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Task 3: Report Generator                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Input:                                               │    │
│  │   - Data analysis results                            │    │
│  │   - Chart URLs                                       │    │
│  │   - User query context                               │    │
│  │                                                       │    │
│  │ Processing:                                          │    │
│  │   - Synthesize insights                              │    │
│  │   - Embed charts                                     │    │
│  │   - Generate narrative                               │    │
│  │   - Format as markdown                               │    │
│  │                                                       │    │
│  │ Output:                                              │    │
│  │   # Sales Analysis Report                            │    │
│  │                                                       │    │
│  │   ## Executive Summary                               │    │
│  │   Total sales: $1.5M (+15.2% YoY)                    │    │
│  │                                                       │    │
│  │   ## Trends                                          │    │
│  │   ![Trend Chart](/charts/abc)                        │    │
│  │   ...                                                 │    │
│  │                                                       │    │
│  │   ## Product Performance                             │    │
│  │   ![Product Chart](/charts/def)                      │    │
│  │   ...                                                 │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                 Final Report to User
```

#### Parallel Workflow

```
User: "Compare these three sales datasets"

┌─────────────────────────────────────────────────────────────┐
│  Orchestrator: Parallel Analysis                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌───────┐        ┌───────┐        ┌───────┐
    │Agent 1│        │Agent 2│        │Agent 3│
    │       │        │       │        │       │
    │Analyze│        │Analyze│        │Analyze│
    │File 1 │        │File 2 │        │File 3 │
    └───┬───┘        └───┬───┘        └───┬───┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  Aggregator Agent              │
        │  - Combine results             │
        │  - Generate comparison         │
        │  - Create unified charts       │
        └────────────────┬───────────────┘
                         │
                         ▼
                  Final Comparison
```

---

### 6. Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         User                                  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 1. Upload Files
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  File Storage Service                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  - Validate file type                                   │  │
│  │  - Generate file ID                                     │  │
│  │  - Store in filesystem/blob storage                     │  │
│  │  - Create database record                               │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 2. File ID
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  User sends query with file IDs                               │
│  POST /api/v1/chat                                            │
│  {                                                             │
│    "message": "Analyze this data",                           │
│    "files": ["file-id-123"]                                  │
│  }                                                             │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 3. Route to Agent
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Framework                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Router: Select agent based on query                    │  │
│  │  Registry: Get agent instance                           │  │
│  │  Executor: Prepare agent request                        │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 4. Execute Agent
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent (e.g., Data Analyzer)                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Step 1: Load file via services.storage                 │  │
│  │    file_data = await services.storage.load("file-123")  │  │
│  │                                                           │  │
│  │  Step 2: Process data                                    │  │
│  │    df = pd.read_csv(file_data)                          │  │
│  │    analysis = analyze(df)                                │  │
│  │                                                           │  │
│  │  Step 3: Generate insights using LLM                     │  │
│  │    insights = await services.llm.complete(...)           │  │
│  │                                                           │  │
│  │  Step 4: Cache results                                   │  │
│  │    await services.cache.set("analysis:123", results)     │  │
│  │                                                           │  │
│  │  Step 5: Store artifacts                                 │  │
│  │    chart_id = await services.storage.save(chart)         │  │
│  │                                                           │  │
│  │  Step 6: Save to database                                │  │
│  │    session = await services.db.get_session()             │  │
│  │    await session.commit()                                │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 5. Return Response
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  API Response                                                 │
│  {                                                             │
│    "message": "Analysis complete! Here are the insights...",  │
│    "data": {                                                  │
│      "summary": {...},                                        │
│      "charts": [...],                                         │
│      "recommendations": [...]                                 │
│    },                                                          │
│    "agent_used": "data-analyzer",                            │
│    "confidence": 0.95                                         │
│  }                                                             │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ 6. Display Results
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Frontend renders:                                            │
│  - Analysis text                                              │
│  - Embedded charts                                            │
│  - Recommendations                                            │
│  - Suggested follow-up questions                             │
└──────────────────────────────────────────────────────────────┘
```

---

### 7. Dependency Injection Pattern

```
┌──────────────────────────────────────────────────────────────┐
│  Application Startup                                          │
│                                                                │
│  1. Initialize Core Services                                  │
│     ┌────────────────────────────────────────────────────┐   │
│     │  database = DatabaseService(connection_pool)        │   │
│     │  storage = StorageService(filesystem_or_blob)       │   │
│     │  cache = CacheService(redis_client)                 │   │
│     │  llm = LLMService(openai_client)                    │   │
│     └────────────────────────────────────────────────────┘   │
│                                                                │
│  2. Create Services Container                                 │
│     ┌────────────────────────────────────────────────────┐   │
│     │  services = AgentServices(                          │   │
│     │    db=database,                                     │   │
│     │    storage=storage,                                 │   │
│     │    cache=cache,                                     │   │
│     │    llm=llm,                                         │   │
│     │    config=app_config                                │   │
│     │  )                                                  │   │
│     └────────────────────────────────────────────────────┘   │
│                                                                │
│  3. Instantiate Agents with Services                          │
│     ┌────────────────────────────────────────────────────┐   │
│     │  chart_agent = ChartGenerator(services)             │   │
│     │  analyzer_agent = DataAnalyzer(services)            │   │
│     │  chat_agent = GeneralChat(services)                 │   │
│     └────────────────────────────────────────────────────┘   │
│                                                                │
│  4. Register in Registry                                      │
│     ┌────────────────────────────────────────────────────┐   │
│     │  registry.register(chart_agent)                     │   │
│     │  registry.register(analyzer_agent)                  │   │
│     │  registry.register(chat_agent)                      │   │
│     └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

Agent Usage:

class ChartGenerator(BaseAgent):
    def __init__(self, services: AgentServices):
        super().__init__(services)
        # Services are injected and accessible

    async def execute(self, request: AgentRequest):
        # Use injected services
        file_data = await self.services.storage.load(request.files[0])

        # Access database
        async with self.services.db.get_session() as session:
            # Query database
            pass

        # Use cache
        cached = await self.services.cache.get(key)

        # Call LLM
        result = await self.services.llm.complete(messages)

        return response

Benefits:
✅ Testable: Inject mock services for testing
✅ Flexible: Swap implementations (Redis → Memory cache)
✅ Clean: No global state or imports
✅ Typed: Services have clear interfaces
```

---

### 8. Error Handling Flow

```
┌──────────────────────────────────────────────────────────────┐
│  User Request                                                 │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Executor (Framework)                                   │
│                                                                │
│  try:                                                          │
│      ┌──────────────────────────────────────────────┐        │
│      │ 1. Validation                                 │        │
│      │    - Check request format                     │        │
│      │    - Validate required fields                 │        │
│      └──────────┬────────────────────────────────────┘        │
│                 │ ValidationError?                            │
│                 ├─ Yes → Return 400 error                     │
│                 └─ No → Continue                              │
│                 │                                              │
│      ┌──────────▼────────────────────────────────────┐        │
│      │ 2. Agent Selection                             │        │
│      │    - Route to best agent                      │        │
│      │    - Check agent availability                 │        │
│      └──────────┬────────────────────────────────────┘        │
│                 │ NoAgentFound?                               │
│                 ├─ Yes → Return 404 error                     │
│                 └─ No → Continue                              │
│                 │                                              │
│      ┌──────────▼────────────────────────────────────┐        │
│      │ 3. Timeout Wrapper                             │        │
│      │    async with timeout(agent.timeout):         │        │
│      │        response = await agent.execute(req)    │        │
│      └──────────┬────────────────────────────────────┘        │
│                 │ TimeoutError?                               │
│                 ├─ Yes → Return 504 timeout error            │
│                 └─ No → Continue                              │
│                 │                                              │
│      ┌──────────▼────────────────────────────────────┐        │
│      │ 4. Agent Execution                             │        │
│      │    Agent-specific logic                       │        │
│      └──────────┬────────────────────────────────────┘        │
│                 │ AgentError?                                 │
│                 ├─ Yes → Log & format error response         │
│                 └─ No → Return success                        │
│                 │                                              │
│  except Exception as e:                                        │
│      ┌──────────▼────────────────────────────────────┐        │
│      │ 5. Error Handler                               │        │
│      │    - Log exception with context               │        │
│      │    - Track in monitoring                       │        │
│      │    - Return user-friendly error               │        │
│      └──────────┬────────────────────────────────────┘        │
│                 │                                              │
└─────────────────┼──────────────────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────────────────┐
│  Error Response to User                                       │
│  {                                                             │
│    "success": false,                                          │
│    "error": "Unable to process request",                      │
│    "error_type": "timeout",                                   │
│    "suggestion": "Try with a simpler query",                 │
│    "request_id": "abc-123"  // For support                   │
│  }                                                             │
└──────────────────────────────────────────────────────────────┘

Error Categories:

1. Client Errors (4xx)
   - 400 Bad Request: Invalid input
   - 404 Not Found: No suitable agent
   - 429 Rate Limit: Too many requests

2. Server Errors (5xx)
   - 500 Internal Error: Unexpected exception
   - 503 Service Unavailable: Agent pool exhausted
   - 504 Timeout: Request took too long

3. Agent Errors (handled gracefully)
   - File not found
   - API key missing
   - LLM rate limit
   - Data parsing error
```

---

## Summary

These diagrams illustrate the transformation from a tightly coupled, inconsistent architecture to a clean, modular, and extensible system. The new architecture provides:

1. **Clear separation of concerns** - Framework / Agents / API
2. **Dependency injection** - Services provided to agents
3. **Smart routing** - Multi-stage agent selection
4. **Flexible orchestration** - Sequential and parallel workflows
5. **Robust error handling** - Graceful failures at every layer
6. **Observable execution** - Clear data flow and metrics

The architecture is designed to scale from simple single-agent queries to complex multi-agent workflows while maintaining code simplicity and developer experience.