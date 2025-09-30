# Agent-Chat Architecture Redesign Plan
## World-Class Multi-Agent Chat System

**Version:** 2.0
**Date:** 2025-09-30
**Status:** Design Phase

---

## Executive Summary

This document outlines a comprehensive architectural redesign of Agent-Chat from first principles, transforming it into a world-class multi-agent chat system. The redesign focuses on **simplicity**, **consistency**, **extensibility**, and **developer experience**.

### Key Goals
- **Plug-and-play agent architecture** - Add new agents in minutes, not hours
- **Consistent agent interface** - All agents follow the same patterns
- **Clean separation of concerns** - Framework, agents, and application are decoupled
- **Observable and debuggable** - Clear insight into agent behavior
- **Production-ready** - Scalable, maintainable, and testable

---

## Current State Analysis

### Anti-Patterns Identified

#### 1. **Inconsistent Agent Implementations**
```python
# Current: Multiple agent styles
- BP003IntelligentAgent: Query classification approach
- AgentOrchestrator: Coordination with AgentPool
- GeneralChatAgent: Simple API wrapper
- AIChartGenerator: AI-powered code generation
```

**Issue:** Each agent has its own approach to initialization, execution, and response formatting.

#### 2. **Tight Coupling**
```python
# orchestrator.py imports specific agents directly
from .bp003_intelligent import QueryType, BP003IntelligentAgent
from .chart_generator import ChartGenerator
from .ai_chart_generator import AIChartGenerator
```

**Issue:** Orchestrator knows implementation details of specific agents, making it hard to add/remove agents.

#### 3. **Mixed Responsibilities**
```python
# AgentOrchestrator does too much:
- Query classification (should be separate)
- Agent selection (should be registry's job)
- Execution coordination (correct responsibility)
- UI streaming (should be separate layer)
```

#### 4. **Database Import Issues**
```python
# Agents importing database directly
from core.database import get_db  # Creates circular dependencies
```

**Issue:** Database session management scattered across codebase.

#### 5. **Code Duplication**
- Multiple chart generators (regular + AI)
- Similar validation logic in multiple agents
- Repeated file loading code
- Duplicated error handling patterns

#### 6. **Unclear Agent Discovery**
```python
# Registry uses keyword matching with hardcoded scores
if word in ["anomaly", "outlier", "detection", "unusual", "som"]:
    scored_agents[agent_id] += 10.0  # Magic numbers
```

**Issue:** No declarative way to define agent capabilities and routing.

---

## Proposed Architecture

### 1. Core Principles

#### Single Responsibility
- **Agents**: Execute one specific task well
- **Registry**: Discover and manage agents
- **Router**: Select the right agent for a query
- **Orchestrator**: Coordinate multi-agent workflows
- **API Layer**: Handle HTTP/WebSocket communication

#### Open/Closed Principle
- System is open for extension (new agents) but closed for modification (framework stays stable)

#### Dependency Inversion
- Agents depend on interfaces, not concrete implementations
- Framework provides services via dependency injection

#### Convention Over Configuration
- Agent manifest files define capabilities
- Auto-discovery scans agent directories
- Sensible defaults with explicit overrides

---

### 2. New Agent Framework

#### Agent Interface (Simplified)

