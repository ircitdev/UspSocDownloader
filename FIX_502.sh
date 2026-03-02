#!/bin/bash
# Fix 502 Bad Gateway error
# Run this on server: bash FIX_502.sh

set -e

echo "🔧 Fixing 502 Bad Gateway error..."
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if on server
if [ ! -d "/opt/uspsocdowloader" ]; then
    echo -e "${RED}❌ Must run on server${NC}"
    exit 1
fi

cd /opt/uspsocdowloader

echo -e "${BLUE}📥 Step 1: Pull latest changes${NC}"
git pull origin master
echo ""

echo -e "${BLUE}📁 Step 2: Create help directory if not exists${NC}"
mkdir -p /opt/uspsocdowloader/help
echo ""

echo -e "${BLUE}📄 Step 3: Check if index.html exists${NC}"
if [ ! -f "help/index.html" ]; then
    echo -e "${RED}❌ help/index.html not found!${NC}"
    echo "Creating from git..."
    git checkout help/index.html
fi
ls -lah help/
echo ""

echo -e "${BLUE}🔐 Step 4: Fix permissions${NC}"
chown -R www-data:www-data /opt/uspsocdowloader/help
chmod -R 755 /opt/uspsocdowloader/help
chmod 644 /opt/uspsocdowloader/help/*.html 2>/dev/null || true
echo ""

echo -e "${BLUE}🌐 Step 5: Update Nginx config${NC}"
cat > /etc/nginx/sites-available/socdownloader-docs << 'NGINXCONF'
# Temporary HTTP-only config for testing
server {
    listen 80;
    listen [::]:80;
    server_name socdownloader.tools.uspeshnyy.ru;

    # Root directory
    root /opt/uspsocdowloader/help;
    index index.html;

    # CORS for Telegram Mini Apps
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type" always;

    # Main location
    location / {
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    # Error pages
    error_page 404 /index.html;
    error_page 500 502 503 504 /index.html;

    # Logs
    access_log /var/log/nginx/socdownloader-docs-access.log;
    error_log /var/log/nginx/socdownloader-docs-error.log;
}
NGINXCONF

echo -e "${GREEN}✅ Nginx config updated (HTTP only for now)${NC}"
echo ""

echo -e "${BLUE}🔗 Step 6: Enable site${NC}"
ln -sf /etc/nginx/sites-available/socdownloader-docs /etc/nginx/sites-enabled/
echo ""

echo -e "${BLUE}✔️ Step 7: Test Nginx config${NC}"
nginx -t
echo ""

echo -e "${BLUE}🔄 Step 8: Reload Nginx${NC}"
systemctl reload nginx
echo ""

echo -e "${BLUE}📊 Step 9: Check files${NC}"
echo "Files in help directory:"
ls -lah /opt/uspsocdowloader/help/
echo ""

echo -e "${BLUE}🧪 Step 10: Test HTTP access${NC}"
curl -I http://socdownloader.tools.uspeshnyy.ru 2>/dev/null | head -n 5
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Fix applied!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Test in browser:${NC}"
echo "   http://socdownloader.tools.uspeshnyy.ru"
echo ""
echo -e "${BLUE}After confirming it works, add SSL:${NC}"
echo "   certbot --nginx -d socdownloader.tools.uspeshnyy.ru"
echo ""
