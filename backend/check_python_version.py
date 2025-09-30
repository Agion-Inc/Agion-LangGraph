#!/usr/bin/env python3
"""
Python Version Checker for Agent-Chat
Ensures we're running Python 3.13 or higher
"""

import sys
import platform

def check_python_version():
    """Check if Python version meets requirements"""
    
    # Get version info
    version_info = sys.version_info
    version_str = platform.python_version()
    implementation = platform.python_implementation()
    
    print("=" * 50)
    print("🐍 Python Version Check")
    print("=" * 50)
    print(f"Python Version: {version_str}")
    print(f"Implementation: {implementation}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print("=" * 50)
    
    # Minimum required version
    min_version = (3, 13, 0)
    
    if version_info >= min_version:
        print(f"✅ Python {version_str} meets requirements")
        print(f"   Minimum required: Python {'.'.join(map(str, min_version))}")
        
        # Python 3.13 specific features
        print("\n📋 Python 3.13 Features Available:")
        print("   • Improved performance (10-15% faster)")
        print("   • Better error messages with more context")
        print("   • Enhanced asyncio performance")
        print("   • Improved type hints and typing")
        print("   • Better memory management")
        print("   • Free-threaded CPython (experimental)")
        
        return True
    else:
        print(f"❌ Python {version_str} does not meet requirements")
        print(f"   Minimum required: Python {'.'.join(map(str, min_version))}")
        print("\n📥 To upgrade to Python 3.13:")
        print("   • macOS: brew install python@3.13")
        print("   • Ubuntu/Debian: apt install python3.13")
        print("   • Windows: Download from python.org")
        print("   • Docker: Use python:3.13-slim base image")
        
        return False

if __name__ == "__main__":
    if not check_python_version():
        sys.exit(1)
    sys.exit(0)