```python
"""
agents/core/interface.py
Simplified agent interface with clear contracts
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class AgentCapability(str, Enum):
    """Standard agent capabilities for discovery"""
    DATA_ANALYSIS = "data_analysis"
    VISUALIZATION = "visualization"
    ANOMALY_DETECTION = "anomaly_detection"
    BRAND_ANALYSIS = "brand_analysis"
    GENERAL_CHAT = "general_chat"
    FILE_PROCESSING = "file_processing"
    CALCULATION = "calculation"
    REPORTING = "reporting"


class AgentRequest(BaseModel):
    """Standardized request to all agents"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field(..., description="User's natural language query")
    context: Dict[str, Any] = Field(default_factory=dict)
    files: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class AgentResponse(BaseModel):
    """Standardized response from all agents"""
    request_id: str
    agent_id: str
    success: bool
    message: str  # Markdown formatted response
    data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0


class AgentManifest(BaseModel):
    """Agent metadata for discovery and routing"""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability]
    priority: int = Field(default=5, ge=1, le=10)  # 10 = highest priority

    # Routing hints
    keywords: List[str] = Field(default_factory=list)
    triggers: List[str] = Field(default_factory=list)
    requires_files: bool = False
    file_types: List[str] = Field(default_factory=list)

    # Configuration
    max_concurrent: int = 1
    timeout_seconds: int = 300
    requires_auth: bool = False

    # Dependencies
    dependencies: List[str] = Field(default_factory=list)
    llm_provider: Optional[str] = None


class BaseAgent(ABC):
    """
    Base agent interface - all agents inherit from this.

    Philosophy: Convention over configuration
    - Agents are self-contained
    - Manifest declares capabilities
    - Framework handles common concerns (logging, metrics, error handling)
    """

    def __init__(self, services: 'AgentServices'):
        """
        Initialize agent with injected services.

        Args:
            services: Framework-provided services (DB, storage, cache, etc.)
        """
        self.services = services
        self._manifest: Optional[AgentManifest] = None

    @property
    def manifest(self) -> AgentManifest:
        """Return agent manifest (lazy loaded)"""
        if not self._manifest:
            self._manifest = self._load_manifest()
        return self._manifest

    @abstractmethod
    def _load_manifest(self) -> AgentManifest:
        """Load agent manifest - implement in subclass"""
        pass

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Execute agent logic - implement in subclass.

        Framework will handle:
        - Request validation
        - Timeout management
        - Error catching and formatting
        - Metrics collection
        - Logging

        Agent only needs to:
        - Process the request
        - Return a response
        """
        pass

    async def validate(self, request: AgentRequest) -> bool:
        """
        Optional: Validate if this agent can handle the request.

        Default: Check if keywords match query
        Override: Custom validation logic
        """
        query_lower = request.query.lower()
        return any(keyword in query_lower for keyword in self.manifest.keywords)

    async def stream(self, request: AgentRequest) -> AsyncIterator[Dict[str, Any]]:
        """
        Optional: Stream partial results for real-time UI updates.

        Default: Execute and yield final result
        Override: Yield intermediate results
        """
        response = await self.execute(request)
        yield {
            "type": "final",
            "response": response.model_dump()
        }
```

#### Agent Services (Dependency Injection)

```python
"""
agents/core/services.py
Services injected into agents by framework
"""

from typing import Protocol, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseService(Protocol):
    """Database access abstraction"""
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        ...


class StorageService(Protocol):
    """File storage abstraction"""
    async def load_file(self, file_id: str) -> bytes:
        """Load file contents"""
        ...

    async def save_file(self, file_id: str, content: bytes) -> str:
        """Save file and return path"""
        ...


class CacheService(Protocol):
    """Caching abstraction"""
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        ...

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set cached value"""
        ...


class LLMService(Protocol):
    """LLM provider abstraction"""
    async def complete(
        self,
        messages: list[dict],
        model: str = "gpt-4",
        temperature: float = 0.7
    ) -> str:
        """Get LLM completion"""
        ...


class AgentServices:
    """Container for all injected services"""

    def __init__(
        self,
        db: DatabaseService,
        storage: StorageService,
        cache: CacheService,
        llm: LLMService,
        config: dict[str, Any]
    ):
        self.db = db
        self.storage = storage
        self.cache = cache
        self.llm = llm
        self.config = config
```

---

### 3. Repository Structure

```
Agent-Chat/
├── backend/
│   ├── framework/                    # Core framework (stable)
│   │   ├── __init__.py
│   │   ├── agent_interface.py        # BaseAgent, AgentRequest, AgentResponse
│   │   ├── agent_services.py         # Service interfaces and implementations
│   │   ├── agent_registry.py         # Agent discovery and management
│   │   ├── agent_router.py           # Smart routing logic
│   │   ├── agent_executor.py         # Execution with metrics/timeout
│   │   ├── agent_orchestrator.py     # Multi-agent coordination
│   │   └── decorators.py             # Helpers (@agent, @tool, etc.)
│   │
│   ├── agents/                       # Agent implementations (extensible)
│   │   ├── __init__.py
│   │   ├── general_chat/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py              # GeneralChatAgent implementation
│   │   │   ├── manifest.yaml         # Agent metadata
│   │   │   ├── prompts.py            # Prompt templates
│   │   │   └── tests/
│   │   │       └── test_agent.py
│   │   │
│   │   ├── chart_generator/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py              # Chart generation logic
│   │   │   ├── manifest.yaml
│   │   │   ├── templates/            # Chart templates
│   │   │   └── tests/
│   │   │
│   │   ├── anomaly_detector/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── manifest.yaml
│   │   │   ├── models.py             # Detection models
│   │   │   └── tests/
│   │   │
│   │   └── brand_analyzer/
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── manifest.yaml
│   │       └── tests/
│   │
│   ├── api/                          # API layer (stable)
│   │   ├── __init__.py
│   │   ├── chat.py                   # Chat endpoints
│   │   ├── agents.py                 # Agent management endpoints
│   │   ├── files.py                  # File management
│   │   └── websocket.py              # Real-time streaming
│   │
│   ├── core/                         # Application core (stable)
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration
│   │   ├── database.py               # Database setup
│   │   ├── auth.py                   # Authentication
│   │   └── middleware.py             # Middleware
│   │
│   ├── models/                       # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   └── files.py
│   │
│   ├── services/                     # Business services
│   │   ├── __init__.py
│   │   ├── storage.py
│   │   ├── cache.py
│   │   └── llm.py
│   │
│   ├── tests/                        # Integration tests
│   │   ├── test_framework.py
│   │   ├── test_routing.py
│   │   └── test_orchestration.py
│   │
│   └── main.py                       # Application entry point
│
└── frontend/                         # React frontend (existing)
    └── ...
```

