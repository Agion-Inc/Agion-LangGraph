"""
Base Pydantic Models with Simplified Configuration
Avoids plugin issues and provides clean base classes
"""

from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from datetime import datetime


class SimpleBaseModel(BaseModel):
    """
    Simplified base model without plugins or complex configurations
    Uses explicit ConfigDict for better control
    """
    model_config = ConfigDict(
        # Basic settings
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=False,
        
        # JSON Schema
        json_schema_extra=None,
        
        # Serialization
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        
        # Performance
        # Don't validate on assignment for better performance
        validate_default=False,
        
        # Compatibility
        populate_by_name=True,  # Accept both field names and aliases
        
        # Strict mode off for flexibility
        strict=False
    )


class APIResponse(SimpleBaseModel):
    """Base class for API responses"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()


class APIRequest(SimpleBaseModel):
    """Base class for API requests"""
    request_id: Optional[str] = None
    timestamp: datetime = datetime.now()
