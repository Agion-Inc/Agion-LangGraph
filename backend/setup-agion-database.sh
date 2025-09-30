#!/bin/bash

# Agent-Chat Database Setup Script for Agion PostgreSQL
# This script creates the database and user on your existing Agion PostgreSQL server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Agent-Chat Database Setup for Agion${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check if .env.production exists
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}Loading configuration from .env.production...${NC}"
    source .env.production
fi

# Prompt for PostgreSQL connection details
echo -e "${YELLOW}Please provide your Agion PostgreSQL connection details:${NC}"
echo ""

if [ -z "$AGION_POSTGRES_HOST" ]; then
    read -p "PostgreSQL Host (e.g., your-server.postgres.database.azure.com): " POSTGRES_HOST
else
    POSTGRES_HOST=$AGION_POSTGRES_HOST
    echo "Using PostgreSQL Host: $POSTGRES_HOST"
fi

if [ -z "$AGION_POSTGRES_PORT" ]; then
    read -p "PostgreSQL Port [5432]: " POSTGRES_PORT
    POSTGRES_PORT=${POSTGRES_PORT:-5432}
else
    POSTGRES_PORT=$AGION_POSTGRES_PORT
fi

if [ -z "$AGION_POSTGRES_ADMIN_USER" ]; then
    read -p "PostgreSQL Admin Username: " POSTGRES_ADMIN_USER
else
    POSTGRES_ADMIN_USER=$AGION_POSTGRES_ADMIN_USER
    echo "Using Admin User: $POSTGRES_ADMIN_USER"
fi

# Database configuration
DB_NAME="bpchat_db"
DB_USER="bpchat_user"
READONLY_USER="bpchat_readonly"

echo ""
echo -e "${YELLOW}Database Configuration:${NC}"
echo "  Database Name: $DB_NAME"
echo "  Application User: $DB_USER"
echo "  Read-only User: $READONLY_USER"
echo ""

# Generate secure passwords
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

echo -e "${YELLOW}Generating secure passwords...${NC}"
DB_PASSWORD=$(generate_password)
READONLY_PASSWORD=$(generate_password)

echo -e "${GREEN}✓ Passwords generated${NC}"
echo ""

# Ask for confirmation
echo -e "${YELLOW}This will create:${NC}"
echo "  1. Database: $DB_NAME"
echo "  2. User: $DB_USER (with full access)"
echo "  3. User: $READONLY_USER (read-only access)"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Setup cancelled${NC}"
    exit 1
fi

# Create SQL script with actual passwords
cat > /tmp/bpchat_setup.sql << EOF
-- Create database
CREATE DATABASE $DB_NAME;

-- Create application user
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Create read-only user
CREATE USER $READONLY_USER WITH ENCRYPTED PASSWORD '$READONLY_PASSWORD';

-- Connect to the new database
\c $DB_NAME

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions to application user
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

-- Grant read-only permissions
GRANT CONNECT ON DATABASE $DB_NAME TO $READONLY_USER;
GRANT USAGE ON SCHEMA public TO $READONLY_USER;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO $READONLY_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO $READONLY_USER;

-- Verification query
SELECT 'Database setup complete' as status;
EOF

echo -e "${YELLOW}Connecting to PostgreSQL server...${NC}"
echo "(You will be prompted for the admin password)"
echo ""

# Execute the setup
PGPASSWORD="" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_ADMIN_USER" -d postgres -f /tmp/bpchat_setup.sql

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Database setup complete!${NC}"
    echo ""
    
    # Build connection string
    CONNECTION_STRING="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${DB_NAME}?sslmode=require"
    READONLY_CONNECTION="postgresql+asyncpg://${READONLY_USER}:${READONLY_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${DB_NAME}?sslmode=require"
    
    # Save to environment file
    echo -e "${YELLOW}Saving configuration...${NC}"
    
    cat > .env.production.database << EOF
# Agent-Chat Database Configuration
# Generated: $(date)

# Primary database connection
DATABASE_URL=$CONNECTION_STRING

# Read-only connection (for analytics/monitoring)
DATABASE_URL_READONLY=$READONLY_CONNECTION

# Individual components (for reference)
DB_HOST=$POSTGRES_HOST
DB_PORT=$POSTGRES_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_READONLY_USER=$READONLY_USER
DB_READONLY_PASSWORD=$READONLY_PASSWORD
EOF
    
    echo -e "${GREEN}✓ Configuration saved to .env.production.database${NC}"
    echo ""
    
    # Test the connection
    echo -e "${YELLOW}Testing database connection...${NC}"
    
    python3 << PYTHON_TEST
import asyncio
import sys

async def test_connection():
    try:
        import asyncpg
        conn = await asyncpg.connect('$CONNECTION_STRING')
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        print("✓ Connection successful!")
        print(f"  PostgreSQL: {version.split(',')[0]}")
        return True
    except ImportError:
        print("⚠ asyncpg not installed. Run: pip install asyncpg")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

asyncio.run(test_connection())
PYTHON_TEST
    
    echo ""
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Copy the DATABASE_URL from .env.production.database to your .env.production"
    echo "2. Run database migrations: python -m alembic upgrade head"
    echo "3. Deploy the application"
    echo ""
    echo -e "${YELLOW}Connection strings have been saved to:${NC}"
    echo "  .env.production.database"
    echo ""
    echo -e "${YELLOW}For Azure App Service, set this environment variable:${NC}"
    echo "  DATABASE_URL=$CONNECTION_STRING"
    
else
    echo ""
    echo -e "${RED}✗ Database setup failed${NC}"
    echo "Please check your connection details and try again"
    exit 1
fi

# Cleanup
rm -f /tmp/bpchat_setup.sql