#### Key Structure Benefits:

1. **Framework Stability**: Core framework rarely changes
2. **Agent Isolation**: Each agent is self-contained with tests
3. **Clear Boundaries**: Framework vs agents vs application
4. **Easy Testing**: Test agents independently
5. **Auto-discovery**: Framework scans `agents/` directory

---

### 4. Agent Manifest Format

Each agent has a `manifest.yaml` that declares its capabilities:

```yaml
# agents/chart_generator/manifest.yaml

agent_id: "chart-generator"
name: "Chart Generator"
description: "Creates beautiful, interactive charts from data using AI"
version: "2.0.0"

capabilities:
  - visualization
  - data_analysis

priority: 8  # High priority for chart requests

# Routing hints
keywords:
  - chart
  - graph
  - plot
  - visualize
  - visualization
  - trend

triggers:
  - "create a chart"
  - "show me a graph"
  - "visualize"

requires_files: true
file_types:
  - csv
  - xlsx
  - json

# Configuration
max_concurrent: 3
timeout_seconds: 120
requires_auth: false

# Dependencies
dependencies:
  - pandas
  - plotly
  - matplotlib

llm_provider: "openai"  # Uses OpenAI for intelligent chart selection

# Custom configuration
config:
  default_chart_type: "auto"
  max_data_points: 10000
  enable_interactive: true
```

---

### 5. Smart Routing System

#### Router Architecture

```python
"""
framework/agent_router.py
Intelligent agent selection based on query and context
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class RoutingScore:
    """Score for agent selection"""
    agent_id: str
    score: float
    reasons: List[str]
    confidence: float


class AgentRouter:
    """
    Smart router that selects the best agent(s) for a query.

    Routing strategy:
    1. Keyword matching (fast, simple)
    2. Trigger phrase detection (explicit requests)
    3. Capability matching (query classification)
    4. ML-based ranking (optional, future)
    """

    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry

    async def route(
        self,
        query: str,
        context: Dict[str, Any],
        top_k: int = 1
    ) -> List[RoutingScore]:
        """
        Route query to best agent(s).

        Returns:
            List of RoutingScores ordered by relevance
        """
        scores = []

        for agent_id, agent in self.registry.agents.items():
            score = await self._score_agent(agent, query, context)
            if score.score > 0:
                scores.append(score)

        # Sort by score (descending) and priority (descending)
        scores.sort(key=lambda s: (s.score, self.registry.get_priority(s.agent_id)), reverse=True)

        return scores[:top_k]

    async def _score_agent(
        self,
        agent: BaseAgent,
        query: str,
        context: Dict[str, Any]
    ) -> RoutingScore:
        """Score an agent for a given query"""
        query_lower = query.lower()
        manifest = agent.manifest
        score = 0.0
        reasons = []

        # 1. Trigger phrase matching (exact matches = high score)
        for trigger in manifest.triggers:
            if trigger.lower() in query_lower:
                score += 20.0
                reasons.append(f"Trigger match: '{trigger}'")

        # 2. Keyword matching (keyword frequency)
        keyword_matches = sum(1 for kw in manifest.keywords if kw.lower() in query_lower)
        if keyword_matches > 0:
            score += keyword_matches * 2.0
            reasons.append(f"{keyword_matches} keyword matches")

        # 3. File requirement matching
        has_files = len(context.get('files', [])) > 0
        if manifest.requires_files and not has_files:
            score = max(0, score - 10.0)  # Penalize if files required but missing
            reasons.append("Files required but not provided")
        elif manifest.requires_files and has_files:
            score += 5.0
            reasons.append("Files available as required")

        # 4. Agent-specific validation
        try:
            request = AgentRequest(query=query, context=context)
            if await agent.validate(request):
                score += 3.0
                reasons.append("Agent validation passed")
        except Exception:
            pass

        # 5. Apply priority multiplier
        priority_boost = manifest.priority / 10.0  # Normalize to 0.1-1.0
        score *= priority_boost

        # Calculate confidence (0-1)
        confidence = min(1.0, score / 30.0)  # 30+ score = high confidence

        return RoutingScore(
            agent_id=manifest.agent_id,
            score=score,
            reasons=reasons,
            confidence=confidence
        )
```

