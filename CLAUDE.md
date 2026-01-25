# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a code generator that produces Ansible modules from the Remnawave Panel OpenAPI specification. The generated modules manage resources (nodes, config profiles) in a Remnawave VPN panel via its REST API.

## Commands

### Generator Commands

```bash
# Install dependencies
pixi install -e dev

# Run the code generator (regenerates modules from OpenAPI spec)
pixi run generate

# Preview what modules would be generated without writing files
pixi run generate-dry-run

# Run linter on generator code
pixi run lint

# Run type checker on generator code
pixi run typecheck

# Check if generated code is in sync with spec
pixi run check-freshness
```

### Testing with tox-ansible

Used for sanity and unit tests with automatic Python/Ansible version matrix:

```bash
# List available test environments
pixi run tox-list

# Run sanity tests for a specific environment
pixi run tox-sanity sanity-py3.11-2.18

# Run unit tests for a specific environment
pixi run tox-unit unit-py3.11-2.18

# Generate GitHub Actions matrix (for CI)
pixi run tox-matrix-sanity
pixi run tox-matrix-unit
```

### E2E Tests with Molecule

E2E tests run directly via molecule (not through tox-ansible due to pytest-ansible path limitations):

```bash
# Run full E2E test sequence
pixi run molecule-test

# Run individual stages for debugging
pixi run molecule-create    # Start containers
pixi run molecule-converge  # Run tests
pixi run molecule-verify    # Verify cleanup
pixi run molecule-destroy   # Teardown
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
ansible_collections/ilyagulya/remnawave/plugins/modules/*.py (generated Ansible modules)
ansible_collections/ilyagulya/remnawave/plugins/module_utils/remnawave.py (generated shared utilities)
```

### Key Files

- **`src/remnawave_ansible_gen/config.yaml`**: Minimal config with:
  - `discovery.include_controllers` / `exclude_controllers` - which controllers to generate
  - `read_only_fields` - global fields excluded from idempotency checks
  - `module_overrides` - per-module fixes for edge cases (extra read_only_fields, custom descriptions)
- **`src/remnawave_ansible_gen/generate.py`**: Auto-discovers module config from OpenAPI spec patterns, then renders Jinja2 templates
- **`ansible_collections/ilyagulya/remnawave/plugins/module_utils/remnawave.py`**: Generated HTTP client with `get_all()` that extracts lists from nested API responses, plus `recursive_diff()` for idempotency
- **`ansible_collections/ilyagulya/remnawave/plugins/modules/*.py`**: Generated Ansible modules (DO NOT EDIT - regenerate instead)
- **`ansible_collections/ilyagulya/remnawave/tests/unit/`**: Unit tests for module_utils

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
git clone --depth 1 https://github.com/ilyagulya/remnawave.git .claudetmp/panel
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

### Xray Config Format — MANDATORY

**IMPORTANT: This rule applies to EVERY location where Xray configuration appears:**
- Example playbooks (`examples/*.yml`)
- API reference (`docs/api_reference/*.yml`)
- Generator config (`src/remnawave_ansible_gen/config.yaml` — `example_values.config`)
- README files
- Any other documentation or code that shows Xray config

**ALWAYS format Xray configuration (the `config` parameter containing inbounds, outbounds, routing) as a JSON object in YAML, NOT as a native YAML object.**

This means using curly braces `{}`, square brackets `[]`, and quoted keys `"key"`. This matches how Xray configs are typically written and makes examples recognizable to users familiar with Xray.

```yaml
# CORRECT - JSON syntax (curly braces, quoted keys)
- name: Create config profile
  ilyagulya.remnawave.config_profile:
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
        ],
        "outbounds": [
          { "tag": "DIRECT", "protocol": "freedom" }
        ],
        "routing": { "rules": [] }
      }

# WRONG - Native YAML format (no braces, unquoted keys)
- name: Create config profile
  ilyagulya.remnawave.config_profile:
    state: present
    name: "my-profile"
    config:
      inbounds:
        - tag: "vless-tcp"
          protocol: "vless"
          port: 443
          settings: {}
```

**Why JSON format?**
1. Xray documentation uses JSON — users copy-paste from Xray docs
2. Visual distinction — `config:` block is clearly "Xray territory"
3. Consistency — all examples look the same regardless of author
