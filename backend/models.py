"""
Agent-Chat Database Models V2
Optimized SQLAlchemy models with file system storage
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
import uuid


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    roles = Column(JSON, default=lambda: ["user"])
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatSession(Base):
    """Chat session model"""
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, index=True)
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class ChatMessage(Base):
    """Chat message model"""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True)  # UUID
    session_id = Column(String(36), index=True)
    role = Column(String(20))  # 'user' or 'assistant'
    content = Column(Text)
    agent_id = Column(String(100))
    meta_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UploadedFile(Base):
    """Uploaded file model - optimized for file system storage"""
    __tablename__ = "uploaded_files"

    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100))
    file_path = Column(String(500), nullable=False)  # Relative path in storage system
    file_hash = Column(String(64))  # SHA-256 hash for deduplication
    category = Column(String(50))  # File category (excel, csv, json, etc.)
    status = Column(String(50), default="uploaded")  # 'uploaded', 'processing', 'processed', 'error'
    upload_source = Column(String(100))  # 'web_ui', 'api', 'batch'
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    last_accessed = Column(DateTime(timezone=True))

    # Relationship to extracted data tables
    worksheets = relationship("WorksheetData", back_populates="file", cascade="all, delete-orphan")
    queries = relationship("DataQuery", back_populates="file", cascade="all, delete-orphan")


class AgentExecution(Base):
    """Agent execution log"""
    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True)  # UUID
    agent_id = Column(String(100))
    request_id = Column(String(36))
    status = Column(String(50))
    execution_time = Column(Float)
    confidence_score = Column(Float)
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class WorksheetData(Base):
    """Extracted worksheet data from Excel/CSV files"""
    __tablename__ = "worksheet_data"

    id = Column(String(36), primary_key=True)  # UUID
    file_id = Column(String(36), ForeignKey("uploaded_files.id"), nullable=False)
    sheet_name = Column(String(255))  # For Excel files with multiple sheets
    sheet_index = Column(Integer, default=0)
    row_count = Column(Integer)
    column_count = Column(Integer)
    column_headers = Column(JSON)  # Store column names/headers
    data_types = Column(JSON)  # Store inferred data types
    sample_data = Column(JSON)  # Store first few rows as sample
    data_summary = Column(JSON)  # Statistical summary of data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("UploadedFile", back_populates="worksheets")
    rows = relationship("WorksheetRow", back_populates="worksheet", cascade="all, delete-orphan")


class WorksheetRow(Base):
    """Individual rows of data from worksheets"""
    __tablename__ = "worksheet_rows"

    id = Column(String(36), primary_key=True)  # UUID
    worksheet_id = Column(String(36), ForeignKey("worksheet_data.id"), nullable=False)
    row_index = Column(Integer, nullable=False)  # 0-based row number
    row_data = Column(JSON, nullable=False)  # Store row data as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worksheet = relationship("WorksheetData", back_populates="rows")


class DataQuery(Base):
    """Store user queries and results for data analysis"""
    __tablename__ = "data_queries"

    id = Column(String(36), primary_key=True)  # UUID
    file_id = Column(String(36), ForeignKey("uploaded_files.id"), nullable=False)
    query_text = Column(Text, nullable=False)  # Natural language query
    sql_query = Column(Text)  # Generated SQL query (if applicable)
    result_data = Column(JSON)  # Query results
    result_summary = Column(Text)  # Human-readable summary
    agent_id = Column(String(100))  # Which agent processed the query
    execution_time = Column(Float)
    confidence_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("UploadedFile", back_populates="queries")


class FileAccessLog(Base):
    """Track file access for analytics and security"""
    __tablename__ = "file_access_logs"

    id = Column(String(36), primary_key=True)  # UUID
    file_id = Column(String(36), ForeignKey("uploaded_files.id"), nullable=False)
    access_type = Column(String(50))  # 'read', 'download', 'process', 'delete'
    user_id = Column(Integer)  # User who accessed the file
    ip_address = Column(String(45))  # IPv4 or IPv6 address
    user_agent = Column(String(500))  # Browser/client info
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file = relationship("UploadedFile")
