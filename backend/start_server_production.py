#!/usr/bin/env python3
"""
Production Backend Startup Script for Azure Deployment
Optimized for Azure App Service with Azure Blob Storage
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_environment():
    """Validate required environment variables for production"""
    required_vars = [
        "STORAGE_BACKEND",
        "REQUESTY_AI_API_KEY",
        "JWT_SECRET_KEY"
    ]
    
    # Additional required vars for Azure storage
    if os.getenv("STORAGE_BACKEND") == "azure":
        required_vars.extend([
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER_NAME"
        ])
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in Azure App Service Configuration or .env file")
        sys.exit(1)
    
    logger.info("✅ All required environment variables are set")


def setup_environment():
    """Setup production environment"""
    
    # Disable Pydantic plugins to avoid timeout issues
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
    
    # Ensure unbuffered output for real-time logs
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    # Set production environment
    if not os.getenv("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "production"
    
    # Set default port for Azure App Service
    if not os.getenv("PORT"):
        os.environ["PORT"] = os.getenv("WEBSITES_PORT", "8000")
    
    # Set host to bind to all interfaces
    if not os.getenv("HOST"):
        os.environ["HOST"] = "0.0.0.0"
    
    logger.info(f"🔧 Environment: {os.getenv('ENVIRONMENT')}")
    logger.info(f"📦 Storage Backend: {os.getenv('STORAGE_BACKEND')}")
    
    if os.getenv("STORAGE_BACKEND") == "azure":
        logger.info(f"☁️  Azure Container: {os.getenv('AZURE_STORAGE_CONTAINER_NAME')}")


def run_migrations():
    """Run database migrations if needed"""
    try:
        # Check if alembic is available and migrations exist
        migrations_dir = Path("alembic")
        if migrations_dir.exists():
            logger.info("🔄 Running database migrations...")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info("✅ Database migrations completed")
            else:
                logger.warning(f"⚠️  Migration output: {result.stderr}")
    except Exception as e:
        logger.warning(f"⚠️  Could not run migrations: {e}")


def create_required_directories():
    """Create required directories for local storage"""
    if os.getenv("STORAGE_BACKEND") == "local":
        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created upload directory: {upload_dir}")


def start_server():
    """Start the production server"""
    
    # Ensure we're in the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WEB_CONCURRENCY", "4"))
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Agent-Chat Backend Server (Production)")
    logger.info(f"📁 Working directory: {backend_dir}")
    logger.info(f"🌐 Host: {host}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"👥 Workers: {workers}")
    logger.info("=" * 60)
    
    # Start uvicorn with production settings
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", host,
            "--port", str(port),
            "--workers", str(workers),
            "--log-level", "info",
            "--access-log",
            "--use-colors",
            "--proxy-headers",  # Important for Azure App Service
            "--forwarded-allow-ips", "*"  # Allow proxy headers from Azure
        ])
    except KeyboardInterrupt:
        logger.info("\n✋ Server stopped")
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    try:
        # Validate environment
        validate_environment()
        
        # Setup environment
        setup_environment()
        
        # Create required directories
        create_required_directories()
        
        # Run migrations
        run_migrations()
        
        # Start server
        start_server()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
