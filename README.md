# Agion-LangGraph - Agion AI LangGraph Multi-Agent Platform

A production-ready LangGraph-based multi-agent orchestration platform powered by GPT-5 via Requesty AI.

## 🚀 Features

### Core Capabilities
- **LangGraph 0.6.8** - State graph-based agent orchestration with supervisor routing
- **GPT-5 Integration** - All agents powered by `openai/gpt-5-chat-latest` via Requesty AI
- **Multi-Agent System** - Specialized agents for different tasks:
  - **Supervisor Agent** - Intelligent routing and task delegation
  - **Chart Agent** - Automated data visualization with deterministic chart generation
  - **General Agent** - Conversational AI for general queries

### Technical Stack
- **Backend**: Python 3.13 with FastAPI
- **Frontend**: React 19 with TypeScript
- **Database**: PostgreSQL with async SQLAlchemy
- **Storage**: Azure Blob Storage for files and charts
- **Deployment**: Azure Kubernetes Service (AKS)

### Enterprise Features
- 🔐 Password-protected access
- 📊 Chart generation with PNG output (no external CDN dependencies)
- 📁 File upload and management
- 💾 Persistent chart storage in Azure Blob
- 🎯 Deterministic AI responses (temperature=0.0, seed=42)
- 📈 Real-time agent execution tracking

## 📐 Architecture

```
User Query
    ↓
Supervisor Node (GPT-5)
    ├─→ Chart Agent (Data Visualization)
    ├─→ General Agent (Conversation)
    └─→ [Future agents...]
    ↓
Response with Metadata
```

### LangGraph Implementation

```python
from langgraph.graph import StateGraph
from langgraph_agents.nodes import supervisor_node, chart_agent_node, general_agent_node

# Create state graph
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("chart_agent", chart_agent_node)
graph.add_node("general_agent", general_agent_node)

# Route based on supervisor decision
graph.add_conditional_edges("supervisor", route_to_agent)
```

## 🛠️ Development Setup

### Prerequisites
- Python 3.13+
- Node.js 18+
- PostgreSQL 14+
- Azure Storage Account

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python init_database.py

# Run development server
python start_server.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with API URL

# Run development server
npm start
```

## 🚀 Production Deployment

### Docker Build

```bash
# Build backend
docker build -f Dockerfile.backend.prod -t agent-chat-backend:latest .

# Build frontend
docker build -f Dockerfile.frontend.prod -t agent-chat-frontend:latest .
```

### Azure Kubernetes Service

```bash
# Apply Kubernetes configurations
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get pods -n agion-airgb
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER_NAME=agent-chat

# Requesty AI (GPT-5)
REQUESTY_AI_API_KEY=your_requesty_api_key
REQUESTY_AI_API_BASE=https://api.requesty.ai/v1

# Authentication
ACCESS_PASSWORD=your_secure_password
```

#### Frontend (.env)
```bash
REACT_APP_API_URL=https://your-backend-url.com
REACT_APP_PASSWORD=your_secure_password
```

## 📊 Chart Agent Features

### Data Analysis
- Automatic detection of numeric, categorical, and date columns
- Intelligent chart type selection based on data structure
- Deterministic code generation for consistency

### Supported Chart Types
- **Line Charts** - Time series data
- **Bar Charts** - Categorical comparisons
- **Scatter Plots** - Correlations
- **Pie Charts** - Part-to-whole relationships
- **Grouped/Stacked Charts** - Multi-series data

### Chart Generation Pipeline
1. User uploads CSV/Excel file
2. Supervisor routes to Chart Agent
3. GPT-5 generates Plotly code
4. Code executes safely in isolated namespace
5. Chart rendered as PNG (no external CDNs)
6. Stored in Azure Blob Storage with permanent URL

## 🏗️ Project Structure

```
Agion-LangGraph/
├── backend/
│   ├── langgraph_agents/      # LangGraph implementation
│   │   ├── nodes/              # Agent nodes
│   │   │   ├── supervisor.py
│   │   │   ├── chart_agent.py
│   │   │   └── general_agent.py
│   │   ├── tools/              # Agent tools
│   │   │   ├── chart_tools.py
│   │   │   ├── database_tools.py
│   │   │   └── storage_tools.py
│   │   ├── graph.py            # Graph definition
│   │   └── state.py            # State management
│   ├── api/                    # FastAPI endpoints
│   ├── core/                   # Core utilities
│   ├── models.py               # Database models
│   └── main.py                 # Application entry
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   ├── services/           # API client
│   │   └── types/              # TypeScript types
│   └── package.json
├── docs/                       # Documentation
├── k8s/                        # Kubernetes configs
└── scripts/                    # Deployment scripts
```

## 🔐 Security

- Password-protected access (configurable)
- No external CDN dependencies for charts
- Azure Blob Storage for secure file handling
- Content Security Policy compliant
- CORS properly configured

## 📈 Performance

- **Chart Generation**: ~2-4 seconds end-to-end
- **Response Time**: <1 second for general queries
- **Concurrency**: Async/await throughout
- **Deterministic**: Fixed seed and temperature for consistency

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Documentation

- [LangGraph Architecture](docs/LANGGRAPH_ARCHITECTURE.md)
- [Quick Start](docs/QUICK_START.md)
- [API Reference](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)

## 🤝 Contributing

This is a proprietary Agion AI platform. For access or contributions, contact the platform team.

## 📝 License

Proprietary - Agion AI Platform

## 🔗 Links

- **Platform**: Agion AI Agent Orchestration
- **Powered by**: Requesty AI (GPT-5)
- **Framework**: LangGraph 0.6.8
- **Deployment**: Azure Kubernetes Service

---

Built with ❤️ by the Agion AI Platform Team