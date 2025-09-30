"""
Tests for LangGraph tools (database, storage, charts)
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, Mock, patch

from langgraph_agents.tools.database_tools import (
    save_message,
    load_session_messages,
    load_file_metadata,
)
from langgraph_agents.tools.chart_tools import (
    validate_dataframe_for_chart,
)


@pytest.mark.asyncio
async def test_save_message(test_db, sample_chat_session):
    """Test saving message to database."""
    message = await save_message(
        db=test_db,
        session_id=sample_chat_session.id,
        role="user",
        content="Hello!",
    )

    assert message.id is not None
    assert message.session_id == sample_chat_session.id
    assert message.role == "user"
    assert message.content == "Hello!"
    assert message.agent_name is None


@pytest.mark.asyncio
async def test_save_assistant_message(test_db, sample_chat_session):
    """Test saving assistant message with agent name."""
    message = await save_message(
        db=test_db,
        session_id=sample_chat_session.id,
        role="assistant",
        content="Here's your answer!",
        agent_name="general_chat",
        metadata={"confidence": 0.9},
    )

    assert message.role == "assistant"
    assert message.agent_name == "general_chat"
    assert message.metadata["confidence"] == 0.9


@pytest.mark.asyncio
async def test_load_session_messages(test_db, sample_chat_session):
    """Test loading messages for a session."""
    # Save multiple messages
    await save_message(test_db, sample_chat_session.id, "user", "Message 1")
    await save_message(test_db, sample_chat_session.id, "assistant", "Response 1")
    await save_message(test_db, sample_chat_session.id, "user", "Message 2")

    # Load messages
    messages = await load_session_messages(test_db, sample_chat_session.id)

    assert len(messages) == 3
    assert messages[0].content == "Message 1"
    assert messages[1].content == "Response 1"
    assert messages[2].content == "Message 2"


@pytest.mark.asyncio
async def test_load_file_metadata(test_db, sample_uploaded_file):
    """Test loading file metadata."""
    files = await load_file_metadata(test_db, [sample_uploaded_file.id])

    assert len(files) == 1
    assert files[0].id == sample_uploaded_file.id
    assert files[0].original_filename == "test_data.xlsx"


@pytest.mark.asyncio
async def test_load_file_metadata_empty():
    """Test loading file metadata with empty list."""
    # Create mock session
    mock_db = AsyncMock()

    files = await load_file_metadata(mock_db, [])

    assert files == []
    # Should not query database
    mock_db.execute.assert_not_called()


def test_validate_dataframe_valid(sample_dataframe):
    """Test validating valid DataFrame."""
    is_valid, error = validate_dataframe_for_chart(sample_dataframe)

    assert is_valid is True
    assert error is None


def test_validate_dataframe_empty():
    """Test validating empty DataFrame."""
    df = pd.DataFrame()

    is_valid, error = validate_dataframe_for_chart(df)

    assert is_valid is False
    assert "No data available" in error


def test_validate_dataframe_too_few_rows():
    """Test validating DataFrame with too few rows."""
    df = pd.DataFrame({"col1": [1]})

    is_valid, error = validate_dataframe_for_chart(df)

    assert is_valid is False
    assert "Not enough data points" in error


def test_validate_dataframe_no_columns():
    """Test validating DataFrame with no columns."""
    df = pd.DataFrame([])

    is_valid, error = validate_dataframe_for_chart(df)

    assert is_valid is False
    assert "No columns" in error or "No data" in error