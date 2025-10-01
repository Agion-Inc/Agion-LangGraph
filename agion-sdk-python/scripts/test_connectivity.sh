#!/bin/bash
# Quick connectivity test script for Agion SDK

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================"
echo "Agion SDK - Backend Connectivity Test"
echo "================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."
GATEWAY_URL="${AGION_GATEWAY_URL:-http://localhost:8080}"
REDIS_URL="${AGION_REDIS_URL:-redis://localhost:6379}"

echo -e "${GREEN}✓${NC} Gateway URL: $GATEWAY_URL"
echo -e "${GREEN}✓${NC} Redis URL:   $REDIS_URL"
echo ""

# Check if SDK is installed
echo "Checking SDK installation..."
if python3 -c "import agion_sdk" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Agion SDK is installed"
else
    echo -e "${YELLOW}!${NC} Agion SDK not found. Installing..."
    cd "$(dirname "$0")/.."
    pip install -e . --quiet
    echo -e "${GREEN}✓${NC} SDK installed"
fi
echo ""

# Check backend services
echo "Checking backend services..."

# Check Gateway
if curl -s -f -m 5 "$GATEWAY_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Gateway is reachable at $GATEWAY_URL"
else
    echo -e "${YELLOW}!${NC} Gateway health check failed at $GATEWAY_URL"
    echo "  (This is OK if Gateway doesn't have /health endpoint)"
fi

# Check Redis
REDIS_HOST=$(echo $REDIS_URL | sed -E 's|redis://([^:]+):.*|\1|')
REDIS_PORT=$(echo $REDIS_URL | sed -E 's|redis://[^:]+:([0-9]+).*|\1|')

if command -v redis-cli &> /dev/null; then
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is reachable at $REDIS_URL"
    else
        echo -e "${RED}✗${NC} Redis is NOT reachable at $REDIS_URL"
        echo "  Please ensure Redis is running"
    fi
else
    echo -e "${YELLOW}!${NC} redis-cli not found, skipping Redis connectivity check"
fi
echo ""

# Run connectivity test
echo "Running SDK connectivity tests..."
echo "================================================================"
echo ""

cd "$(dirname "$0")/.."
python3 -m tests.test_backend_connectivity

echo ""
echo "================================================================"
echo "Test complete!"
echo "================================================================"