#### Fallback Strategy

```python
class RouterWithFallback:
    """Router with intelligent fallback"""

    def __init__(self, router: AgentRouter, fallback_agent_id: str = "general-chat"):
        self.router = router
        self.fallback_agent_id = fallback_agent_id

    async def route_with_fallback(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Route with fallback to general chat"""
        scores = await self.router.route(query, context, top_k=1)

        if not scores or scores[0].confidence < 0.3:
            # Low confidence, use fallback
            return self.fallback_agent_id

        return scores[0].agent_id
```

---

### 6. Multi-Agent Orchestration

```python
"""
framework/agent_orchestrator.py
Coordinate multiple agents for complex workflows
"""

from typing import List, Dict, Any, AsyncIterator
from dataclasses import dataclass
import asyncio


@dataclass
class AgentTask:
    """Task for an agent in orchestration"""
    agent_id: str
    request: AgentRequest
    depends_on: List[str] = None  # Task IDs this depends on
    task_id: str = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())


@dataclass
class OrchestrationResult:
    """Result from orchestrated workflow"""
    success: bool
    results: Dict[str, AgentResponse]
    execution_order: List[str]
    total_time_ms: int


class AgentOrchestrator:
    """
    Orchestrate multiple agents in workflows.

    Supports:
    - Sequential execution (A -> B -> C)
    - Parallel execution (A + B + C)
    - DAG-based workflows (A -> B, A -> C, B+C -> D)
    """

    def __init__(self, registry: 'AgentRegistry'):
        self.registry = registry

    async def execute_workflow(
        self,
        tasks: List[AgentTask],
        mode: str = "auto"  # auto, sequential, parallel
    ) -> OrchestrationResult:
        """
        Execute workflow of multiple agents.

        Args:
            tasks: List of agent tasks to execute
            mode: Execution mode (auto detects based on dependencies)
        """
        start_time = time.time()
        results = {}
        execution_order = []

        if mode == "sequential" or self._has_dependencies(tasks):
            # Execute in order, passing results between agents
            for task in self._sort_by_dependencies(tasks):
                response = await self._execute_task(task, results)
                results[task.task_id] = response
                execution_order.append(task.agent_id)
        else:
            # Execute in parallel
            task_futures = [
                self._execute_task(task, results)
                for task in tasks
            ]
            responses = await asyncio.gather(*task_futures, return_exceptions=True)

            for task, response in zip(tasks, responses):
                results[task.task_id] = response
                execution_order.append(task.agent_id)

        total_time_ms = int((time.time() - start_time) * 1000)

        return OrchestrationResult(
            success=all(r.success for r in results.values() if isinstance(r, AgentResponse)),
            results=results,
            execution_order=execution_order,
            total_time_ms=total_time_ms
        )

    async def execute_streaming(
        self,
        tasks: List[AgentTask]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute workflow with streaming updates"""
        for task in tasks:
            # Stream start
            yield {
                "type": "task_start",
                "agent_id": task.agent_id,
                "task_id": task.task_id
            }

            # Stream progress
            agent = self.registry.get(task.agent_id)
            async for update in agent.stream(task.request):
                yield {
                    "type": "task_update",
                    "agent_id": task.agent_id,
                    "task_id": task.task_id,
                    "data": update
                }

            # Stream completion
            yield {
                "type": "task_complete",
                "agent_id": task.agent_id,
                "task_id": task.task_id
            }
```

---

### 7. API Design

#### RESTful Endpoints

