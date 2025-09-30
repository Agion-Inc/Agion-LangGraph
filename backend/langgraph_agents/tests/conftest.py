"""
Pytest configuration and shared fixtures for LangGraph tests
"""

import pytest
import pandas as pd
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from core.database import Base
from models.models import ChatSession, ChatMessage, UploadedFile


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session.

    Yields:
        AsyncSession: Test database session
    """
    # Create engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """
    Create sample DataFrame for chart tests.

    Returns:
        pd.DataFrame: Sample data
    """
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10),
        "sales": [100, 120, 115, 130, 125, 140, 135, 150, 145, 160],
        "region": ["North", "South", "North", "South", "North", "South", "North", "South", "North", "South"],
    })


@pytest.fixture
def sample_session_id() -> str:
    """
    Generate sample session ID.

    Returns:
        str: Session ID
    """
    return "test-session-123"


@pytest.fixture
async def sample_chat_session(test_db: AsyncSession, sample_session_id: str) -> ChatSession:
    """
    Create sample chat session in test database.

    Args:
        test_db: Test database session
        sample_session_id: Session ID

    Returns:
        ChatSession: Created session
    """
    session = ChatSession(id=sample_session_id)
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)
    return session


@pytest.fixture
async def sample_uploaded_file(test_db: AsyncSession, sample_session_id: str) -> UploadedFile:
    """
    Create sample uploaded file in test database.

    Args:
        test_db: Test database session
        sample_session_id: Session ID

    Returns:
        UploadedFile: Created file record
    """
    file = UploadedFile(
        original_filename="test_data.xlsx",
        blob_name=f"{sample_session_id}/test_data.xlsx",
        file_size=1024,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        session_id=sample_session_id,
    )
    test_db.add(file)
    await test_db.commit()
    await test_db.refresh(file)
    return file


@pytest.fixture
def mock_anthropic_api_key(monkeypatch):
    """Mock Anthropic API key for tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")