"""add performance indexes

Revision ID: 001
Revises: 
Create Date: 2024-09-28 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes to improve query speed"""
    
    # User table indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    
    # Chat session indexes
    op.create_index('idx_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    op.create_index('idx_chat_sessions_created_at', 'chat_sessions', ['created_at'])
    
    # Chat messages indexes
    op.create_index('idx_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('idx_chat_messages_created_at', 'chat_messages', ['created_at'])
    op.create_index('idx_chat_messages_role', 'chat_messages', ['role'])
    
    # Uploaded files indexes
    op.create_index('idx_uploaded_files_user_id', 'uploaded_files', ['user_id'])
    op.create_index('idx_uploaded_files_status', 'uploaded_files', ['status'])
    op.create_index('idx_uploaded_files_created_at', 'uploaded_files', ['created_at'])
    op.create_index('idx_uploaded_files_content_type', 'uploaded_files', ['content_type'])
    
    # Worksheet data indexes
    op.create_index('idx_worksheet_data_file_id', 'worksheet_data', ['file_id'])
    op.create_index('idx_worksheet_data_name', 'worksheet_data', ['name'])
    
    # Worksheet rows indexes
    op.create_index('idx_worksheet_rows_worksheet_id', 'worksheet_rows', ['worksheet_id'])
    op.create_index('idx_worksheet_rows_row_index', 'worksheet_rows', ['row_index'])
    
    # File access log indexes (for audit and performance tracking)
    op.create_index('idx_file_access_logs_file_id', 'file_access_logs', ['file_id'])
    op.create_index('idx_file_access_logs_user_id', 'file_access_logs', ['user_id'])
    op.create_index('idx_file_access_logs_action', 'file_access_logs', ['action'])
    op.create_index('idx_file_access_logs_timestamp', 'file_access_logs', ['timestamp'])
    
    # Composite indexes for common query patterns
    op.create_index('idx_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'])
    op.create_index('idx_uploaded_files_user_status', 'uploaded_files', ['user_id', 'status'])
    op.create_index('idx_file_access_logs_file_timestamp', 'file_access_logs', ['file_id', 'timestamp'])


def downgrade() -> None:
    """Remove performance indexes"""
    
    # Remove composite indexes
    op.drop_index('idx_file_access_logs_file_timestamp', 'file_access_logs')
    op.drop_index('idx_uploaded_files_user_status', 'uploaded_files')
    op.drop_index('idx_chat_messages_session_created', 'chat_messages')
    
    # Remove file access log indexes
    op.drop_index('idx_file_access_logs_timestamp', 'file_access_logs')
    op.drop_index('idx_file_access_logs_action', 'file_access_logs')
    op.drop_index('idx_file_access_logs_user_id', 'file_access_logs')
    op.drop_index('idx_file_access_logs_file_id', 'file_access_logs')
    
    # Remove worksheet rows indexes
    op.drop_index('idx_worksheet_rows_row_index', 'worksheet_rows')
    op.drop_index('idx_worksheet_rows_worksheet_id', 'worksheet_rows')
    
    # Remove worksheet data indexes
    op.drop_index('idx_worksheet_data_name', 'worksheet_data')
    op.drop_index('idx_worksheet_data_file_id', 'worksheet_data')
    
    # Remove uploaded files indexes
    op.drop_index('idx_uploaded_files_content_type', 'uploaded_files')
    op.drop_index('idx_uploaded_files_created_at', 'uploaded_files')
    op.drop_index('idx_uploaded_files_status', 'uploaded_files')
    op.drop_index('idx_uploaded_files_user_id', 'uploaded_files')
    
    # Remove chat messages indexes
    op.drop_index('idx_chat_messages_role', 'chat_messages')
    op.drop_index('idx_chat_messages_created_at', 'chat_messages')
    op.drop_index('idx_chat_messages_session_id', 'chat_messages')
    
    # Remove chat session indexes
    op.drop_index('idx_chat_sessions_created_at', 'chat_sessions')
    op.drop_index('idx_chat_sessions_user_id', 'chat_sessions')
    
    # Remove user indexes
    op.drop_index('idx_users_is_active', 'users')
    op.drop_index('idx_users_username', 'users')
    op.drop_index('idx_users_email', 'users')