```python
"""
api/chat.py
Clean REST API for chat functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/api/v1")


@router.post("/chat")
async def send_message(
    request: ChatRequest,
    services: AgentServices = Depends(get_services)
):
    """
    Send a chat message (auto-routes to best agent).

    Request:
        {
            "message": "Create a chart showing sales trends",
            "session_id": "optional-uuid",
            "context": {},
            "files": ["file-id-1", "file-id-2"]
        }

    Response:
        {
            "message": "Chart created successfully!",
            "agent_used": "chart-generator",
            "confidence": 0.95,
            "data": {...},
            "suggestions": [...]
        }
    """
    # Route to best agent
    router = AgentRouter(agent_registry)
    agent_id = await router.route_with_fallback(request.message, request.context)

    # Execute agent
    agent = agent_registry.get(agent_id)
    agent_request = AgentRequest(
        query=request.message,
        context=request.context,
        files=request.files,
        session_id=request.session_id
    )

    response = await agent.execute(agent_request)

    return {
        "message": response.message,
        "agent_used": response.agent_id,
        "confidence": response.confidence,
        "data": response.data,
        "suggestions": response.suggestions
    }


@router.post("/chat/multi-agent")
async def multi_agent_query(
    request: ChatRequest,
    max_agents: int = 3
):
    """
    Query multiple agents in parallel for comprehensive analysis.
    """
    router = AgentRouter(agent_registry)
    agent_scores = await router.route(request.message, request.context, top_k=max_agents)

    # Create tasks
    tasks = [
        AgentTask(
            agent_id=score.agent_id,
            request=AgentRequest(
                query=request.message,
                context=request.context,
                files=request.files
            )
        )
        for score in agent_scores
    ]

    # Execute in parallel
    orchestrator = AgentOrchestrator(agent_registry)
    result = await orchestrator.execute_workflow(tasks, mode="parallel")

    return {
        "results": [r.model_dump() for r in result.results.values()],
        "execution_time_ms": result.total_time_ms
    }


@router.get("/agents")
async def list_agents():
    """List all available agents with their capabilities."""
    return {
        "agents": [
            {
                "agent_id": agent.manifest.agent_id,
                "name": agent.manifest.name,
                "description": agent.manifest.description,
                "capabilities": agent.manifest.capabilities,
                "keywords": agent.manifest.keywords
            }
            for agent in agent_registry.list()
        ]
    }
```

#### WebSocket for Streaming

```python
"""
api/websocket.py
WebSocket endpoint for real-time streaming
"""

from fastapi import WebSocket, WebSocketDisconnect
import json


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket for real-time chat with streaming updates.

    Client sends:
        {
            "type": "message",
            "data": {
                "message": "Create a chart",
                "session_id": "uuid",
                "files": []
            }
        }

    Server streams:
        {"type": "routing", "agent": "chart-generator"}
        {"type": "progress", "status": "analyzing"}
        {"type": "partial", "content": "Creating chart..."}
        {"type": "complete", "response": {...}}
    """
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            if data["type"] == "message":
                msg = data["data"]

                # Route
                router = AgentRouter(agent_registry)
                agent_id = await router.route_with_fallback(msg["message"], {})

                await websocket.send_json({
                    "type": "routing",
                    "agent": agent_id
                })

                # Stream execution
                agent = agent_registry.get(agent_id)
                request = AgentRequest(
                    query=msg["message"],
                    session_id=msg.get("session_id"),
                    files=msg.get("files", [])
                )

                async for update in agent.stream(request):
                    await websocket.send_json({
                        "type": "update",
                        "data": update
                    })

    except WebSocketDisconnect:
        print("Client disconnected")
```

---

### 8. Developer Experience

#### Adding a New Agent (Step-by-Step)

**Goal:** Add a new agent in 5 minutes or less.

```bash
# 1. Create agent directory
mkdir -p backend/agents/my_new_agent
cd backend/agents/my_new_agent

# 2. Create files
touch __init__.py agent.py manifest.yaml tests/test_agent.py
```

```python
# 3. Write agent.py
"""
agents/my_new_agent/agent.py
My new agent implementation
"""

from framework.agent_interface import BaseAgent, AgentRequest, AgentResponse, AgentManifest


class MyNewAgent(BaseAgent):
    """My new agent that does something awesome"""

    def _load_manifest(self) -> AgentManifest:
        """Load manifest from YAML file"""
        return AgentManifest(
            agent_id="my-new-agent",
            name="My New Agent",
            description="Does something awesome",
            version="1.0.0",
            capabilities=["data_analysis"],
            keywords=["awesome", "new"],
            priority=5
        )

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute agent logic"""
        # Your logic here
        result = await self._do_something_awesome(request.query)

        return AgentResponse(
            request_id=request.request_id,
            agent_id=self.manifest.agent_id,
            success=True,
            message=f"Result: {result}",
            confidence=0.9
        )

    async def _do_something_awesome(self, query: str) -> str:
        """Agent-specific logic"""
        # Use injected services
        cached = await self.services.cache.get(f"result:{query}")
        if cached:
            return cached

        # Do work
        result = f"Awesome result for: {query}"

        # Cache it
        await self.services.cache.set(f"result:{query}", result)

        return result
```

