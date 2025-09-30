# Agent-Chat Architecture Quick Reference

**For:** Developers implementing the redesign
**Updated:** 2025-09-30

---

## TL;DR

Transform Agent-Chat from tightly coupled agents to a plug-and-play architecture where:
- Adding agents takes **5 minutes** (was 1+ hours)
- **No database imports** in agents (use injected services)
- **Declarative manifests** (no hardcoded properties)
- **90%+ test coverage** (easy with mock services)
- **Auto-discovery** (scan directories, no manual registration)

---

## Core Concepts

### 1. Dependency Injection

**Old (❌):**
```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Direct imports - bad!
        from core.database import get_db
        self.db = get_db
        self.api_key = os.getenv("API_KEY")
```

**New (✅):**
```python
class MyAgent(BaseAgent):
    def __init__(self, services: AgentServices):
        super().__init__(services)
        # Services injected - good!
        # Access via self.services.db, self.services.storage, etc.
```

---

### 2. Agent Structure

**Every agent has this structure:**
```
agents/my_agent/
├── __init__.py
├── agent.py           # Main agent class
├── manifest.yaml      # Configuration (replaces properties)
├── [helpers.py]       # Optional: Separated logic
└── tests/
    └── test_agent.py  # Unit tests with mocks
```

---

### 3. Manifest File

**Replaces hardcoded properties:**

```yaml
# agents/my_agent/manifest.yaml
agent_id: "my-agent"
name: "My Agent"
description: "Does something awesome"
version: "1.0.0"

capabilities:
  - data_analysis
  - visualization

priority: 5  # 1-10, higher = preferred in routing

keywords:
  - keyword1
  - keyword2

triggers:
  - "exact phrase to trigger"

requires_files: false
file_types: []

max_concurrent: 1
timeout_seconds: 300
```

---

### 4. Agent Implementation Template

```python
"""
agents/my_agent/agent.py
"""

from framework.agent_interface import (
    BaseAgent,
    AgentRequest,
    AgentResponse,
    AgentManifest,
    AgentServices
)


class MyAgent(BaseAgent):
    """
    My agent implementation.

    Services available:
    - self.services.db: Database access
    - self.services.storage: File operations
    - self.services.cache: Caching
    - self.services.llm: LLM API
    - self.services.config: Configuration
    """

    def __init__(self, services: AgentServices):
        super().__init__(services)
        # Initialize agent-specific components

    def _load_manifest(self) -> AgentManifest:
        """Load manifest from YAML file"""
        import yaml
        from pathlib import Path

        manifest_path = Path(__file__).parent / "manifest.yaml"
        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        return AgentManifest(**data)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Main execution logic.

        Framework handles:
        - Timeout management
        - Error catching
        - Metrics collection
        - Logging

        Agent only needs to:
        - Process request
        - Return response
        """
        try:
            # 1. Access services
            data = await self.services.storage.load_file(request.files[0])

            # 2. Do your logic
            result = await self._do_something(data)

            # 3. Return success response
            return AgentResponse(
                request_id=request.request_id,
                agent_id=self.manifest.agent_id,
                success=True,
                message="Result: ...",
                data={"result": result},
                confidence=0.9
            )

        except Exception as e:
            # Framework catches this, but you can handle specifically
            return AgentResponse(
                request_id=request.request_id,
                agent_id=self.manifest.agent_id,
                success=False,
                message=f"Error: {str(e)}",
                error=str(e)
            )

    async def validate(self, request: AgentRequest) -> bool:
        """
        Optional: Custom validation logic.

        Default: Checks keywords from manifest.
        Override: For custom validation.
        """
        # Your validation logic
        return True

    async def _do_something(self, data):
        """Your agent-specific logic"""
        pass
```

---

## Service APIs

### Database Service

```python
# Get a database session
async with self.services.db.get_session() as session:
    # Query
    result = await session.execute(
        select(Model).where(Model.id == some_id)
    )
    record = result.scalar_one_or_none()

    # Insert
    new_record = Model(data="value")
    session.add(new_record)
    await session.commit()
```

### Storage Service

```python
# Load file
file_data = await self.services.storage.load_file(file_id)
# Returns: bytes

# Get file info
info = await self.services.storage.get_file_info(file_id)
# Returns: {"extension": ".csv", "size": 12345, ...}

# Save file
new_file_id = await self.services.storage.save_file(
    "path/to/file.png",
    bytes_data
)
```

### Cache Service

