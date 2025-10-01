#!/usr/bin/env python3
"""
Test Runner for SDK Integration Tests
Handles Pydantic plugin issues
"""

import os
import sys
import subprocess

def run_tests():
    """Run SDK integration tests with proper environment setup"""

    # Disable Pydantic plugins to avoid network timeout issues
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"

    # Ensure we're in the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    print("🧪 Running Agion SDK Integration Tests")
    print(f"📁 Working directory: {backend_dir}")
    print("🔧 Pydantic plugins disabled")
    print("=" * 50)

    # Run tests
    try:
        result = subprocess.run([
            sys.executable, "test_sdk_integration.py"
        ])
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n✋ Tests stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
