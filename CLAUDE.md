# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a code generator that produces Ansible modules from the Remnawave Panel OpenAPI specification. The generated modules manage resources (nodes, config profiles) in a Remnawave VPN panel via its REST API.

## Commands

```bash
# Install dependencies
uv sync --all-extras

# Run the code generator (regenerates modules from OpenAPI spec)
uv run generate

# Run linter on generator code
uv run ruff check src/

# Check if generated code is in sync with spec
bash scripts/check-freshness.sh

# Run Molecule tests (mock API using Prism)
npm install -g @stoplight/prism-cli   # one-time setup
prism mock api-spec/api-1.yaml -p 4010 &
uv run molecule test

# Run E2E tests (real Remnawave backend in Docker)
# Molecule handles setup/teardown automatically
uv run molecule test -s e2e

# E2E debugging mode (manual control over environment lifecycle)
# Use these scripts ONLY when debugging tests step-by-step
bash scripts/e2e-setup.sh            # Start containers, get API token
uv run molecule converge -s e2e      # Run converge only (no setup/teardown)
uv run molecule verify -s e2e        # Run verify only
bash scripts/e2e-teardown.sh         # Cleanup when done
```

## Architecture

### Code Generation Flow

```
api-spec/api-1.yaml (OpenAPI spec)
         ↓
src/remnawave_ansible_gen/config.yaml (module definitions + read-only fields)
         ↓
src/remnawave_ansible_gen/generate.py (generator)
         ↓
src/remnawave_ansible_gen/templates/*.j2 (Jinja2 templates)
         ↓
collection/plugins/modules/*.py (generated Ansible modules)
collection/plugins/module_utils/remnawave.py (generated shared utilities)
```

### Key Files

- **`src/remnawave_ansible_gen/config.yaml`**: Defines modules to generate, their endpoints, and `read_only_fields` excluded from idempotency checks
- **`src/remnawave_ansible_gen/generate.py`**: Parses OpenAPI spec and renders Jinja2 templates
- **`collection/plugins/module_utils/remnawave.py`**: Generated HTTP client with `get_all()` that extracts lists from nested API responses, plus `recursive_diff()` for idempotency
- **`collection/plugins/modules/rw_*.py`**: Generated Ansible modules (DO NOT EDIT - regenerate instead)

### Testing Infrastructure

- **`molecule/default/`**: Mock tests using Prism OpenAPI mock server on port 4010
- **`molecule/e2e/`**: E2E tests against real Remnawave backend in Docker
  - Uses Caddy reverse proxy to inject required `X-Forwarded-Proto: https` header
  - PostgreSQL + Valkey + Backend containers via docker-compose

## Remnawave API Quirks

These behaviors were discovered during implementation and are important for module development:

1. **Header Requirements**: API requires `X-Forwarded-Proto: https` header (simulating reverse proxy). E2E tests use Caddy proxy for this.

2. **API Token Creation**: Creating API tokens via JWT requires `X-Remnawave-Client-Type: browser` header.

3. **Config Profile Validation**: Config profiles must have at least one inbound in the config. Empty `inbounds: []` fails validation.

4. **Node Response Structure**: The `activeInbounds` array is not returned by the API in node responses, so it's in `read_only_fields` to prevent false idempotency failures.

5. **List Endpoints**: API returns `{"response": {"total": N, "items": [...]}}` where `items` key varies (e.g., `configProfiles`, `nodes`). The `get_all()` method handles this by finding the first list in the response.

## Remnawave Source Access

If you need to understand Remnawave internals (API behavior, error codes, authentication flow), clone repositories into `.claudetmp/`:

```bash
git clone https://github.com/remnawave/backend.git .claudetmp/backend
git clone https://github.com/remnawave/node.git .claudetmp/node
git clone https://github.com/remnawave/panel.git .claudetmp/panel
```

Useful locations in backend:
- `libs/contract/constants/errors/errors.ts` - Error codes (A032, A112, etc.)
- `libs/contract/commands/` - Zod request/response schemas
- `src/common/helpers/xray-config/` - Config validation logic
