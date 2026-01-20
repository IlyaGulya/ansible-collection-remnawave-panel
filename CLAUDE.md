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

# Preview what modules would be generated without writing files
uv run generate --dry-run

# Run linter on generator code
uv run ruff check src/

# Run type checker on generator code
uv run mypy src/

# Check if generated code is in sync with spec
bash scripts/check-freshness.sh

# Run E2E tests (real Remnawave backend in Docker)
# Molecule handles setup/teardown automatically
uv run molecule test -s e2e

# E2E debugging mode (manual control over environment lifecycle)
# Use these scripts ONLY when debugging tests step-by-step
bash scripts/e2e-setup.sh            # Start containers, get API token
uv run molecule converge -s e2e      # Run converge only (no setup/teardown)
uv run molecule verify -s e2e        # Run verify only
bash scripts/e2e-teardown.sh         # Cleanup when done

# Run Ansible sanity tests on collection
cd ansible_collections/remnawave/panel && ansible-test sanity --docker default

# Run Ansible unit tests on collection
cd ansible_collections/remnawave/panel && ansible-test units --docker default -v
```

## Architecture

### Code Generation Flow

```
api-spec/api-1.yaml (OpenAPI spec)
         ↓
    Auto-Discovery (generate.py)
    - Groups operations by controller tag
    - Classifies endpoints (create/update/get_all/get_one/delete)
    - Detects id_param from path parameters
    - Detects lookup_field from Create DTO constraints
    - Computes read_only_fields (response fields - create fields)
         ↓
src/remnawave_ansible_gen/config.yaml (overrides only)
         ↓
src/remnawave_ansible_gen/templates/*.j2 (Jinja2 templates)
         ↓
ansible_collections/remnawave/panel/plugins/modules/*.py (generated Ansible modules)
ansible_collections/remnawave/panel/plugins/module_utils/remnawave.py (generated shared utilities)
```

### Key Files

- **`src/remnawave_ansible_gen/config.yaml`**: Minimal config with:
  - `discovery.include_controllers` / `exclude_controllers` - which controllers to generate
  - `read_only_fields` - global fields excluded from idempotency checks
  - `module_overrides` - per-module fixes for edge cases (extra read_only_fields, custom descriptions)
- **`src/remnawave_ansible_gen/generate.py`**: Auto-discovers module config from OpenAPI spec patterns, then renders Jinja2 templates
- **`ansible_collections/remnawave/panel/plugins/module_utils/remnawave.py`**: Generated HTTP client with `get_all()` that extracts lists from nested API responses, plus `recursive_diff()` for idempotency
- **`ansible_collections/remnawave/panel/plugins/modules/*.py`**: Generated Ansible modules (DO NOT EDIT - regenerate instead)
- **`ansible_collections/remnawave/panel/tests/unit/`**: Unit tests for module_utils

### Testing Infrastructure

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
git clone --depth 1 https://github.com/remnawave/backend.git .claudetmp/backend
git clone --depth 1 https://github.com/remnawave/node.git .claudetmp/node
git clone --depth 1 https://github.com/remnawave/panel.git .claudetmp/panel
```

Useful locations in backend:
- `libs/contract/constants/errors/errors.ts` - Error codes (A032, A112, etc.)
- `libs/contract/commands/` - Zod request/response schemas
- `src/common/helpers/xray-config/` - Config validation logic

## Ansible Collections Development documentation

If you need to understand how to develop ansible collections, clone repository into `.claudetmp/`:

```bash
git clone --depth 1 https://github.com/ansible/ansible-documentation.git .claudetmp/ansible-documentation
```

Development documentation is located in:

- `.claudetmp/ansible-documentation/docs/docsite/rst/dev_guide/`

## Molecule Testing Framework

If you need to understand how Molecule works for testing Ansible collections:

```bash
git clone --depth 1 https://github.com/ansible/molecule.git .claudetmp/molecule
```

Useful locations:
- `.claudetmp/molecule/docs/` - Documentation (markdown files)
- `.claudetmp/molecule/src/molecule/` - Source code
- `.claudetmp/molecule/src/molecule/provisioner/` - Provisioner implementation (handles env vars, ansible config)

### Molecule Configuration Notes

- **ansible-native config**: Use `ansible:` section with `env:` for environment variables (modern approach)
- **ANSIBLE_COLLECTIONS_PATH**: Must be relative to scenario directory (e.g., `../..` from `molecule/e2e/` to reach project root)
- **cwd for ansible-playbook**: Molecule runs ansible-playbook from `self._config.scenario_path` (e.g., `molecule/e2e/`), so paths must be relative to that
