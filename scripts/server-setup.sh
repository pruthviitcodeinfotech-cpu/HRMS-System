#!/usr/bin/env bash
# =============================================================================
# HRMS Server Setup Script
# Run on: 192.168.1.60 (as a user with sudo privileges)
#
# This script:
#   1. Verifies Docker is installed and running
#   2. Verifies Jenkins is running
#   3. Adds jenkins user to docker group (so pipeline can run docker commands)
#   4. Creates required directories and files
#   5. Opens firewall ports
#   6. Prints a summary
#
# Usage:
#   chmod +x server-setup.sh
#   sudo bash server-setup.sh
# =============================================================================

set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'   # No Color

print_section() { echo -e "\n${BLUE}══════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}══════════════════════════════════════════${NC}"; }
print_ok()      { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn()    { echo -e "  ${YELLOW}⚠${NC}  $1"; }
print_fail()    { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${BLUE}→${NC} $1"; }

# =============================================================================
# 1. SYSTEM INFO
# =============================================================================
print_section "System Information"
echo -e "  Hostname  : $(hostname)"
echo -e "  OS        : $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo -e "  Kernel    : $(uname -r)"
echo -e "  Date      : $(date)"
echo -e "  User      : $(whoami)"

# =============================================================================
# 2. DOCKER VERIFICATION & SETUP
# =============================================================================
print_section "Docker Verification"

# Check if Docker is installed
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_ok "Docker is installed: ${DOCKER_VERSION}"
else
    print_fail "Docker is NOT installed!"
    print_info "Installing Docker..."
    # Install Docker (Ubuntu/Debian)
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    print_ok "Docker installed successfully"
fi

# Check Docker service status
if systemctl is-active --quiet docker; then
    print_ok "Docker service is running"
else
    print_warn "Docker service is NOT running — starting it..."
    systemctl enable docker
    systemctl start docker
    sleep 3
    if systemctl is-active --quiet docker; then
        print_ok "Docker service started successfully"
    else
        print_fail "Failed to start Docker service!"
        journalctl -u docker --no-pager -n 20
        exit 1
    fi
fi

# Docker info
print_info "Docker info:"
docker info --format 'Server Version: {{.ServerVersion}} | Storage Driver: {{.Driver}} | OS: {{.OperatingSystem}}' 2>/dev/null || true

# =============================================================================
# 3. JENKINS VERIFICATION
# =============================================================================
print_section "Jenkins Verification"

# Check Jenkins process
if pgrep -f "jenkins" &>/dev/null || systemctl is-active --quiet jenkins 2>/dev/null; then
    print_ok "Jenkins process is running"
else
    print_warn "Jenkins process not detected via pgrep/systemctl"
    print_info "Checking Jenkins via HTTP..."
fi

# Check Jenkins HTTP endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/ 2>/dev/null || echo "000")
if [ "${HTTP_STATUS}" = "200" ] || [ "${HTTP_STATUS}" = "403" ]; then
    # 403 = Jenkins is up but requires authentication (expected)
    print_ok "Jenkins is accessible at http://localhost:8090/ (HTTP ${HTTP_STATUS})"
else
    print_warn "Jenkins HTTP status: ${HTTP_STATUS} — may not be running or uses a different port"
    print_info "Checking for Jenkins on common ports..."
    for PORT in 8080 8090 9090; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/ 2>/dev/null || echo "000")
        [ "${STATUS}" != "000" ] && print_info "Jenkins found on port ${PORT} (HTTP ${STATUS})" && break
    done
fi

# =============================================================================
# 4. ADD JENKINS USER TO DOCKER GROUP
# =============================================================================
print_section "Docker Permissions for Jenkins"

# Determine Jenkins user (could be 'jenkins' or the user Jenkins runs as)
JENKINS_USER="jenkins"

if id "${JENKINS_USER}" &>/dev/null; then
    # Check if already in docker group
    if groups "${JENKINS_USER}" | grep -q docker; then
        print_ok "User '${JENKINS_USER}' is already in the 'docker' group"
    else
        usermod -aG docker "${JENKINS_USER}"
        print_ok "Added '${JENKINS_USER}' to the 'docker' group"
        print_warn "You MUST restart Jenkins for the group change to take effect:"
        print_info "  systemctl restart jenkins"
    fi
else
    print_warn "User '${JENKINS_USER}' does not exist — skipping group add"
    print_info "If Jenkins runs as a different user, add them manually:"
    print_info "  usermod -aG docker <jenkins-user>"
fi

# Also add the current user (itcode) to docker group
CURRENT_USER="${SUDO_USER:-$(whoami)}"
if [ "${CURRENT_USER}" != "root" ]; then
    if groups "${CURRENT_USER}" | grep -q docker; then
        print_ok "User '${CURRENT_USER}' is already in the 'docker' group"
    else
        usermod -aG docker "${CURRENT_USER}"
        print_ok "Added '${CURRENT_USER}' to the 'docker' group"
        print_warn "Log out and back in (or run 'newgrp docker') for the group change to take effect"
    fi
fi

# =============================================================================
# 5. CREATE REQUIRED DIRECTORIES
# =============================================================================
print_section "Creating Required Directories"

# Backend env file location
mkdir -p /etc/hrms
chmod 750 /etc/hrms
print_ok "Created /etc/hrms (backend env files)"

# Backend upload volume mount
mkdir -p /etc/hrms/uploads
chmod 755 /etc/hrms/uploads
print_ok "Created /etc/hrms/uploads (backend file uploads)"

# =============================================================================
# 6. CREATE PLACEHOLDER BACKEND ENV FILE
# =============================================================================
print_section "Backend Environment File"

BACKEND_ENV="/etc/hrms/backend.env"
if [ -f "${BACKEND_ENV}" ]; then
    print_ok "Backend env file already exists: ${BACKEND_ENV}"
else
    cat > "${BACKEND_ENV}" <<'EOF'
# ==========================================================================
# HRMS Backend — Production Environment Variables
# Edit this file with real values before the first deployment.
# ==========================================================================

APP_NAME=HRMS
ENVIRONMENT=production
DEBUG=false
API_V1_PREFIX=/api/v1
SECRET_KEY=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32

HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://192.168.1.60:10015

# ── Database ──────────────────────────────────────────────────────────────
# Update host/port if PostgreSQL runs on a different server
DATABASE_URL=postgresql+asyncpg://hrms:hrms@192.168.1.60:5432/hrms
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# ── Redis ─────────────────────────────────────────────────────────────────
REDIS_URL=redis://192.168.1.60:6379/0
CACHE_TTL_SECONDS=300
REQUIRE_REDIS_IN_PRODUCTION=true

# ── JWT / Auth ────────────────────────────────────────────────────────────
JWT_SECRET=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL=900
REFRESH_TOKEN_TTL=1209600

# ── Rate Limiting ─────────────────────────────────────────────────────────
RATE_LIMIT_ENABLED=true
LOGIN_RATE_LIMIT_ATTEMPTS=10
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
REFRESH_RATE_LIMIT_ATTEMPTS=30
REFRESH_RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_MAX_FAILED_ATTEMPTS=5
LOGIN_FAILURE_WINDOW_SECONDS=900
LOGIN_LOCKOUT_SECONDS=900

# ── Email / SMTP ──────────────────────────────────────────────────────────
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=no-reply@hrms.local

# ── Storage ───────────────────────────────────────────────────────────────
STORAGE_BACKEND=local
UPLOAD_DIR=var/uploads
MAX_UPLOAD_SIZE_MB=10

# ── Background Jobs ───────────────────────────────────────────────────────
QUEUE_BACKEND=redis
WORKER_CONCURRENCY=4
JOB_MAX_TRIES=3
JOB_TIMEOUT_SECONDS=300
JOB_RESULT_TTL_SECONDS=86400
LEAVE_ACCRUAL_CRON_HOUR=1
LEAVE_ACCRUAL_CRON_MINUTE=30
DEVICE_SYNC_INTERVAL_MINUTES=15
SCHEDULER_ENABLED=true

# ── Logging ───────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FORMAT=json

# ── WebSockets ────────────────────────────────────────────────────────────
WS_PATH=/ws
EOF
    chmod 600 "${BACKEND_ENV}"
    print_ok "Created placeholder backend env file: ${BACKEND_ENV}"
    print_warn "⚠️  EDIT ${BACKEND_ENV} with real values before first deployment!"
fi

# =============================================================================
# 7. FIREWALL CONFIGURATION
# =============================================================================
print_section "Firewall Configuration"

if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status | head -1)
    print_info "UFW status: ${UFW_STATUS}"

    # Open required ports
    for PORT_RULE in "10015/tcp" "10016/tcp" "8090/tcp"; do
        ufw allow "${PORT_RULE}" 2>/dev/null && print_ok "Opened port ${PORT_RULE}"
    done

    print_info "Current UFW rules:"
    ufw status numbered 2>/dev/null || true
