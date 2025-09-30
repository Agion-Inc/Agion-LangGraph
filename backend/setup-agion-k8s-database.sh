#!/bin/bash

# Setup Agent-Chat Database in Agion Kubernetes PostgreSQL
# Creates database and user in the existing agion-data PostgreSQL

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Agent-Chat Database Setup in K8s${NC}"
echo -e "${BLUE}PostgreSQL: agion-data namespace${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Configuration
NAMESPACE="agion-data"
POSTGRES_POD="postgres-0"
DB_NAME="bpchat_db"
DB_USER="bpchat_user"

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

echo -e "${YELLOW}📊 Database Configuration:${NC}"
echo "  Namespace: $NAMESPACE"
echo "  PostgreSQL Pod: $POSTGRES_POD"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Create database and user
echo -e "${YELLOW}🔧 Creating database and user...${NC}"

# First, check if database exists
DB_EXISTS=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}Database $DB_NAME already exists${NC}"
    read -p "Drop and recreate? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME"
        kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -c "DROP USER IF EXISTS $DB_USER"
    else
        echo "Using existing database"
        # Get existing password if possible
        echo -e "${YELLOW}Please provide the existing password for $DB_USER:${NC}"
        read -s DB_PASSWORD
        echo ""
    fi
fi

if [ "$DB_EXISTS" != "1" ] || [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create the database and user
    kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres << EOF
-- Create user
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to the database
\c $DB_NAME

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO $DB_USER;
EOF

    echo -e "${GREEN}✓ Database and user created${NC}"
fi

# Build connection string
CONNECTION_STRING="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres.agion-data.svc.cluster.local:5432/${DB_NAME}"

# Update .env.production
echo -e "${YELLOW}📝 Updating .env.production...${NC}"

# Backup current .env.production
cp .env.production .env.production.backup

# Update the DATABASE_URL in .env.production
sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$CONNECTION_STRING|" .env.production

echo -e "${GREEN}✓ Updated .env.production with PostgreSQL connection${NC}"

# Also save to a separate file for reference
cat > .env.production.database << EOF
# Agion Kubernetes PostgreSQL Configuration
# Generated: $(date)

# Connection for use within Kubernetes cluster
DATABASE_URL=$CONNECTION_STRING

# Individual components
DB_HOST=postgres.agion-data.svc.cluster.local
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# For external access (if needed)
# Use: kubectl port-forward -n agion-data postgres-0 5432:5432
# Then use: postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
EOF

echo -e "${GREEN}✓ Credentials also saved to .env.production.database${NC}"

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Database Setup Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo "Connection String:"
echo "$CONNECTION_STRING"
echo ""
echo "✅ .env.production has been updated with the PostgreSQL connection"
echo "✅ Backup saved as .env.production.backup"
echo ""
echo "Next step: Run ./deploy-to-aks-with-postgres.sh to deploy"
echo ""
