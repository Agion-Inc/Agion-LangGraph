"""
Input Validators for Agent-Chat API
Provides comprehensive input validation and sanitization
"""

import re
from typing import Optional, List, Any
from pydantic import BaseModel, Field, validator, constr
from datetime import datetime


class SanitizedStr(str):
    """String type that prevents SQL injection and XSS"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('string required')
        
        # Remove SQL injection attempts
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\bOR\b.*=.*)",
            r"('.*--)",
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Potential SQL injection detected')
        
        # Remove XSS attempts
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
        ]
        
        for pattern in xss_patterns:
            v = re.sub(pattern, '', v, flags=re.IGNORECASE)
        
        # Strip HTML tags
        v = re.sub(r'<[^>]+>', '', v)
        
        # Limit whitespace
        v = re.sub(r'\s+', ' ', v)
        
        return v.strip()


class ChatMessageRequest(BaseModel):
    """Validated chat message request"""
    message: SanitizedStr = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, max_length=100)
    file_ids: Optional[List[str]] = Field(default_factory=list, max_items=10)
    agent_id: Optional[str] = Field(None, max_length=100)
    
    @validator('file_ids')
    def validate_file_ids(cls, v):
        if v:
            for file_id in v:
                if not re.match(r'^[a-zA-Z0-9_-]+$', file_id):
                    raise ValueError(f'Invalid file ID: {file_id}')
        return v
    
    @validator('session_id', 'agent_id')
    def validate_id_format(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid ID format')
        return v


class FileUploadRequest(BaseModel):
    """Validated file upload request"""
    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    size: int = Field(..., gt=0, le=104857600)  # Max 100MB
    
    @validator('filename')
    def validate_filename(cls, v):
        # Remove path components
        v = v.replace('\\', '/').split('/')[-1]
        
        # Check for valid filename
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Invalid filename')
        
        # Check extension
        allowed_extensions = ['.xlsx', '.xls', '.csv', '.json', '.parquet', '.txt']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}')
        
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/json',
            'application/octet-stream',
            'text/plain'
        ]
        
        if v not in allowed_types:
            raise ValueError(f'Content type not allowed: {v}')
        
        return v


class AgentInvokeRequest(BaseModel):
    """Validated agent invocation request"""
    agent_id: str = Field(..., max_length=100)
    user_query: SanitizedStr = Field(..., min_length=1, max_length=5000)
    file_ids: Optional[List[str]] = Field(default_factory=list, max_items=10)
    session_id: Optional[str] = Field(None, max_length=100)
    timeout: Optional[int] = Field(30, ge=1, le=300)  # 1-300 seconds
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid agent ID format')
        return v


class ChartGenerationRequest(BaseModel):
    """Validated chart generation request"""
    chart_type: str = Field(..., max_length=50)
    data: dict = Field(...)
    title: Optional[str] = Field(None, max_length=200)
    options: Optional[dict] = Field(default_factory=dict)
    
    @validator('chart_type')
    def validate_chart_type(cls, v):
        allowed_types = [
            'bar', 'line', 'scatter', 'pie', 'donut', 
            'area', 'heatmap', 'box', 'violin', 'histogram'
        ]
        
        if v.lower() not in allowed_types:
            raise ValueError(f'Invalid chart type. Allowed: {", ".join(allowed_types)}')
        
        return v.lower()
    
    @validator('data')
    def validate_data(cls, v):
        if not v:
            raise ValueError('Data cannot be empty')
        
        # Check for required fields based on structure
        if 'labels' in v and 'values' not in v:
            raise ValueError('Values required when labels provided')
        
        if 'values' in v and 'labels' not in v:
            raise ValueError('Labels required when values provided')
        
        return v


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, le=1000)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[str] = Field('desc')
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v and v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v
    
    @validator('sort_by')
    def validate_sort_field(cls, v):
        if v:
            allowed_fields = ['created_at', 'updated_at', 'name', 'size', 'type']
            if v not in allowed_fields:
                raise ValueError(f'Invalid sort field. Allowed: {", ".join(allowed_fields)}')
        return v


class SearchParams(BaseModel):
    """Search parameters"""
    query: SanitizedStr = Field(..., min_length=1, max_length=500)
    filters: Optional[dict] = Field(default_factory=dict)
    include_archived: bool = Field(False)
    
    @validator('filters')
    def validate_filters(cls, v):
        if v:
            # Validate filter keys
            allowed_keys = ['type', 'status', 'agent_id', 'date_from', 'date_to']
            for key in v.keys():
                if key not in allowed_keys:
                    raise ValueError(f'Invalid filter key: {key}')
        return v


def sanitize_html(text: str) -> str:
    """Remove HTML tags and dangerous content"""
    if not text:
        return text
    
    # Remove script tags and content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove style tags and content
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove javascript: links
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # Remove event handlers
    text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_file_path(path: str) -> bool:
    """Validate file path to prevent directory traversal"""
    # Remove any directory traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        return False
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9_/.-]+$', path):
        return False
    
    return True


def validate_json_data(data: Any, max_depth: int = 10) -> bool:
    """Validate JSON data structure to prevent deeply nested attacks"""
    def check_depth(obj, depth=0):
        if depth > max_depth:
            return False
        
        if isinstance(obj, dict):
            return all(check_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            return all(check_depth(item, depth + 1) for item in obj)
        
        return True
    
    return check_depth(data)
