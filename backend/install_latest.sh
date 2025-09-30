#!/bin/bash

echo "Upgrading pip first..."
pip3 install --upgrade pip

echo "Installing latest versions of core packages..."

# Core packages
pip3 install --upgrade fastapi uvicorn[standard] pydantic pydantic-settings

# Database
pip3 install --upgrade sqlalchemy aiosqlite alembic

# File processing
pip3 install --upgrade pandas numpy openpyxl python-multipart

# Charting
pip3 install --upgrade matplotlib seaborn plotly

# Web/HTTP
pip3 install --upgrade websockets aiofiles httpx requests

# Utils
pip3 install --upgrade python-dotenv

# Security (basic)
pip3 install --upgrade bcrypt passlib[bcrypt]

echo "Installation complete!"

# Generate updated requirements.txt with installed versions
echo "Generating updated requirements.txt..."
pip3 freeze | grep -E "fastapi|uvicorn|pydantic|sqlalchemy|aiosqlite|alembic|pandas|numpy|openpyxl|python-multipart|matplotlib|seaborn|plotly|websockets|aiofiles|httpx|python-dotenv|bcrypt|passlib" > requirements_latest.txt

echo "Done! Check requirements_latest.txt for installed versions"
