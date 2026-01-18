#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
E2E_DIR="$PROJECT_ROOT/molecule/e2e"
ENV_FILE="$E2E_DIR/.env.e2e"

# Test credentials (password without special chars that need escaping)
E2E_USERNAME="e2eadmin"
E2E_PASSWORD="E2eTestPassword1234567890"

# Common curl options for API calls (simulate being behind reverse proxy)
CURL_OPTS=(-H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure clean state by tearing down any existing containers
log_info "Cleaning up any existing containers..."
cd "$E2E_DIR"
docker compose down -v --remove-orphans 2>/dev/null || true

# Generate JWT secrets
log_info "Generating JWT secrets..."
JWT_AUTH_SECRET=$(openssl rand -hex 64)
JWT_API_TOKENS_SECRET=$(openssl rand -hex 64)

# Write environment file
log_info "Writing environment file to $ENV_FILE..."
cat > "$ENV_FILE" << EOF
# Auto-generated E2E test environment - DO NOT COMMIT
APP_PORT=3000
METRICS_PORT=3001
DATABASE_URL=postgresql://postgres:postgres@remnawave-db:5432/postgres
REDIS_HOST=remnawave-redis
REDIS_PORT=6379
JWT_AUTH_SECRET=$JWT_AUTH_SECRET
JWT_API_TOKENS_SECRET=$JWT_API_TOKENS_SECRET
FRONT_END_DOMAIN=*
SUB_PUBLIC_DOMAIN=localhost/api/sub
METRICS_USER=e2e_metrics
METRICS_PASS=e2e_metrics_pass
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
EOF

# Start Docker containers
log_info "Starting Docker containers..."
cd "$E2E_DIR"
docker compose --env-file "$ENV_FILE" up -d

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0
until docker compose --env-file "$ENV_FILE" exec -T remnawave-db pg_isready -U postgres > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        log_error "PostgreSQL failed to become ready"
        docker compose --env-file "$ENV_FILE" logs remnawave-db
        exit 1
    fi
    log_info "Waiting for PostgreSQL... ($attempt/$max_attempts)"
    sleep 2
done
log_info "PostgreSQL is ready"

# Wait for Valkey (Redis) to be ready
log_info "Waiting for Valkey to be ready..."
attempt=0
until docker compose --env-file "$ENV_FILE" exec -T remnawave-redis valkey-cli ping 2>/dev/null | grep -q PONG; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        log_error "Valkey failed to become ready"
        docker compose --env-file "$ENV_FILE" logs remnawave-redis
        exit 1
    fi
    log_info "Waiting for Valkey... ($attempt/$max_attempts)"
    sleep 2
done
log_info "Valkey is ready"

# Wait for backend to be ready (check if API responds with JSON)
log_info "Waiting for backend to be ready..."
attempt=0
max_attempts=15
until response=$(curl -s "${CURL_OPTS[@]}" http://localhost:3000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"_healthcheck_","password":"_healthcheck_"}' 2>&1) && echo "$response" | grep -qE '"(errorCode|statusCode|message)"'; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        log_error "Backend failed to become ready"
        log_error "Last response: $response"
        docker compose --env-file "$ENV_FILE" logs remnawave-backend --tail 50
        exit 1
    fi
    log_info "Waiting for backend API... ($attempt/$max_attempts) - Response: $response"
    sleep 1
done
log_info "Backend is ready"

# Register admin user
log_info "Registering admin user..."
register_response=$(curl -sf "${CURL_OPTS[@]}" http://localhost:3000/api/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$E2E_USERNAME\", \"password\": \"$E2E_PASSWORD\"}" 2>&1) || {
    log_warn "Registration may have failed (user might already exist): $register_response"
}

# Login to get JWT
log_info "Logging in to get JWT..."
login_response=$(curl -sf "${CURL_OPTS[@]}" http://localhost:3000/api/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$E2E_USERNAME\", \"password\": \"$E2E_PASSWORD\"}")

if [ -z "$login_response" ]; then
    log_error "Login failed - empty response"
    exit 1
fi

# Extract JWT from response
jwt_token=$(echo "$login_response" | grep -o '"accessToken":"[^"]*"' | cut -d'"' -f4)
if [ -z "$jwt_token" ]; then
    log_error "Failed to extract JWT from login response: $login_response"
    exit 1
fi
log_info "JWT obtained successfully"

# Create API token (X-Remnawave-Client-Type: browser is required to create tokens via JWT)
log_info "Creating API token..."
token_response=$(curl -s "${CURL_OPTS[@]}" http://localhost:3000/api/tokens \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $jwt_token" \
    -H "X-Remnawave-Client-Type: browser" \
    -d '{"tokenName": "e2e-test-token"}')

log_info "Token creation response: $token_response"

if [ -z "$token_response" ]; then
    log_error "API token creation failed - empty response"
    exit 1
fi

# Extract API token from response
api_token=$(echo "$token_response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
if [ -z "$api_token" ]; then
    log_error "Failed to extract API token from response: $token_response"
    exit 1
fi

log_info "API token created successfully"

# Wait for proxy to be ready
log_info "Waiting for reverse proxy to be ready..."
attempt=0
max_attempts=15
until response=$(curl -s http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"_healthcheck_","password":"_healthcheck_"}' 2>&1) && echo "$response" | grep -qE '"(errorCode|statusCode|message)"'; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        log_error "Proxy failed to become ready"
        log_error "Last response: $response"
        docker compose --env-file "$ENV_FILE" logs remnawave-proxy --tail 20
        exit 1
    fi
    log_info "Waiting for proxy... ($attempt/$max_attempts) - Response: $response"
    sleep 1
done
log_info "Reverse proxy is ready"

# Export the token
echo ""
echo "========================================"
echo "E2E Setup Complete!"
echo "========================================"
echo ""
echo "API Token: $api_token"
echo ""
echo "To use in your shell:"
echo "  export E2E_API_TOKEN='$api_token'"
echo ""

# Write token to file for Molecule to read
echo "$api_token" > "$E2E_DIR/.api-token"

# Also export for current shell if sourced
export E2E_API_TOKEN="$api_token"