```yaml
# 4. Write manifest.yaml
agent_id: "my-new-agent"
name: "My New Agent"
description: "Does something awesome"
version: "1.0.0"

capabilities:
  - data_analysis

priority: 5

keywords:
  - awesome
  - new
  - cool

triggers:
  - "do something awesome"

requires_files: false
```

```python
# 5. Write test
"""
agents/my_new_agent/tests/test_agent.py
"""

import pytest
from agents.my_new_agent.agent import MyNewAgent
from framework.agent_interface import AgentRequest


@pytest.mark.asyncio
async def test_my_new_agent(mock_services):
    agent = MyNewAgent(mock_services)

    request = AgentRequest(query="do something awesome")
    response = await agent.execute(request)

    assert response.success
    assert "awesome" in response.message.lower()
```

```python
# 6. Register in main.py (auto-discovery in future)
from agents.my_new_agent.agent import MyNewAgent

# In startup
agent_registry.register(MyNewAgent(services))
```

**Done!** Agent is now discoverable and usable.

---

### 9. Technology Recommendations

#### LangChain/LangGraph Assessment

**Should we use LangChain/LangGraph?**

| Aspect | LangChain/LangGraph | Custom Framework | Recommendation |
|--------|---------------------|------------------|----------------|
| **Pros** | - Built-in patterns<br>- Tool calling<br>- Chains<br>- Community support | - Full control<br>- Lightweight<br>- No vendor lock-in<br>- Easier debugging | **Custom Framework** |
| **Cons** | - Heavy dependency<br>- Abstraction complexity<br>- Lock-in<br>- Overkill for use case | - Build from scratch<br>- Maintain framework | (for now) |
| **Complexity** | High | Low-Medium | **Low-Medium** |
| **Performance** | Medium | High | **High** |
| **Learning Curve** | Steep | Gentle | **Gentle** |

**Decision: Custom Framework** (with LangChain integration option)

**Rationale:**
1. **Current codebase** already has a good foundation (BaseAgent)
2. **Use case** is specific - not generic LLM workflows
3. **Control** over agent lifecycle and orchestration is critical
4. **Performance** matters - lightweight is better
5. **Future option**: Can integrate LangChain tools as agents later

**Hybrid Approach:**
- Custom framework for agent lifecycle
- Use LangChain tools/utilities where beneficial:
  - `LLMChain` for prompt management
  - Tool abstractions for external APIs
  - Vector stores for context retrieval

```python
# Example: Using LangChain tools in custom agent
from langchain.tools import Tool
from framework.agent_interface import BaseAgent

class HybridAgent(BaseAgent):
    """Agent that uses LangChain tools"""

    def __init__(self, services):
        super().__init__(services)
        # Use LangChain tool
        self.search_tool = Tool.from_function(
            func=self._search,
            name="search",
            description="Search for information"
        )

    async def execute(self, request: AgentRequest) -> AgentResponse:
        # Use tool
        result = await self.search_tool.arun(request.query)
        return AgentResponse(...)
```

---

### 10. Implementation Phases

#### Phase 1: Foundation (Weeks 1-2)

**Goal:** Build stable framework without breaking existing functionality.

**Deliverables:**
1. New `framework/` directory with core interfaces
2. `BaseAgent` v2 with simplified interface
3. `AgentServices` for dependency injection
4. `AgentRegistry` with manifest support
5. `AgentRouter` with scoring system
6. Unit tests for framework

**Migration:**
- Keep existing agents working
- Add adapters for backward compatibility
- No frontend changes

**Success Metrics:**
- All existing tests pass
- Framework tests at 90%+ coverage
- Zero regressions

#### Phase 2: Agent Migration (Weeks 3-4)

**Goal:** Migrate existing agents to new framework.

**Deliverables:**
1. Migrate `GeneralChatAgent` (simplest)
2. Migrate `AIChartGenerator`
3. Migrate `BP004AnomalyDetectionAgent`
4. Migrate `AgentOrchestrator`
5. Remove old base classes

**Process:**
- Create manifest.yaml for each agent
- Refactor to use new BaseAgent
- Update tests
- Verify functionality