else
    print_warn "UFW not found — skipping firewall config"
    print_info "Manually open ports: 10015 (frontend), 10016 (backend), 8090 (Jenkins)"

    # Try iptables as fallback
    if command -v iptables &>/dev/null; then
        for PORT in 10015 10016; do
            iptables -C INPUT -p tcp --dport ${PORT} -j ACCEPT 2>/dev/null || \
                iptables -A INPUT -p tcp --dport ${PORT} -j ACCEPT && \
                print_ok "iptables: opened port ${PORT}"
        done
    fi
fi

# =============================================================================
# 8. VERIFY PORTS ARE FREE
# =============================================================================
print_section "Port Availability Check"

for PORT in 10015 10016; do
    if ss -tlnp 2>/dev/null | grep -q ":${PORT} " || netstat -tlnp 2>/dev/null | grep -q ":${PORT} "; then
        print_warn "Port ${PORT} is already in use — existing container may need to be stopped"
        ss -tlnp 2>/dev/null | grep ":${PORT} " || netstat -tlnp 2>/dev/null | grep ":${PORT} " || true
    else
        print_ok "Port ${PORT} is available"
    fi
done

# =============================================================================
# 9. DOCKER NETWORK
# =============================================================================
print_section "Docker Network Setup"

NETWORK_NAME="hrms-network"
if docker network inspect "${NETWORK_NAME}" &>/dev/null; then
    print_ok "Docker network '${NETWORK_NAME}' already exists"
