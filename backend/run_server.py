#!/usr/bin/env python3
"""
Agent-Chat Server Startup Script
Quick startup script for development
"""

import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Agent-Chat Backend Server...")
    print("📍 URL: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )