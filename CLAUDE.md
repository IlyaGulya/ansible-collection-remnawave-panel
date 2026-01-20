# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a code generator that produces Ansible modules from the Remnawave Panel OpenAPI specification. The generated modules manage resources (nodes, config profiles) in a Remnawave VPN panel via its REST API.

## Commands

### Generator Commands

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
```

### Testing with tox-ansible

Used for sanity and unit tests with automatic Python/Ansible version matrix:

```bash
cd ansible_collections/remnawave/panel

# List available test environments
tox list --ansible --conf tox-ansible.ini

# Run sanity tests
tox --ansible -e sanity-py3.11-2.18 --conf tox-ansible.ini

# Run unit tests
tox --ansible -e unit-py3.11-2.18 --conf tox-ansible.ini
```

### E2E Tests with Molecule

E2E tests run directly via molecule (not through tox-ansible due to pytest-ansible path limitations):

```bash
cd ansible_collections/remnawave/panel

# Run full E2E test sequence
uv run molecule test -s e2e

# Run individual stages for debugging
uv run molecule create -s e2e    # Start containers
uv run molecule converge -s e2e  # Run tests
uv run molecule verify -s e2e    # Verify cleanup
uv run molecule destroy -s e2e   # Teardown
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

- **tox-ansible**: Used for sanity and unit tests with automatic Python/Ansible version matrix
  - `tox-ansible.ini`: Version skip rules (skips py3.9/3.10, ansible < 2.15)
  - `test-requirements.txt`: Test dependencies
- **Molecule E2E tests**: `extensions/molecule/e2e/`
  - Uses Caddy reverse proxy to inject required `X-Forwarded-Proto: https` header
  - PostgreSQL + Valkey + Backend containers via docker-compose
  - Ansible-native create/destroy playbooks

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

- **ANSIBLE_COLLECTIONS_PATH**: Configured in `molecule.yml` via `MOLECULE_PROJECT_DIRECTORY` environment variable
- **molecule_scenario_directory**: Use this variable in playbooks for file paths (e.g., for `.api-token` file location)

## Documentation Style

### Xray Config Format

When writing examples that include Xray configuration (the `config` parameter with inbounds, outbounds, routing), always use JSON syntax (as a YAML object, not a string). This matches how Xray configs are typically written and makes examples more recognizable to users familiar with Xray.

```yaml
# Good - JSON syntax for entire config
- name: Create config profile
  remnawave.panel.config_profile:
    state: present
    name: "my-profile"
    config:
      {
        "inbounds": [
          {
            "tag": "vless-tcp",
            "protocol": "vless",
            "port": 443,
            "settings": {}
          }
        ]
      }

# Bad - YAML format for config
- name: Create config profile
  remnawave.panel.config_profile:
    state: present
    name: "my-profile"
    config:
      inbounds:
        - tag: "vless-tcp"
          protocol: "vless"
          port: 443
          settings: {}
```
