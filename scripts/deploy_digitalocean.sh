#!/bin/bash
# =============================================================================
# EVAonline - DigitalOcean Droplet Deploym  ent Script
# =============================================================================
# Run this script on a fresh Ubuntu 22.04+ Droplet with Docker pre-installed
# Usage: bash deploy_digitalocean.sh
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "=============================================="
echo "  EVAonline - DigitalOcean Deployment"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Step 1: System Update & Security
# -----------------------------------------------------------------------------
log_info "Step 1/9: Updating system and installing security tools..."

apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq fail2ban ufw curl git nano htop

# Configure fail2ban for SSH brute-force protection
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

systemctl enable fail2ban
systemctl restart fail2ban
log_ok "System updated, fail2ban configured"

# -----------------------------------------------------------------------------
# Step 2: Firewall Configuration (UFW)
# -----------------------------------------------------------------------------
log_info "Step 2/9: Configuring firewall (only SSH, HTTP, HTTPS)..."

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Nginx)
ufw allow 443/tcp   # HTTPS (Nginx + SSL)
ufw --force enable

log_ok "Firewall active: only ports 22, 80, 443 open"

# -----------------------------------------------------------------------------
# Step 3: Verify Docker
# -----------------------------------------------------------------------------
log_info "Step 3/9: Verifying Docker installation..."

if ! command -v docker &> /dev/null; then
    log_warn "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! docker compose version &> /dev/null; then
    log_error "Docker Compose V2 not available. Please install Docker Compose."
    exit 1
fi

docker --version
docker compose version
log_ok "Docker is ready"

# -----------------------------------------------------------------------------
# Step 4: Clone Repository
# -----------------------------------------------------------------------------
log_info "Step 4/9: Cloning EVAonline repository..."

APP_DIR="/opt/evaonline"

if [ -d "$APP_DIR" ]; then
    log_warn "Directory $APP_DIR already exists. Pulling latest..."
    cd "$APP_DIR"
    git pull origin main
else
    git clone https://github.com/angelacunhasoares/EVAONLINE.git "$APP_DIR"
    cd "$APP_DIR"
fi

log_ok "Repository cloned to $APP_DIR"

# -----------------------------------------------------------------------------
# Step 5: Generate Secure Credentials & Create .env
# -----------------------------------------------------------------------------
log_info "Step 5/9: Generating secure credentials..."

# Generate random passwords
POSTGRES_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
REDIS_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
GRAFANA_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
FLOWER_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Get Droplet public IP
DROPLET_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || curl -s ifconfig.me)

cat > "$APP_DIR/.env" << ENVEOF
# =============================================================================
# EVAonline - Production Configuration (Auto-generated)
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Server IP: ${DROPLET_IP}
# =============================================================================

# AMBIENTE
ENVIRONMENT=production
DEBUG=False
PYTHONUNBUFFERED=1
PYTHONUTF8=1

# BANCO DE DADOS
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=evaonline
POSTGRES_PASSWORD=${POSTGRES_PASS}
POSTGRES_DB=evaonline
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30

# REDIS
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${REDIS_PASS}
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=10
REDIS_SOCKET_CONNECT_TIMEOUT=5

# CELERY
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_TASK_SOFT_TIME_LIMIT=300
CELERY_TASK_TIME_LIMIT=600

# CACHE
CACHE_TTL=1800
CACHE_SHORT_TTL=300
CACHE_LONG_TTL=3600
CACHE_ENABLED=True
CACHE_COMPRESSION=True
CACHE_KEY_PREFIX=evaonline

# APIs EXTERNAS
NASA_POWER_URL=https://power.larc.nasa.gov/api/temporal/daily/point
NASA_POWER_TIMEOUT=30
OPENMETEO_ARCHIVE_URL=https://archive-api.open-meteo.com/v1/archive
OPENMETEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
OPENMETEO_TIMEOUT=30
MET_NORWAY_URL=https://api.met.no/weatherapi/locationforecast/2.0/complete
MET_NORWAY_TIMEOUT=30
FROST_CLIENT_ID=YOUR_FROST_CLIENT_ID_HERE
FROST_CLIENT_SECRET=YOUR_FROST_CLIENT_SECRET_HERE
FROST_AUTH_URL=https://frost.met.no/auth/accessToken
FROST_OBSERVATIONS_URL=https://frost.met.no/observations/v0.jsonld
FROST_AVAILABLE_TIMESERIES_URL=https://frost.met.no/observations/availableTimeSeries/v0.jsonld
FROST_TIMEOUT=30
NWS_BASE_URL=https://api.weather.gov
NWS_TIMEOUT=30
EXTERNAL_API_RATE_LIMIT=1000
EXTERNAL_API_MAX_RETRIES=3
EXTERNAL_API_RETRY_DELAY=1.0

