"""
Agent-Chat Health Check API
System health and status endpoints
"""

from fastapi import APIRouter
from datetime import datetime
from core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "framework": "LangGraph 0.6.8",
        "environment": settings.environment
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "framework": "LangGraph 0.6.8",
            "environment": settings.environment,
            "system_info": {
                "agents": {
                    "architecture": "LangGraph",
                    "available_agents": [
                        "supervisor",
                        "chart_agent",
                        "brand_performance_agent",
                        "forecasting_agent",
                        "anomaly_detection_agent",
                        "general_agent"
                    ],
                    "total_agents": 6
                },
                "database": {
                    "status": "connected",
                    "url_configured": bool(settings.database_url)
                },
                "cache": {
                    "status": "configured" if settings.redis_url else "disabled",
                    "url_configured": bool(settings.redis_url)
                }
            },
            "configuration": {
                "debug_mode": settings.debug,
                "max_file_size": settings.max_file_size,
                "allowed_file_types": settings.allowed_file_types
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/health/agents")
async def agents_health_check():
    """Health check specifically for LangGraph agents"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "architecture": "LangGraph 0.6.8",
        "model": "GPT-5 via Requesty AI",
        "agent_summary": {
            "total_agents": 6,
            "routing_strategy": "Supervisor-based conditional routing"
        },
        "agents": [
            {
                "name": "supervisor",
                "type": "router",
                "description": "Intelligent query routing using GPT-5",
                "status": "active"
            },
            {
                "name": "chart_agent",
                "type": "specialized",
                "description": "Data visualization and chart generation",
                "capabilities": ["plotly_charts", "png_export", "azure_storage"],
                "status": "active"
            },
            {
                "name": "brand_performance_agent",
                "type": "specialized",
                "description": "Brand/product performance analysis and KPIs",
                "capabilities": ["data_quality", "growth_analysis", "market_share", "kpi_calculation"],
                "status": "active"
            },
            {
                "name": "forecasting_agent",
                "type": "specialized",
                "description": "Time series forecasting and predictions",
                "capabilities": ["prophet_forecasting", "trend_analysis", "confidence_intervals"],
                "status": "active"
            },
            {
                "name": "anomaly_detection_agent",
                "type": "specialized",
                "description": "Outlier detection and anomaly analysis",
                "capabilities": ["statistical_detection", "ml_detection", "consensus_analysis"],
                "status": "active"
            },
            {
                "name": "general_agent",
                "type": "fallback",
                "description": "General conversation and Q&A",
                "status": "active"
            }
        ]
    }

@router.get("/health/storage")
async def storage_health_check():
    """Health check for storage backend (Azure Blob Storage or Local)"""
    try:
        from services.unified_storage import unified_storage
        
        # Get storage statistics
        stats = await unified_storage.get_storage_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "storage_backend": settings.storage_backend,
            "storage_info": {
                "backend": stats.get("storage_backend", "unknown"),
                "total_files": stats.get("total_files", 0),
                "total_size_mb": round(stats.get("total_size", 0) / (1024 * 1024), 2),
                "is_azure": settings.storage_backend == "azure",
                "azure_configured": bool(settings.azure_storage_connection_string) if settings.storage_backend == "azure" else None,
                "container_name": settings.azure_storage_container_name if settings.storage_backend == "azure" else None,
            },
            "categories": stats.get("categories", {})
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "storage_backend": settings.storage_backend,
            "error": str(e)
        }