**Success Metrics:**
- All 4 agents migrated
- Tests passing
- API responses unchanged

#### Phase 3: Enhanced Features (Weeks 5-6)

**Goal:** Add new capabilities enabled by clean architecture.

**Deliverables:**
1. Auto-discovery (scan `agents/` directory)
2. Agent hot-reload (add agents without restart)
3. Advanced routing (ML-based scoring)
4. Workflow builder (GUI for multi-agent workflows)
5. Agent marketplace (install agents from registry)

**Success Metrics:**
- Add new agent without code restart
- Routing accuracy >90%
- Workflow builder functional

#### Phase 4: Production Hardening (Weeks 7-8)

**Goal:** Production-ready deployment.

**Deliverables:**
1. Performance optimization (caching, connection pooling)
2. Monitoring and metrics (Prometheus, Grafana)
3. Error tracking (Sentry)
4. Load testing (handle 100+ concurrent requests)
5. Documentation (API docs, agent development guide)

**Success Metrics:**
- <100ms p50 latency
- >99.9% uptime
- Complete API documentation

---

### 11. Migration Strategy

#### Backward Compatibility

```python
"""
framework/adapters.py
Adapters for backward compatibility during migration
"""

from typing import Any
from agents.base import BaseAgent as OldBaseAgent
from framework.agent_interface import BaseAgent as NewBaseAgent


class LegacyAgentAdapter(NewBaseAgent):
    """Adapter to run old agents in new framework"""

    def __init__(self, old_agent: OldBaseAgent, services: AgentServices):
        super().__init__(services)
        self.old_agent = old_agent

    def _load_manifest(self) -> AgentManifest:
        """Generate manifest from old agent"""
        return AgentManifest(
            agent_id=self.old_agent.agent_id,
            name=self.old_agent.name,
            description=self.old_agent.description,
            version=self.old_agent.version,
            capabilities=self.old_agent.capabilities,
            keywords=self.old_agent.keywords,
            requires_files=len(self.old_agent.required_files) > 0
        )

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Convert request, execute old agent, convert response"""
        old_request = self._convert_request(request)
        old_response = await self.old_agent.execute(old_request)
        return self._convert_response(old_response)
```

#### Gradual Rollout

1. **Week 1-2:** Framework in parallel with old system
2. **Week 3-4:** Migrate agents one-by-one
3. **Week 5-6:** All new features use new framework
4. **Week 7:** Remove old framework
5. **Week 8:** Cleanup and documentation

#### Rollback Plan

If issues arise:
1. Use feature flags to switch between old/new agents
2. Keep old code for 2 releases
3. Database schema is backward compatible

---

### 12. State and Memory

#### Conversation State

```python
"""
framework/state_manager.py
Manage conversation state across agent calls
"""

from typing import Dict, Any, Optional


class ConversationState:
    """State for a conversation session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_interaction(self, query: str, response: AgentResponse):
        """Add interaction to history"""
        self.history.append({
            "query": query,
            "response": response.message,
            "agent": response.agent_id,
            "timestamp": datetime.utcnow()
        })

    def get_context(self, key: str) -> Optional[Any]:
        """Get context value"""
        return self.context.get(key)

    def set_context(self, key: str, value: Any):
        """Set context value"""
        self.context[key] = value

    def get_recent_history(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.history[-n:]


class StateManager:
    """Manage state for all sessions"""

    def __init__(self, cache: CacheService):
        self.cache = cache
        self.sessions: Dict[str, ConversationState] = {}

    async def get_session(self, session_id: str) -> ConversationState:
        """Get or create session state"""
        if session_id not in self.sessions:
            # Try to load from cache
            cached = await self.cache.get(f"session:{session_id}")
            if cached:
                self.sessions[session_id] = cached
            else:
                self.sessions[session_id] = ConversationState(session_id)

        return self.sessions[session_id]

    async def save_session(self, session_id: str):
        """Save session to cache"""
        if session_id in self.sessions:
            await self.cache.set(
                f"session:{session_id}",
                self.sessions[session_id],
                ttl=3600  # 1 hour
            )
```

#### Agent Memory

```python
"""
framework/memory.py
Agent memory for learning and context
"""

class AgentMemory:
    """Memory system for agents"""

    def __init__(self, agent_id: str, services: AgentServices):
        self.agent_id = agent_id
        self.services = services

    async def remember(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in agent memory"""
        memory_key = f"memory:{self.agent_id}:{key}"
        await self.services.cache.set(memory_key, value, ttl=ttl or 86400)

    async def recall(self, key: str) -> Optional[Any]:
        """Retrieve value from agent memory"""
        memory_key = f"memory:{self.agent_id}:{key}"
        return await self.services.cache.get(memory_key)

    async def forget(self, key: str):
        """Delete value from memory"""
        memory_key = f"memory:{self.agent_id}:{key}"
        await self.services.cache.delete(memory_key)
```