else
    docker network create --driver bridge "${NETWORK_NAME}"
    print_ok "Created Docker network '${NETWORK_NAME}'"
fi

# =============================================================================
# 10. SUMMARY
# =============================================================================
print_section "Setup Summary"

echo ""
echo -e "  ${GREEN}Server IP        :${NC} $(hostname -I | awk '{print $1}')"
echo -e "  ${GREEN}Docker           :${NC} $(docker --version 2>/dev/null | head -1)"
echo -e "  ${GREEN}Docker Service   :${NC} $(systemctl is-active docker 2>/dev/null || echo 'unknown')"
echo -e "  ${GREEN}Jenkins URL      :${NC} http://$(hostname -I | awk '{print $1}'):8090"
echo -e "  ${GREEN}Frontend Port    :${NC} 10015"
echo -e "  ${GREEN}Backend Port     :${NC} 10016"
echo -e "  ${GREEN}Backend Env File :${NC} /etc/hrms/backend.env"
echo -e "  ${GREEN}Backend Uploads  :${NC} /etc/hrms/uploads"
echo ""
echo -e "  ${YELLOW}NEXT STEPS:${NC}"
echo -e "  1. Edit /etc/hrms/backend.env with real DATABASE_URL, REDIS_URL, JWT_SECRET"
echo -e "  2. Restart Jenkins: systemctl restart jenkins"
echo -e "  3. Log into Jenkins at http://$(hostname -I | awk '{print $1}'):8090"
echo -e "  4. Follow CICD_SETUP_GUIDE.md for Jenkins plugin & pipeline configuration"
echo ""
