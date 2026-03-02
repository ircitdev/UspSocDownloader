#!/bin/bash
# Quick deployment script for web documentation
# Run this on the server: bash DEPLOY_WEB_DOCS.sh

set -e

echo "🚀 Deploying web documentation for UspSocDownloader..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on server
if [ ! -d "/opt/uspsocdowloader" ]; then
    echo -e "${RED}❌ Error: This script must be run on the production server${NC}"
    echo "Expected directory: /opt/uspsocdowloader"
    exit 1
fi

cd /opt/uspsocdowloader

echo -e "${BLUE}📥 Step 1: Pulling latest changes from GitHub...${NC}"
git pull origin master
echo -e "${GREEN}✅ Done${NC}"
echo ""

echo -e "${BLUE}📁 Step 2: Checking help directory...${NC}"
if [ ! -d "help" ]; then
    echo -e "${RED}❌ Error: help directory not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Help directory exists${NC}"
echo ""

echo -e "${BLUE}🔐 Step 3: Setting permissions...${NC}"
chown -R www-data:www-data help/
chmod -R 755 help/
chmod 644 help/*.html help/*.md 2>/dev/null || true
echo -e "${GREEN}✅ Permissions set${NC}"
echo ""

echo -e "${BLUE}🌐 Step 4: Configuring Nginx...${NC}"
if [ ! -f "/etc/nginx/sites-available/socdownloader-docs" ]; then
    echo "Creating Nginx configuration..."
    cp help/nginx.conf /etc/nginx/sites-available/socdownloader-docs

    # Enable site
    if [ ! -L "/etc/nginx/sites-enabled/socdownloader-docs" ]; then
        ln -s /etc/nginx/sites-available/socdownloader-docs /etc/nginx/sites-enabled/
        echo -e "${GREEN}✅ Nginx site enabled${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  Nginx configuration already exists${NC}"
fi
echo ""

echo -e "${BLUE}✔️  Step 5: Testing Nginx configuration...${NC}"
nginx -t
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration has errors${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}🔒 Step 6: SSL Certificate...${NC}"
if [ ! -d "/etc/letsencrypt/live/socdownloader.tools.uspeshnyy.ru" ]; then
    echo -e "${BLUE}📜 Obtaining SSL certificate...${NC}"
    certbot --nginx -d socdownloader.tools.uspeshnyy.ru --non-interactive --agree-tos --email admin@uspeshnyy.ru --redirect
    echo -e "${GREEN}✅ SSL certificate obtained${NC}"
else
    echo -e "${GREEN}✅ SSL certificate already exists${NC}"
fi
echo ""

echo -e "${BLUE}🔄 Step 7: Reloading Nginx...${NC}"
systemctl reload nginx
echo -e "${GREEN}✅ Nginx reloaded${NC}"
echo ""

echo -e "${BLUE}🤖 Step 8: Restarting bot...${NC}"
systemctl restart uspsocdowloader
sleep 2
if systemctl is-active --quiet uspsocdowloader; then
    echo -e "${GREEN}✅ Bot restarted successfully${NC}"
else
    echo -e "${RED}❌ Bot failed to restart${NC}"
    systemctl status uspsocdowloader
    exit 1
fi
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📱 Test in Telegram:${NC}"
echo "   1. Open @UspSocDownloader_bot"
echo "   2. Send command: /howto"
echo "   3. Click 'Открыть руководство'"
echo ""
echo -e "${BLUE}🌐 Direct URL:${NC}"
echo "   https://socdownloader.tools.uspeshnyy.ru"
echo ""
echo -e "${BLUE}📊 Check logs:${NC}"
echo "   Bot: journalctl -u uspsocdowloader -f"
echo "   Nginx: tail -f /var/log/nginx/socdownloader-docs-access.log"
echo ""