```python
# Get cached value
value = await self.services.cache.get("key")

# Set cached value
await self.services.cache.set(
    "key",
    value,
    ttl=3600  # 1 hour
)

# Delete
await self.services.cache.delete("key")
```

### LLM Service

```python
# Get completion
response = await self.services.llm.complete(
    messages=[
        {"role": "system", "content": "You are..."},
        {"role": "user", "content": "Query"}
    ],
    model="gpt-4",
    temperature=0.7,
    max_tokens=500
)
# Returns: string
```

---

## Testing Pattern

```python
"""
agents/my_agent/tests/test_agent.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agents.my_agent.agent import MyAgent
from framework.agent_interface import AgentRequest, AgentServices


@pytest.fixture
def mock_services():
    """Create mock services for testing"""
    services = MagicMock(spec=AgentServices)

    # Mock database
    services.db = AsyncMock()

    # Mock storage
    services.storage = AsyncMock()
    services.storage.load_file = AsyncMock(return_value=b"test data")
    services.storage.get_file_info = AsyncMock(return_value={"extension": ".csv"})

    # Mock cache
    services.cache = AsyncMock()
    services.cache.get = AsyncMock(return_value=None)

    # Mock LLM
    services.llm = AsyncMock()
    services.llm.complete = AsyncMock(return_value="LLM response")

    # Config
    services.config = {}

    return services


@pytest.mark.asyncio
async def test_execute_success(mock_services):
    """Test successful execution"""
    # Arrange
    agent = MyAgent(mock_services)
    request = AgentRequest(
        query="Do something",
        files=["file-123"]
    )

    # Act
    response = await agent.execute(request)

    # Assert
    assert response.success is True
    assert response.agent_id == "my-agent"
    assert "result" in response.data

    # Verify service calls
    mock_services.storage.load_file.assert_called_once_with("file-123")


@pytest.mark.asyncio
async def test_execute_failure(mock_services):
    """Test execution handles errors"""
    # Arrange
    agent = MyAgent(mock_services)
    mock_services.storage.load_file = AsyncMock(side_effect=Exception("Error"))
    request = AgentRequest(query="Do something", files=["file-123"])

    # Act
    response = await agent.execute(request)

    # Assert
    assert response.success is False
    assert "Error" in response.message


@pytest.mark.asyncio
async def test_validation(mock_services):
    """Test validation logic"""
    # Arrange
    agent = MyAgent(mock_services)
    request = AgentRequest(query="keyword1 in query", files=[])

    # Act
    can_handle = await agent.validate(request)

    # Assert
    assert can_handle is True
```

---

## Common Patterns

### Pattern 1: File Processing Agent

```python
async def execute(self, request: AgentRequest) -> AgentResponse:
    # 1. Load file
    file_data = await self.services.storage.load_file(request.files[0])

    # 2. Parse file
    import pandas as pd
    df = pd.read_csv(BytesIO(file_data))

    # 3. Process
    result = self._analyze(df)

    # 4. Return
    return AgentResponse(
        request_id=request.request_id,
        agent_id=self.manifest.agent_id,
        success=True,
        message=f"Analyzed {len(df)} rows",
        data={"result": result}
    )
```

### Pattern 2: LLM-Powered Agent

```python
async def execute(self, request: AgentRequest) -> AgentResponse:
    # 1. Build prompt
    prompt = f"User asked: {request.query}\n\nProvide analysis."

    # 2. Get LLM response
    llm_response = await self.services.llm.complete(
        messages=[
            {"role": "system", "content": "You are an expert..."},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4"
    )

    # 3. Return
    return AgentResponse(
        request_id=request.request_id,
        agent_id=self.manifest.agent_id,
        success=True,
        message=llm_response
    )
```

### Pattern 3: Caching Agent

```python
async def execute(self, request: AgentRequest) -> AgentResponse:
    # 1. Check cache
    cache_key = f"result:{request.query}"
    cached = await self.services.cache.get(cache_key)

    if cached:
        return AgentResponse(
            request_id=request.request_id,
            agent_id=self.manifest.agent_id,
            success=True,
            message=cached["message"],
            data=cached["data"]
        )

    # 2. Compute result
    result = await self._compute_expensive_operation(request)

    # 3. Cache it
    await self.services.cache.set(
        cache_key,
        {"message": result.message, "data": result.data},
        ttl=3600
    )

    return result
```

---

## Router Configuration

The router automatically scores agents based on manifest. You can influence routing:

### High Priority Agent

