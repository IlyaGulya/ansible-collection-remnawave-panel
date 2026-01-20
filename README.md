# Remnawave Ansible Collection

Ansible collection for managing [Remnawave](https://github.com/remnawave/panel) VPN panel resources.

**Collection version:** 0.1.0 (generated from Remnawave API 2.5.3)

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Available Modules](#available-modules)
- [Authentication](#authentication)
- [Usage Examples](#usage-examples)
- [Common Parameters](#common-parameters)
- [Important Notes](#important-notes)
- [Module Features](#module-features)
- [Requirements](#requirements)

## Installation

```bash
ansible-galaxy collection install remnawave.panel
```

Or add to `requirements.yml`:

```yaml
collections:
  - name: remnawave.panel
    version: ">=0.1.0"
```

## Quick Start

1. Set your credentials:
   ```bash
   export REMNAWAVE_API_URL="https://panel.example.com"
   export REMNAWAVE_API_TOKEN="your-api-token"
   ```

2. Create a playbook (`playbook.yml`):
   ```yaml
   - hosts: localhost
     tasks:
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
   ```

3. Run it:
   ```bash
   ansible-playbook playbook.yml
   ```

## Available Modules

| Module | Description |
|--------|-------------|
| `remnawave.panel.node` | Manage panel nodes |
| `remnawave.panel.config_profile` | Manage configuration profiles |

## Authentication

All modules require API credentials:

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `api_url` | `REMNAWAVE_API_URL` | Panel API URL |
| `api_token` | `REMNAWAVE_API_TOKEN` | API token |

Create an API token in the Remnawave panel under Settings > API Tokens.

## Usage Examples

### Managing Config Profiles

```yaml
- name: Create a config profile
  remnawave.panel.config_profile:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: present
    name: "production-config"
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

- name: Delete a config profile
  remnawave.panel.config_profile:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: absent
    name: "production-config"
```

### Managing Nodes

```yaml
- name: Create a node (using name-based lookup)
  remnawave.panel.node:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: present
    name: "edge-server-1"
    address: "192.168.1.100"
    port: 443
    config_profile:
      active_config_profile: "production-config"  # Reference by name
      active_inbound_tags:
        - "vless-tcp"  # Reference by tag

- name: Delete a node
  remnawave.panel.node:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: absent
    name: "edge-server-1"
```

### Using Environment Variables

```yaml
- name: Create node using environment credentials
  remnawave.panel.node:
    state: present
    name: "edge-server-1"
    address: "192.168.1.100"
    config_profile:
      active_config_profile: "production-config"
      active_inbound_tags:
        - "vless-tcp"
  environment:
    REMNAWAVE_API_URL: "https://panel.example.com"
    REMNAWAVE_API_TOKEN: "{{ vault_api_token }}"
```

### Node Traffic Tracking

The `node` module supports traffic tracking parameters:

```yaml
- name: Create node with traffic limits
  remnawave.panel.node:
    state: present
    name: "edge-server-1"
    address: "192.168.1.100"
    config_profile:
      active_config_profile: "production-config"
      active_inbound_tags:
        - "vless-tcp"
    is_traffic_tracking_active: true
    traffic_limit_bytes: 107374182400  # 100 GB
    notify_percent: 80                  # Alert at 80% usage
    traffic_reset_day: 1                # Reset on 1st of month
```

For more examples including workflows, multi-region deployments, and production patterns, see the [examples directory](ansible_collections/remnawave/panel/examples/).

## Common Parameters

All modules support these additional parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `validate_certs` | `true` | Set to `false` for self-signed certificates |
| `timeout` | `30` | API request timeout in seconds |

## Important Notes

- **Config profiles first**: Nodes require a config profile. Always create profiles before nodes.
- **Inbounds required**: Config profiles must have at least one inbound defined. Empty `inbounds: []` will fail validation.
- **Name-based lookup**: You can reference resources by name instead of UUID for better readability (see examples above).
- **Self-signed certs**: Use `validate_certs: false` for panels with self-signed certificates.

## Module Features

All modules support:

- **Idempotency**: Resources are only modified when changes are needed
- **Check mode**: Use `--check` to preview changes without applying them
- **Diff mode**: Use `--diff` to see what would change
- **Lookup by name or UUID**: Reference resources by either identifier

## Requirements

- Ansible >= 2.15
- Python >= 3.11
- Remnawave Panel >= 2.5.0

## License

MIT

## Links

- [Remnawave Panel](https://github.com/remnawave/panel)
- [Remnawave Documentation](https://docs.remnawave.com)