# USER AGENTS
MET_NORWAY_USER_AGENT=EVAonline/1.0 (https://github.com/angelacunhasoares/EVAONLINE)
NWS_USER_AGENT=(EVAonline/1.0, https://github.com/angelacunhasoares/EVAONLINE)

# MONITORAMENTO
PROMETHEUS_ENABLED=True
PROMETHEUS_PORT=8001
LOG_LEVEL=INFO
LOG_FORMAT=json
HEALTH_CHECK_ENDPOINT=/api/v1/health
READINESS_ENDPOINT=/api/v1/ready

# SEGURANÇA
SECRET_KEY=${SECRET}
BACKEND_CORS_ORIGINS=["http://${DROPLET_IP}","http://${DROPLET_IP}:80","https://${DROPLET_IP}","https://evaonline.app.br","https://www.evaonline.app.br"]
CORS_ALLOW_CREDENTIALS=True
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
SECURE_HEADERS_ENABLED=True
SECURE_HEADERS_HSTS=False
SECURE_HEADERS_CSP=True

# PERFORMANCE
API_MAX_CONNECTIONS=50
API_TIMEOUT=30

# TIMEZONE
TZ=America/Sao_Paulo
LANG=pt_BR.UTF-8
LC_ALL=pt_BR.UTF-8

# DASH
DASH_URL_BASE_PATHNAME=/
DASH_ASSETS_FOLDER=frontend/assets
DASH_COMPRESS_ASSETS=True
DASH_INCLUDE_ASSETS_FILES=True
DASH_DEBUG=False
FASTAPI_RELOAD=False

# EMAIL (configure com suas credenciais reais)
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@evaonline.com
SMTP_USE_TLS=true

# NGINX
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# GRAFANA
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASS}

# FLOWER
FLOWER_USER=admin
FLOWER_PASSWORD=${FLOWER_PASS}

# DOCKER
COMPOSE_PROJECT_NAME=evaonline
ENVEOF

chmod 600 "$APP_DIR/.env"
log_ok "Production .env created with secure credentials"

# Save credentials to a secure file for the admin
cat > /root/evaonline_credentials.txt << CREDEOF
=============================================================================
EVAonline - Server Credentials (KEEP THIS FILE SECURE!)
Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
=============================================================================

Server IP:          ${DROPLET_IP}
App URL:            http://${DROPLET_IP}

PostgreSQL:
  User:             evaonline
  Password:         ${POSTGRES_PASS}
  Database:         evaonline

Redis Password:     ${REDIS_PASS}

Secret Key:         ${SECRET}

Grafana:
  URL:              http://${DROPLET_IP}/grafana/
  User:             admin
  Password:         ${GRAFANA_PASS}

Flower:
  URL:              http://${DROPLET_IP}/flower/
  User:             admin
  Password:         ${FLOWER_PASS}

=============================================================================
CREDEOF

chmod 600 /root/evaonline_credentials.txt
log_ok "Credentials saved to /root/evaonline_credentials.txt"

# -----------------------------------------------------------------------------
# Step 6: Create required directories
# -----------------------------------------------------------------------------
log_info "Step 6/9: Creating required directories..."

mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/data"
mkdir -p "$APP_DIR/temp"
mkdir -p "$APP_DIR/docker/nginx/ssl"

log_ok "Directories created"

# -----------------------------------------------------------------------------
# Step 7/9: Build and Start Services (HTTP only initially)
# -----------------------------------------------------------------------------
log_info "Step 7/9: Building and starting Docker services..."
log_warn "This may take 5-10 minutes on first build..."

cd "$APP_DIR"

# Build all images
docker compose build --no-cache 2>&1 | tail -5

# Generate self-signed certs so Nginx can start with HTTPS block
# (will be replaced by Let's Encrypt in Step 8)
if [ ! -f "$APP_DIR/docker/nginx/ssl/fullchain.pem" ]; then
    log_info "Generating temporary self-signed certificates..."
    openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout "$APP_DIR/docker/nginx/ssl/privkey.pem" \
        -out "$APP_DIR/docker/nginx/ssl/fullchain.pem" \
        -subj "/CN=evaonline.app.br/O=EVAonline" 2>/dev/null
    log_ok "Temporary SSL certificates generated"
fi

# Start services in detached mode
docker compose up -d

log_ok "Docker services started"

# -----------------------------------------------------------------------------
# Step 8/9: SSL Certificate (Let's Encrypt via Certbot)
# -----------------------------------------------------------------------------
log_info "Step 8/9: Obtaining SSL certificate from Let's Encrypt..."

DOMAIN="evaonline.app.br"
EMAIL="your-email@example.com"  # Change to your real email

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    apt-get install -y -qq certbot
fi

# Wait for Nginx to be ready
sleep 10

# Obtain certificate using webroot (Nginx serves /.well-known/acme-challenge/)
certbot certonly --webroot \
    -w /var/lib/docker/volumes/evaonline_certbot_webroot/_data \
    -d "$DOMAIN" -d "www.$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos --non-interactive \
    --deploy-hook "docker compose -f $APP_DIR/docker-compose.yml exec -T nginx nginx -s reload" \
    2>&1 || {
        log_warn "Certbot failed — check DNS A record points to this server"
        log_warn "You can run certbot manually later:"
        log_warn "  certbot certonly --webroot -w /var/lib/docker/volumes/evaonline_certbot_webroot/_data -d $DOMAIN"
        log_warn "Using self-signed certificate for now."
    }

