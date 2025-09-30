"""
Agent-Chat Main Application - LangGraph Multi-Agent Platform
FastAPI application with LangGraph 0.6.8 orchestration and GPT-5 via Requesty AI
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db, close_db
from api import chat, files, health, charts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Agent-Chat Backend (LangGraph 0.6.8)...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Initialize Azure sync if using Azure storage
    if settings.storage_backend == 'azure':
        try:
            from services.azure_sync import azure_sync_service
            from core.database import get_db

            print("🔄 Starting Azure Blob Storage sync...")

            # Perform initial sync on startup
            async for db in get_db():
                try:
                    sync_result = await azure_sync_service.sync_azure_to_database(db)
                    if sync_result['status'] == 'success':
                        print(f"✅ Azure sync completed: {sync_result.get('added', 0)} files added, {sync_result.get('updated', 0)} updated")
                    else:
                        print(f"⚠️ Azure sync had issues: {sync_result}")
                except Exception as e:
                    print(f"❌ Azure sync failed: {str(e)}")
                finally:
                    break  # Exit the async for loop

            # Start background sync task
            await azure_sync_service.start_background_sync()
            print("✅ Azure background sync started")

        except Exception as e:
            print(f"⚠️ Failed to initialize Azure sync: {str(e)}")
            # Don't fail startup, continue without sync

    # LangGraph agents are initialized on demand via graph.py
    print("✅ LangGraph agents ready:")
    print("   - Supervisor (GPT-5 routing)")
    print("   - Chart Agent (Plotly + PNG)")
    print("   - Brand Performance Agent (KPIs + Analytics)")
    print("   - Forecasting Agent (Prophet + Trends)")
    print("   - Anomaly Detection Agent (Statistical + ML)")
    print("   - General Agent (Conversation)")

    print("🎯 Agent-Chat Backend ready!")
    yield

    # Shutdown
    print("🛑 Shutting down Agent-Chat Backend...")

    # Stop Azure sync if running
    if settings.storage_backend == 'azure':
        try:
            from services.azure_sync import azure_sync_service
            await azure_sync_service.stop_background_sync()
            print("✅ Azure sync stopped")
        except Exception as e:
            print(f"⚠️ Failed to stop Azure sync: {str(e)}")

    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Agent-Chat API - Agion AI Platform",
    description="LangGraph 0.6.8 Multi-Agent Orchestration Platform powered by GPT-5 via Requesty AI",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Accept"],  # Specific headers only
    max_age=3600,  # Cache preflight for 1 hour
)

# Include routers
app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
app.include_router(chat.router, prefix=settings.api_prefix, tags=["chat"])
app.include_router(files.router, prefix=settings.api_prefix, tags=["files"])
app.include_router(charts.router, prefix=settings.api_prefix, tags=["charts"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Agent-Chat API - Agion AI Platform",
        "version": "2.0.0",
        "framework": "LangGraph 0.6.8",
        "model": "GPT-5 via Requesty AI",
        "status": "operational",
        "agents": 6,
        "docs": "/docs" if not settings.is_production else "Contact admin for API documentation"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "server_error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )