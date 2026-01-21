# Remnawave Ansible Collection Examples

This directory contains example playbooks demonstrating how to use the Remnawave Ansible collection.

> **Note:** These examples are automatically generated. Do not edit them directly.

## Prerequisites

1. Install the collection:
   ```bash
   ansible-galaxy collection install ilyagulya.remnawave
   ```

2. Copy and customize the example variables:
   ```bash
   cp vars/example_vars.yml vars/my_vars.yml
   # Edit my_vars.yml with your API credentials and settings
   ```

## Directory Structure

```
examples/
├── README.md              # This file
├── basic/                 # Simple CRUD operations
│   ├── config_profile_create.yml
│   ├── config_profile_update.yml
│   ├── config_profile_delete.yml
│   ├── node_create.yml
│   ├── node_update.yml
│   └── node_delete.yml
├── workflows/             # Multi-resource workflows
│   ├── setup_infrastructure.yml
│   ├── teardown_infrastructure.yml
│   ├── production_setup.yml
│   └── production_teardown.yml
├── advanced/              # Advanced patterns
│   ├── check_mode.yml
│   └── multi_region_nodes.yml
└── vars/                  # Example variables
    ├── example_vars.yml
    └── production_vars.yml
```

## Basic Examples

### Config Profile Operations

| Playbook | Description |
|----------|-------------|
| `basic/config_profile_create.yml` | Create a new configuration profile with Xray settings |
| `basic/config_profile_update.yml` | Update an existing configuration profile |
| `basic/config_profile_delete.yml` | Delete a configuration profile |

### Node Operations

| Playbook | Description |
|----------|-------------|
| `basic/node_create.yml` | Create a new node with a config profile |
| `basic/node_update.yml` | Update node settings |
| `basic/node_delete.yml` | Delete a node |

## Workflow Examples

### Basic Workflows

| Playbook | Description |
|----------|-------------|
| `workflows/setup_infrastructure.yml` | Basic setup: creates 1 profile and 1 node |
| `workflows/teardown_infrastructure.yml` | Basic teardown: deletes nodes then profile |

### Production Workflows

These workflows demonstrate a realistic multi-region VPN infrastructure with multiple config profiles and nodes.

| Playbook | Description |
|----------|-------------|
| `workflows/production_setup.yml` | Production setup: creates multiple regional profiles and nodes |
| `workflows/production_teardown.yml` | Production teardown: cleanly removes all nodes and profiles |

The production workflows use `vars/production_vars.yml` which includes:
- **3 config profiles** (US, EU, Asia regions with different Xray configurations)
- **6 nodes** across regions (2 US, 2 EU, 2 Asia)
- Per-region traffic limits and settings

## Advanced Examples

| Playbook | Description |
|----------|-------------|
| `advanced/check_mode.yml` | Demonstrates dry-run mode with `--check` flag |
| `advanced/multi_region_nodes.yml` | Loop-based deployment for multiple regions |

## Usage

### Running a Basic Example

```bash
# Using the example variables file
ansible-playbook basic/config_profile_create.yml -e @vars/example_vars.yml

# Or with inline variables
ansible-playbook basic/config_profile_create.yml \
  -e remnawave_api_url=https://panel.example.com \
  -e remnawave_api_token=your-token
```

### Running with Check Mode (Dry Run)

Preview changes without applying them:

```bash
ansible-playbook basic/config_profile_create.yml -e @vars/example_vars.yml --check --diff
```

### Running Workflows

```bash
# Setup complete infrastructure
ansible-playbook workflows/setup_infrastructure.yml -e @vars/example_vars.yml

# Teardown when done
ansible-playbook workflows/teardown_infrastructure.yml -e @vars/example_vars.yml
```

### Multi-Region Deployment

```bash
# Deploy nodes to multiple regions
ansible-playbook advanced/multi_region_nodes.yml -e @vars/example_vars.yml
```

### Production Deployment

Deploy a complete multi-region infrastructure with multiple config profiles:

```bash
# Setup production infrastructure (3 profiles, 6 nodes)
ansible-playbook workflows/production_setup.yml -e @vars/production_vars.yml

# Preview changes first with check mode
ansible-playbook workflows/production_setup.yml -e @vars/production_vars.yml --check --diff

# Teardown production infrastructure
ansible-playbook workflows/production_teardown.yml -e @vars/production_vars.yml
```

## Configuration Reference

### Required Variables

| Variable | Description |
|----------|-------------|
| `remnawave_api_url` | URL of your Remnawave panel (e.g., `https://panel.example.com`) |
| `remnawave_api_token` | API token for authentication |

### Optional Variables

See `vars/example_vars.yml` for basic configuration options including:
- Xray configuration templates
- Node settings
- Traffic tracking options
- Multi-region node definitions

See `vars/production_vars.yml` for production-like configuration including:
- Multiple config profiles by region (US, EU, Asia)
- Multiple nodes with regional assignments
- Per-node traffic limits

## Tips

1. **Idempotency**: All modules are idempotent. Running the same playbook multiple times will only make changes if the desired state differs from the current state.

2. **Check Mode**: Always test with `--check --diff` first to preview changes.

3. **Config Profiles**: Nodes require a config profile. Create the profile before creating nodes.

4. **Inbound Reference**: You can reference inbounds by UUID or by tag name:
   ```yaml
   # By UUID
   active_inbounds:
     - "uuid-here"

   # By tag name (more readable)
   active_inbound_tags:
     - "MainInbound"
   ```

5. **Profile Reference**: You can reference config profiles by UUID or by name:
   ```yaml
   # By UUID
   active_config_profile_uuid: "uuid-here"

   # By name (more readable)
   active_config_profile: "Production Profile"
   ```