# Copy Let's Encrypt certs to Nginx ssl directory
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$APP_DIR/docker/nginx/ssl/fullchain.pem"
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem "$APP_DIR/docker/nginx/ssl/privkey.pem"
    chmod 644 "$APP_DIR/docker/nginx/ssl/fullchain.pem"
    chmod 600 "$APP_DIR/docker/nginx/ssl/privkey.pem"

    # Re-enable ssl_stapling in nginx.conf for real certificates
    sed -i 's|# ssl_stapling on;|ssl_stapling on;|' "$APP_DIR/docker/nginx/nginx.conf"
    sed -i 's|# ssl_stapling_verify on;|ssl_stapling_verify on;|' "$APP_DIR/docker/nginx/nginx.conf"

    # Reload Nginx with real certificates
    docker compose restart nginx
    log_ok "SSL certificate installed for $DOMAIN"

    # Set up auto-renewal cron job
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $APP_DIR/docker/nginx/ssl/fullchain.pem && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $APP_DIR/docker/nginx/ssl/privkey.pem && docker compose -f $APP_DIR/docker-compose.yml restart nginx'") | crontab -
    log_ok "Auto-renewal cron job configured (daily at 3 AM)"
else
    log_warn "Let's Encrypt certificate not available — using self-signed"
    log_warn "HTTPS will work but browsers will show a security warning"
fi

# -----------------------------------------------------------------------------
# Step 9/9: Health Check
# -----------------------------------------------------------------------------
log_info "Step 9/9: Waiting for services to become healthy..."

sleep 30  # Give services time to start

echo ""
echo "----------------------------------------------"
echo "  Service Status"
echo "----------------------------------------------"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "----------------------------------------------"
echo "  Container Resource Usage"
echo "----------------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "=============================================="
echo -e "  ${GREEN}EVAonline Deployed Successfully!${NC}"
echo "=============================================="
echo ""
echo "  App URL:     https://evaonline.app.br"
echo "  App IP:      http://${DROPLET_IP}"
echo "  Grafana:     https://evaonline.app.br/grafana/"
echo "  Flower:      https://evaonline.app.br/flower/"
echo ""
echo "  Credentials: /root/evaonline_credentials.txt"
echo "  App Dir:     /opt/evaonline"
echo ""
echo "  Useful Commands:"
echo "    docker compose -f /opt/evaonline/docker-compose.yml logs -f"
echo "    docker compose -f /opt/evaonline/docker-compose.yml ps"
echo "    docker compose -f /opt/evaonline/docker-compose.yml restart"
echo ""
echo -e "  ${YELLOW}NEXT STEPS:${NC}"
echo "  1. Change root password:    passwd"
echo "  2. Configure email SMTP:    nano /opt/evaonline/.env"
echo "  3. Verify SSL certificate:  curl -I https://evaonline.app.br"
echo "  4. DigitalOcean Firewall:   Create via DO Control Panel"
echo "  5. Check credentials:       cat /root/evaonline_credentials.txt"
echo "=============================================="
