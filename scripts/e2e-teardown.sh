#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
E2E_DIR="$PROJECT_ROOT/molecule/e2e"
ENV_FILE="$E2E_DIR/.env.e2e"

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

cd "$E2E_DIR"

# Stop and remove containers
log_info "Stopping and removing Docker containers..."
if [ -f "$ENV_FILE" ]; then
    docker compose --env-file "$ENV_FILE" down -v --remove-orphans 2>/dev/null || true
else
    docker compose down -v --remove-orphans 2>/dev/null || true
fi

# Remove generated files
log_info "Cleaning up generated files..."
rm -f "$ENV_FILE"
rm -f "$E2E_DIR/.api-token"

log_info "E2E teardown complete"