---

### 13. Testing Strategy

#### Unit Tests (Framework)

```python
"""
tests/framework/test_agent_router.py
"""

import pytest
from framework.agent_router import AgentRouter
from framework.agent_interface import AgentManifest


@pytest.mark.asyncio
async def test_router_keyword_matching():
    """Test that router matches keywords correctly"""
    router = AgentRouter(mock_registry)

    scores = await router.route("create a chart", {}, top_k=3)

    assert len(scores) > 0
    assert scores[0].agent_id == "chart-generator"
    assert scores[0].score > 10.0


@pytest.mark.asyncio
async def test_router_trigger_matching():
    """Test that trigger phrases have high priority"""
    router = AgentRouter(mock_registry)

    scores = await router.route("do something awesome", {}, top_k=1)

    assert scores[0].agent_id == "my-new-agent"
    assert scores[0].confidence > 0.8


@pytest.mark.asyncio
async def test_router_fallback():
    """Test that unclear queries fall back to general chat"""
    router = RouterWithFallback(AgentRouter(mock_registry))

    agent_id = await router.route_with_fallback("random gibberish", {})

    assert agent_id == "general-chat"
```

#### Integration Tests (Agents)

```python
"""
tests/integration/test_chart_generation.py
"""

@pytest.mark.asyncio
async def test_end_to_end_chart_generation():
    """Test complete chart generation workflow"""
    # Upload file
    file_id = await upload_test_file("sales_data.csv")

    # Send request
    response = await api_client.post("/api/v1/chat", {
        "message": "Create a line chart of sales over time",
        "files": [file_id]
    })

    # Verify response
    assert response.status_code == 200
    assert response.json()["agent_used"] == "chart-generator"
    assert "chart" in response.json()["data"]

    # Verify chart file exists
    chart_url = response.json()["data"]["chart"]["url"]
    chart_response = await api_client.get(chart_url)
    assert chart_response.status_code == 200
```

#### Load Tests

```python
"""
tests/load/test_concurrent_requests.py
"""

import asyncio
from locust import HttpUser, task, between


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def send_message(self):
        self.client.post("/api/v1/chat", json={
            "message": "What is the sales trend?"
        })


# Run: locust -f tests/load/test_concurrent_requests.py
# Target: 100+ concurrent users, <500ms p95 latency
```

---

### 14. Success Metrics

#### Code Quality

- **Agent Addition Time:** <5 minutes (from 1+ hour currently)
- **Test Coverage:** >90% (from ~60% currently)
- **Code Duplication:** <5% (from ~20% currently)
- **Cyclomatic Complexity:** <10 per function
- **Type Safety:** 100% type hints

#### Developer Velocity

- **New Agent Development:** 1 day (from 1 week)
- **Bug Fix Time:** <1 hour (from 4+ hours)
- **Onboarding Time:** 1 day (from 1 week)
- **Documentation Coverage:** 100%

#### System Reliability

- **Uptime:** >99.9%
- **Error Rate:** <0.1%
- **P50 Latency:** <100ms
- **P95 Latency:** <500ms
- **P99 Latency:** <1000ms

#### Business Metrics

- **Agent Success Rate:** >95% (correct agent selected)
- **User Satisfaction:** >4.5/5
- **Query Resolution:** >90% first try
- **Agent Utilization:** All agents used regularly

---

## Conclusion

This architectural redesign transforms Agent-Chat into a world-class multi-agent system with:

1. **Plug-and-play architecture** - Add agents in 5 minutes
2. **Consistent patterns** - All agents follow the same interface
3. **Smart routing** - Queries go to the right agent
4. **Clean code** - Separation of concerns, easy to maintain
5. **Production-ready** - Scalable, observable, testable

### Next Steps

1. **Review this plan** with the team
2. **Create GitHub issues** for each phase
3. **Set up project board** for tracking
4. **Start Phase 1** foundation work
5. **Weekly reviews** to track progress

### Key Decisions Required

- [ ] Approve new framework architecture
- [ ] Commit to 8-week timeline
- [ ] Assign developers to phases
- [ ] Set up CI/CD for new structure
- [ ] Plan database migration strategy

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** Claude (System Architecture Designer)