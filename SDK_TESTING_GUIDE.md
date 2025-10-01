## SDK Testing Guide - Agion Platform Integration

Complete guide for testing the Agion SDK functionality, including user feedback, trust scores, and governance.

## Overview

The Agion SDK integration provides:
1. **User Feedback** → Trust score updates
2. **Governance** → Policy enforcement before agent execution
3. **Metrics** → Real-time execution tracking
4. **Trust Management** → Automatic score calculation

## Architecture Flow

```
User Query
    ↓
Chat API (/api/v1/chat/send)
    ↓
LangGraph Graph Execution
    ↓
@governed_node Decorator:
  1. Check policies (< 1ms)
  2. Execute agent
  3. Report metrics to Redis
  4. Update trust score
    ↓
Return response with execution_id
    ↓
User provides feedback (/api/v1/feedback)
    ↓
SDK publishes feedback event
    ↓
Governance Service updates trust score
```

## Setup for Testing

### 1. Start Required Services

```bash
# Start Redis (for SDK events)
docker run -d -p 6379:6379 redis:6.4.0

# Or use existing Redis
redis-cli ping  # Should return PONG
```

### 2. Configure Environment

```bash
# backend/.env
AGION_GATEWAY_URL=http://localhost:8080  # Or platform gateway
AGION_REDIS_URL=redis://localhost:6379
AGION_AGENT_ID=langgraph-v2
AGION_AGENT_VERSION=2.0.0
AGION_POLICY_SYNC_ENABLED=true
```

### 3. Initialize Database

```bash
cd backend
python init_database.py
```

This creates the `user_feedback` table:
```sql
CREATE TABLE user_feedback (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,  -- 'thumbs_up' or 'thumbs_down'
    rating INTEGER,                       -- Optional 1-5
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Start Backend

```bash
cd backend
python start_server.py
```

Expected output:
```
✅ Database initialized
✅ Agion SDK initialized (platform integration active)
✅ Agents registered: 6 agents
🎯 Agent-Chat Backend ready!
```

## Testing Scenarios

### Scenario 1: Basic Chat with Feedback

**Step 1: Send a chat message**

```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "session_id": "test-session-1"
  }'
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "Hello! I'm doing well...",
    "agent_id": "general_chat",
    "metadata": {
      "message_id": "abc-123-def-456",
      "execution_id": "exec-789-xyz-012",
      "confidence": 0.95,
      "execution_time": 1.234
    }
  },
  "agent_used": "general_chat",
  "confidence": 0.95,
  "session_id": "test-session-1"
}
```

**Step 2: Provide positive feedback**

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "abc-123-def-456",
    "feedback_type": "thumbs_up",
    "rating": 5,
    "comment": "Great response!",
    "user_id": "user-001"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Feedback submitted successfully",
  "feedback_id": "feedback-123",
  "trust_impact": "+0.5% trust score (positive rating)"
}
```

**Step 3: Verify feedback was recorded**

```bash
curl http://localhost:8000/api/v1/feedback/message/abc-123-def-456
```

**Response:**
```json
{
  "status": "success",
  "message_id": "abc-123-def-456",
  "feedback_count": 1,
  "feedbacks": [
    {
      "id": "feedback-123",
      "feedback_type": "thumbs_up",
      "rating": 5,
      "comment": "Great response!",
      "user_id": "user-001",
      "created_at": "2025-10-01T12:34:56Z"
    }
  ]
}
```

### Scenario 2: Chart Generation with Feedback

**Step 1: Upload a CSV file**

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@data.csv"
```

**Response:**
```json
{
  "file_id": "file-abc-123",
  "filename": "data.csv",
  "status": "uploaded"
}
```

**Step 2: Request a chart**

```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a bar chart showing sales by region",
    "files": ["file-abc-123"]
  }'
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "✅ Here's your chart based on 'data.csv':",
    "agent_id": "chart_generator",
    "metadata": {
      "message_id": "msg-xyz-789",
      "execution_id": "exec-chart-123",
      "agent_data": {
        "chart_png": "data:image/png;base64,...",
        "chart_url": "https://storage.azure.com/charts/..."
      }
    }
  },
  "agent_used": "chart_generator",
  "confidence": 1.0
}
```

**Step 3: Provide negative feedback**

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg-xyz-789",
    "feedback_type": "thumbs_down",
    "rating": 2,
    "comment": "Chart colors are hard to read"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Feedback submitted successfully",
  "feedback_id": "feedback-456",
  "trust_impact": null  // No trust impact (rating < 4)
}
```

### Scenario 3: Monitor Trust Score Updates

**Monitor Redis Events**

```bash
# Terminal 1: Watch trust events
redis-cli XREAD COUNT 10 STREAMS agion:events:trust 0-0

# Terminal 2: Watch user feedback events
redis-cli XREAD COUNT 10 STREAMS agion:events:feedback 0-0
```

**Expected trust event:**
```json
{
  "agent_id": "langgraph-v2:chart_agent",
  "event_type": "task_completed",
  "severity": "positive",
  "impact": "0.02",  // +2%
  "confidence": "1.0",
  "context": {
    "execution_id": "exec-chart-123",
    "latency_ms": "1234.5"
  },
  "timestamp": "2025-10-01T12:34:56Z"
}
```