```yaml
priority: 9  # 1-10, higher = preferred
keywords:
  - specific
  - unique
  - terms
triggers:
  - "exact phrase that strongly indicates this agent"
```

### Fallback Agent

```yaml
priority: 1  # Low priority
keywords: []  # No keywords = catches unmatched queries
```

### File-Required Agent

```yaml
requires_files: true
file_types:
  - csv
  - xlsx
# Router will penalize if files missing
```

---

## Migration Checklist

Migrating an existing agent? Follow these steps:

- [ ] Create agent directory: `agents/my_agent/`
- [ ] Create `manifest.yaml` from old properties
- [ ] Refactor `agent.py`:
  - [ ] Add `services` parameter to `__init__`
  - [ ] Replace direct imports with `self.services.*`
  - [ ] Remove hardcoded properties (use manifest)
  - [ ] Simplify `execute()` (framework handles errors)
- [ ] Separate concerns (extract helper classes)
- [ ] Write tests with mock services
- [ ] Verify API responses unchanged
- [ ] Update registration in `main.py`
- [ ] Remove old agent file

---

## Common Mistakes

### ❌ Don't: Import database directly
```python
from core.database import get_db
async for db in get_db():
    # Bad - tight coupling
```

### ✅ Do: Use injected service
```python
async with self.services.db.get_session() as session:
    # Good - decoupled
```

---

### ❌ Don't: Hardcode file paths
```python
file_path = f"uploads/{file_id}.csv"
with open(file_path) as f:
    # Bad - not portable
```

### ✅ Do: Use storage service
```python
file_data = await self.services.storage.load_file(file_id)
# Good - abstracted
```

---

### ❌ Don't: Define properties manually
```python
@property
def agent_id(self) -> str:
    return "my-agent"

@property
def keywords(self) -> List[str]:
    return ["keyword1", "keyword2"]
# Bad - boilerplate
```

### ✅ Do: Use manifest
```yaml
# manifest.yaml
agent_id: "my-agent"
keywords:
  - keyword1
  - keyword2
# Good - declarative
```

---

## Debug Commands

```bash
# Run specific agent test
pytest agents/my_agent/tests/ -v

# Test with coverage
pytest agents/my_agent/tests/ --cov=agents.my_agent --cov-report=html

# Test all agents
pytest agents/ -v

# Check types
mypy agents/my_agent/

# Format code
black agents/my_agent/
isort agents/my_agent/

# Lint
flake8 agents/my_agent/
```

---

## Quick Commands

```bash
# Create new agent structure
mkdir -p agents/my_agent/tests
touch agents/my_agent/{__init__.py,agent.py,manifest.yaml}
touch agents/my_agent/tests/{__init__.py,test_agent.py}

# Run app in dev mode
uvicorn backend.main:app --reload

# Run tests
pytest -v

# Check coverage
pytest --cov=backend --cov-report=html
open htmlcov/index.html
```

---

## Framework APIs Reference

### AgentRequest
```python
class AgentRequest:
    request_id: str          # Unique request ID
    query: str               # User query
    context: Dict[str, Any]  # Additional context
    files: List[str]         # File IDs
    session_id: str | None   # Session ID
    user_id: str | None      # User ID
```

### AgentResponse
```python
class AgentResponse:
    request_id: str          # Same as request
    agent_id: str            # Your agent ID
    success: bool            # Success/failure
    message: str             # Markdown formatted message
    data: Dict[str, Any]     # Structured data
    confidence: float        # 0.0-1.0
    suggestions: List[str]   # Follow-up suggestions
    error: str | None        # Error message if failed
```

### AgentManifest
```python
class AgentManifest:
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    keywords: List[str]
    triggers: List[str]
    requires_files: bool
    file_types: List[str]
    priority: int            # 1-10
    max_concurrent: int
    timeout_seconds: int
```

---

## Need Help?

1. **Read the docs:**
   - [Architecture Plan](./ARCHITECTURE_REDESIGN_PLAN.md)
   - [Architecture Diagrams](./ARCHITECTURE_DIAGRAMS.md)
   - [Migration Example](./MIGRATION_EXAMPLE.md)

2. **Look at examples:**
   - See migrated agents in `agents/` directory
   - Check tests for patterns

3. **Ask questions:**
   - Create GitHub issue
   - Ask tech lead
   - Check code comments

---

**Keep this reference handy while implementing the redesign!**

---

**Last Updated:** 2025-09-30
**Version:** 1.0