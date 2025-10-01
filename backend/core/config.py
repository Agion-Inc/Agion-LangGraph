"""
Agent-Chat Configuration Management
World-class configuration with environment-based settings
"""

from functools import lru_cache
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Agent-Chat"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Environment: development, staging, production"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="HOST")
    api_port: int = Field(default=8000, alias="PORT")
    api_prefix: str = "/api/v1"
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
        description="List of allowed CORS origins",
        json_schema_extra={"env": "CORS_ORIGINS"}
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./bpchat.db",
        description="Async SQLite connection string"
    )
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # 1 hour default

    # File Storage
    upload_dir: str = "uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = [".xlsx", ".csv", ".json", ".parquet"]
    
    # Storage Backend Configuration
    storage_backend: str = Field(
        default="local",
        alias="STORAGE_BACKEND",
        description="Storage backend: 'local' or 'azure'"
    )
    
    # Azure Blob Storage Configuration
    azure_storage_connection_string: Optional[str] = Field(
        default=None,
        alias="AZURE_STORAGE_CONNECTION_STRING",
        description="Azure Storage connection string"
    )
    azure_storage_container_name: str = Field(
        default="bpchat-files",
        alias="AZURE_STORAGE_CONTAINER_NAME",
        description="Azure Storage container name"
    )
    azure_storage_sas_expiry_days: int = Field(
        default=7,
        alias="AZURE_STORAGE_SAS_EXPIRY_DAYS",
        description="Default SAS token expiry in days"
    )

    # Security
    secret_key: str = Field(
        default="Agent-Chat-Default-Secret-Change-In-Production-2025",
        alias="JWT_SECRET_KEY",
        description="JWT secret key - MUST be set in production"
    )
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # AI/ML Configuration
    REQUESTY_AI_API_KEY: Optional[str] = Field(default=None, alias="REQUESTY_AI_API_KEY")
    requesty_ai_api_key: Optional[str] = Field(default=None, alias="REQUESTY_AI_API_KEY")
    REQUESTY_AI_API_BASE: Optional[str] = Field(default=None, alias="REQUESTY_AI_API_BASE")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    embedding_model: str = "all-MiniLM-L6-v2"
    max_embedding_batch_size: int = 32

    # Agent Configuration
    max_concurrent_agents: int = 10
    agent_timeout_seconds: int = 300  # 5 minutes
    agent_retry_attempts: int = 3

    # Monitoring & Logging
    log_level: str = "INFO"
    log_format: str = "json"
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Agion Platform Integration
    agion_gateway_url: str = Field(
        default="http://gateway-service.agion-core.svc.cluster.local:8080",
        alias="AGION_GATEWAY_URL",
        description="Agion Gateway Service URL"
    )
    agion_redis_url: str = Field(
        default="redis://redis-service.agion-core.svc.cluster.local:6379",
        alias="AGION_REDIS_URL",
        description="Agion Redis URL for events and policy sync"
    )
    agion_agent_id: str = Field(
        default="langgraph-v2",
        alias="AGION_AGENT_ID",
        description="Agion agent container identifier"
    )
    agion_agent_version: str = Field(
        default="2.0.0",
        alias="AGION_AGENT_VERSION",
        description="Agent container version"
    )
    agion_policy_sync_enabled: bool = Field(
        default=True,
        alias="AGION_POLICY_SYNC_ENABLED",
        description="Enable automatic policy synchronization"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        # In production, use explicit allowed origins
        # In development, still use configured origins for security
        return self.allowed_origins


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance
settings = get_settings()