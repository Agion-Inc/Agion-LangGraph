"""
Database Tools - Type-safe database operations for LangGraph agents

Provides utilities for:
- Saving and loading chat messages
- Loading file metadata
- Session management
"""

from typing import AsyncGenerator, List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from core.database import get_db
from models import ChatSession, ChatMessage, UploadedFile


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for agent operations.

    Yields:
        AsyncSession: Database session
    """
    async for db in get_db():
        yield db


async def save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChatMessage:
    """
    Save a chat message to the database.

    Args:
        db: Database session
        session_id: Chat session ID
        role: Message role ("user" or "assistant")
        content: Message content
        agent_name: Name of agent that generated response (for assistant messages)
        metadata: Additional metadata (chart data, confidence, etc.)

    Returns:
        ChatMessage: Saved message object
    """
    import uuid
    message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        agent_id=agent_name,
        meta_data=metadata or {},
        # created_at is set automatically by server_default
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message


async def load_session_messages(
    db: AsyncSession,
    session_id: str,
    limit: int = 50,
) -> List[ChatMessage]:
    """
    Load recent messages for a session.

    Args:
        db: Database session
        session_id: Chat session ID
        limit: Maximum number of messages to load

    Returns:
        List[ChatMessage]: Messages ordered by timestamp (oldest first)
    """
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    # Return in chronological order (oldest first)
    return list(reversed(messages))


async def load_file_metadata(
    db: AsyncSession,
    file_ids: List[str],
) -> List[UploadedFile]:
    """
    Load metadata for uploaded files.

    Args:
        db: Database session
        file_ids: List of file IDs to load

    Returns:
        List[UploadedFile]: File metadata objects
    """
    if not file_ids:
        return []

    query = select(UploadedFile).where(UploadedFile.id.in_(file_ids))
    result = await db.execute(query)

    return result.scalars().all()


async def get_or_create_session(
    db: AsyncSession,
    session_id: str,
) -> ChatSession:
    """
    Get existing session or create new one.

    Args:
        db: Database session
        session_id: Chat session ID

    Returns:
        ChatSession: Session object
    """
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        session = ChatSession(
            id=session_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return session


async def update_session_timestamp(
    db: AsyncSession,
    session_id: str,
) -> None:
    """
    Update session's last activity timestamp.

    Args:
        db: Database session
        session_id: Chat session ID
    """
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if session:
        session.updated_at = datetime.utcnow()
        await db.commit()