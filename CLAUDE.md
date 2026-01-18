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
bash scripts/e2e-setup.sh
uv run molecule test -s e2e
bash scripts/e2e-teardown.sh
```

## Architecture

### Code Generation Flow

```
api-spec/api-1.yaml (OpenAPI spec)
         ↓
src/remnawave_ansible_gen/config.yaml (module definitions)
         ↓
src/remnawave_ansible_gen/generate.py (generator)
         ↓
src/remnawave_ansible_gen/templates/*.j2 (Jinja2 templates)
         ↓
collection/plugins/modules/*.py (generated Ansible modules)
collection/plugins/module_utils/remnawave.py (generated shared utilities)
```

### Key Files

- **`src/remnawave_ansible_gen/config.yaml`**: Defines which modules to generate, their endpoints, and read-only fields to exclude from idempotency checks
- **`src/remnawave_ansible_gen/generate.py`**: Main generator that parses OpenAPI spec and renders Jinja2 templates
- **`collection/plugins/module_utils/remnawave.py`**: Generated shared HTTP client and diff utilities used by all modules
- **`collection/plugins/modules/rw_*.py`**: Generated Ansible modules (DO NOT EDIT - regenerate instead)

### Testing Infrastructure

- **`molecule/default/`**: Mock tests using Prism OpenAPI mock server on port 4010
- **`molecule/e2e/`**: E2E tests against real Remnawave backend (Docker Compose with PostgreSQL, Valkey, backend)

The E2E tests require the Remnawave API to be accessed with `X-Forwarded-Proto: https` header (simulating reverse proxy).

## Remnawave Source Access

If you need to understand Remnawave internals (API behavior, database schema, authentication flow), clone the relevant repositories into `.claudetmp/`:

```bash
git clone https://github.com/remnawave/backend.git .claudetmp/backend
git clone https://github.com/remnawave/node.git .claudetmp/node
git clone https://github.com/remnawave/panel.git .claudetmp/panel
```

## Important Notes

- Files in `collection/plugins/modules/` and `collection/plugins/module_utils/remnawave.py` are auto-generated. To make changes, modify the templates in `src/remnawave_ansible_gen/templates/` or the generator itself, then run `uv run generate`.
- The CI checks that generated code matches the current spec/templates. If you change templates or config, regenerate and commit the output.
- Remnawave API requires API tokens for programmatic access (not JWT tokens). API tokens must currently be created through the admin dashboard.