**Expected feedback event:**
```json
{
  "execution_id": "exec-chart-123",
  "user_id": "user-001",
  "feedback_type": "thumbs_up",
  "rating": "5",
  "comment": "Great chart!",
  "timestamp": "2025-10-01T12:35:10Z"
}
```

### Scenario 4: Get Feedback Statistics

```bash
curl http://localhost:8000/api/v1/feedback/stats
```

**Response:**
```json
{
  "status": "success",
  "total_feedback": 25,
  "thumbs_up": 18,
  "thumbs_down": 7,
  "satisfaction_rate": 0.72,  // 72%
  "average_rating": 4.2,
  "feedback_with_comments": 15
}
```

## Trust Score Mechanics

### Impact Values

| Event Type | Trust Impact | Example |
|------------|--------------|---------|
| Task Started | 0% | Tracking only |
| Task Completed | **+2%** | Successful execution |
| Task Failed | **-2%** | Failure without exception |
| Error | **-3%** | Exception thrown |
| Governance Violation | **-5%** | Policy breach |
| Positive Feedback (rating ≥4) | **+0.5%** | User satisfaction |
| Negative Feedback (rating <4) | 0% | Recorded but no impact |

### Trust Score Progression

Starting from 0.4 (40% baseline):

```
Execution 1:  Success (+2%)  → 0.42
Execution 2:  Success (+2%)  → 0.44
Execution 3:  Success (+2%)  → 0.46
Execution 4:  Success (+2%)  → 0.48
Execution 5:  Success (+2%)  → 0.50
Execution 6:  Success (+2%)  → 0.52
Execution 7:  Success (+2%)  → 0.54
Execution 8:  Success (+2%)  → 0.56
Execution 9:  Success (+2%)  → 0.58
Execution 10: Success (+2%)  → 0.60 ✅ GRADUATED

User feedback: Rating 5 (+0.5%) → 0.605
```

**Graduation**: After 10 successful executions, agent graduates from 0.4 → 0.6 (proven reliability).

## API Endpoints

### Chat Endpoints

```
POST /api/v1/chat/send
  - Send message and get response
  - Returns: message with execution_id

GET /api/v1/chat/sessions
  - List chat sessions

GET /api/v1/chat/sessions/{session_id}/messages
  - Get messages for session
```

### Feedback Endpoints

```
POST /api/v1/feedback
  - Submit user feedback
  - Body: {message_id, feedback_type, rating?, comment?, user_id?}
  - Returns: feedback_id and trust_impact

GET /api/v1/feedback/message/{message_id}
  - Get all feedback for a message

GET /api/v1/feedback/stats
  - Get aggregated feedback statistics
```

### Health Endpoint

```
GET /api/v1/health
  - Check backend health
  - Includes SDK status
```

## Frontend Integration

### React Example

```typescript
// Send message
const sendMessage = async (message: string) => {
  const response = await fetch('/api/v1/chat/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message})
  });
  const data = await response.json();

  // Store message_id for feedback
  setMessageId(data.message.metadata.message_id);
  return data;
};

// Submit feedback
const submitFeedback = async (
  messageId: string,
  feedbackType: 'thumbs_up' | 'thumbs_down',
  rating?: number
) => {
  const response = await fetch('/api/v1/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      message_id: messageId,
      feedback_type: feedbackType,
      rating,
      user_id: currentUser.id
    })
  });

  const data = await response.json();
  console.log('Trust impact:', data.trust_impact);
  return data;
};

// UI Component
function MessageActions({messageId}: {messageId: string}) {
  return (
    <div>
      <button onClick={() => submitFeedback(messageId, 'thumbs_up', 5)}>
        👍
      </button>
      <button onClick={() => submitFeedback(messageId, 'thumbs_down', 2)}>
        👎
      </button>
    </div>
  );
}
```

## Debugging

### Check SDK Status

```bash
curl http://localhost:8000/api/v1/health
```

Look for:
```json
{
  "agion_sdk": {
    "initialized": true,
    "metrics": {
      "policy_engine": {...},
      "event_client": {...}
    }
  }
}
```

### Check Redis Connection

```bash
redis-cli ping  # Should return PONG
redis-cli XINFO STREAM agion:events:trust  # Check stream exists
```

### View Backend Logs

```bash
# Look for SDK initialization
grep "Agion SDK" backend.log

# Look for agent registration
grep "Agents registered" backend.log

# Look for trust events
grep "trust impact" backend.log
```

### Common Issues

**Issue**: "Agion SDK not initialized"
- **Fix**: Check AGION_GATEWAY_URL and AGION_REDIS_URL in .env

**Issue**: "Message not found" when submitting feedback
- **Fix**: Ensure message_id from chat response matches feedback request

**Issue**: Feedback submitted but no trust impact
- **Fix**: Rating must be ≥4 for +0.5% trust impact

## Performance Benchmarks

- **Policy Check**: < 1ms (local engine)
- **Event Publishing**: < 5ms (async, non-blocking)
- **Feedback Submission**: < 50ms (database + SDK)
- **Trust Score Update**: Asynchronous (via Redis Streams)

## Summary

✅ **User feedback system** fully implemented
✅ **Trust score updates** via SDK
✅ **Database model** for feedback storage
✅ **API endpoints** for feedback submission and stats
✅ **Frontend integration** examples provided
✅ **Redis event streaming** for platform integration
✅ **Comprehensive testing** scenarios documented

Users can now rate agent responses, which directly affects agent trust scores through the Agion SDK!
