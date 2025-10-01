"""
Agent-Chat Chat API
Endpoints for chat functionality and message processing
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uuid

from core.database import get_db
from models import ChatSession as DBChatSession, ChatMessage as DBChatMessage
from langgraph_agents import create_agent_graph
from langgraph_agents.state import create_initial_state

router = APIRouter()


class ChatMessage(BaseModel):
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None
    agent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Dict[str, Any] = {}
    files: List[str] = []


class ChatResponse(BaseModel):
    message: ChatMessage
    agent_used: Optional[str] = None
    confidence: float
    session_id: str


@router.post("/chat/send")
async def send_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Send a chat message and get AI response"""
    try:
        # Create or get session
        session_id = request.session_id or str(uuid.uuid4())

        # Check if session exists in DB
        result = await db.execute(
            select(DBChatSession).where(DBChatSession.id == session_id)
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            # Create new session
            db_session = DBChatSession(
                id=session_id,
                title=request.message[:100] if request.message else "New Chat",
                is_active=True
            )
            db.add(db_session)
            await db.flush()

        # Store user message
        user_message = DBChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=request.message,
            meta_data={"context": request.context, "files": request.files}
        )
        db.add(user_message)
        await db.flush()

        # Use LangGraph for agent orchestration
        graph = create_agent_graph()

        # Create initial state
        initial_state = create_initial_state(
            query=request.message,
            session_id=session_id,
            uploaded_files=request.files,
        )

        # Execute graph
        start_time = datetime.utcnow()
        result_state = await graph.ainvoke(initial_state)
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Extract results
        agent_response = result_state.get("agent_response", "I apologize, but I couldn't process your request.")
        selected_agent = result_state.get("selected_agent", "unknown")
        confidence = result_state.get("confidence", 0.0)
        agent_data = result_state.get("agent_data", {})
        error = result_state.get("error")
        execution_id = result_state.get("execution_id")  # From governance wrapper

        # Store assistant message
        assistant_message_id = str(uuid.uuid4())
        assistant_db_message = DBChatMessage(
            id=assistant_message_id,
            session_id=session_id,
            role="assistant",
            content=agent_response,
            agent_id=selected_agent,
            meta_data={
                "confidence": confidence,
                "execution_time": execution_time,
                "agent_data": agent_data,
                "execution_path": result_state.get("execution_path", []),
                "error": error,
                "execution_id": execution_id,  # Include for feedback tracking
            }
        )
        db.add(assistant_db_message)

        # Update session
        db_session.updated_at = datetime.utcnow()
        await db.commit()

        # Create chat message response
        assistant_message = ChatMessage(
            id=assistant_message_id,
            role="assistant",
            content=agent_response,
            timestamp=datetime.utcnow(),
            agent_id=selected_agent,
            metadata={
                "message_id": assistant_message_id,  # For feedback submission
                "confidence": confidence,
                "execution_time": execution_time,
                "agent_data": agent_data,
                "execution_id": execution_id,
            }
        )

        return ChatResponse(
            message=assistant_message,
            agent_used=selected_agent,
            confidence=confidence,
            session_id=session_id
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


# Multi-agent endpoint removed - LangGraph automatically routes to best agent


@router.get("/chat/suggestions")
async def get_chat_suggestions():
    """Get suggested queries for chat interface"""
    return {
        "status": "success",
        "suggestions": [
            {
                "category": "Brand Analysis",
                "queries": [
                    "Analyze NS Carton brand performance in Almaty",
                    "Show me YoY growth trends for my brand",
                    "What's driving revenue growth vs VPO decline?",
                    "Generate brand performance recommendations"
                ]
            },
            {
                "category": "Anomaly Detection",
                "queries": [
                    "Detect anomalies in SOM data",
                    "Check for unusual market share changes",
                    "Alert me to significant SOM deviations",
                    "Analyze SOM trends for 65+ demographics"
                ]
            },
            {
                "category": "General Analysis",
                "queries": [
                    "Upload and analyze my Excel data",
                    "What insights can you provide from my files?",
                    "Help me understand my data patterns",
                    "Create a summary report"
                ]
            }
        ]
    }


# Chat History Management Endpoints

class SessionListResponse(BaseModel):
    """Response model for session list"""
    sessions: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int


class MessageListResponse(BaseModel):
    """Response model for message list"""
    messages: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int


@router.get("/chat/sessions", response_model=SessionListResponse)
async def get_chat_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of chat sessions"""
    try:
        # Get total count
        count_result = await db.execute(
            select(DBChatSession).where(DBChatSession.is_active == True)
        )
        total = len(count_result.all())

        # Get paginated sessions
        offset = (page - 1) * per_page
        result = await db.execute(
            select(DBChatSession)
            .where(DBChatSession.is_active == True)
            .order_by(desc(DBChatSession.updated_at))
            .limit(per_page)
            .offset(offset)
        )
        sessions = result.scalars().all()

        return SessionListResponse(
            sessions=[
                {
                    "id": s.id,
                    "title": s.title,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ],
            total=total,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")


@router.get("/chat/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated messages for a specific session"""
    try:
        # Verify session exists
        session_result = await db.execute(
            select(DBChatSession).where(DBChatSession.id == session_id)
        )
        if not session_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Session not found")

        # Get total message count
        count_result = await db.execute(
            select(DBChatMessage).where(DBChatMessage.session_id == session_id)
        )
        total = len(count_result.all())

        # Get paginated messages
        offset = (page - 1) * per_page
        result = await db.execute(
            select(DBChatMessage)
            .where(DBChatMessage.session_id == session_id)
            .order_by(DBChatMessage.created_at)
            .limit(per_page)
            .offset(offset)
        )
        messages = result.scalars().all()

        return MessageListResponse(
            messages=[
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "agent_id": m.agent_id,
                    "metadata": m.meta_data,
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
            total=total,
            page=page,
            per_page=per_page
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    try:
        result = await db.execute(
            select(DBChatSession).where(DBChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Soft delete by marking inactive
        session.is_active = False
        await db.commit()

        return {"status": "success", "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")