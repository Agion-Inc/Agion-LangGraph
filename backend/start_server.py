#!/usr/bin/env python3
"""
Simplified Backend Startup Script
Handles Pydantic plugin issues and starts the server cleanly
"""

import os
import sys
import subprocess

def start_backend():
    """Start the backend server with proper environment setup"""
    
    # Disable Pydantic plugins to avoid network timeout issues
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
    
    # Set other environment variables
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    # Ensure we're in the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    print("🚀 Starting Agent-Chat Backend Server...")
    print(f"📁 Working directory: {backend_dir}")
    print("🔧 Pydantic plugins disabled (to avoid timeout issues)")
    print("-" * 50)
    
    # Start uvicorn
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n✋ Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_backend()
