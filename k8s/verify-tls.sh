#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 Verifying TLS/HTTPS Setup for AIRGB${NC}"
echo ""

# Check certificate status
echo -e "${YELLOW}📜 Certificate Status:${NC}"
kubectl get certificate -n agion-airgb
echo ""

# Check certificate details
echo -e "${YELLOW}🔍 Certificate Details:${NC}"
kubectl describe certificate airgb-tls-certificate -n agion-airgb | grep -E "Status:|Ready:|Dns Names:|Issuer Ref:" -A 2
echo ""

# Test HTTPS connectivity
echo -e "${YELLOW}🌐 Testing HTTPS Access:${NC}"
echo -n "Frontend (https://airgb.agion.dev): "
if curl -s -o /dev/null -w "%{http_code}" https://airgb.agion.dev | grep -q "200"; then
    echo -e "${GREEN}✅ Working${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
fi

echo -n "API Health (https://airgb.agion.dev/api/v1/health): "
if curl -s https://airgb.agion.dev/api/v1/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Working${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
fi
echo ""

# Check redirect
echo -e "${YELLOW}🔄 Testing HTTP to HTTPS Redirect:${NC}"
REDIRECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://airgb.agion.dev)
if [ "$REDIRECT_CODE" = "308" ]; then
    echo -e "${GREEN}✅ Redirecting with code 308 (Permanent Redirect)${NC}"
else
    echo -e "${RED}❌ Not redirecting properly (code: $REDIRECT_CODE)${NC}"
fi
echo ""

# Check security headers
echo -e "${YELLOW}🛡️ Security Headers:${NC}"
HEADERS=$(curl -sI https://airgb.agion.dev)
echo "$HEADERS" | grep -i "strict-transport-security" && echo -e "${GREEN}✅ HSTS Present${NC}" || echo -e "${RED}❌ HSTS Missing${NC}"
echo "$HEADERS" | grep -i "x-frame-options" && echo -e "${GREEN}✅ X-Frame-Options Present${NC}" || echo -e "${RED}❌ X-Frame-Options Missing${NC}"
echo "$HEADERS" | grep -i "x-content-type-options" && echo -e "${GREEN}✅ X-Content-Type-Options Present${NC}" || echo -e "${RED}❌ X-Content-Type-Options Missing${NC}"
echo ""

# SSL Certificate info
echo -e "${YELLOW}🔐 SSL Certificate Info:${NC}"
echo | openssl s_client -servername airgb.agion.dev -connect airgb.agion.dev:443 2>/dev/null | openssl x509 -noout -issuer -subject -dates 2>/dev/null | head -3
echo ""

echo -e "${GREEN}✨ TLS Verification Complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Summary:${NC}"
echo "   🔗 Secure URL: https://airgb.agion.dev"
echo "   🔒 Certificate: Let's Encrypt Production"
echo "   🔄 Auto-renewal: Managed by cert-manager"
echo "   🛡️ Security: HSTS, XSS Protection, Frame Options"
