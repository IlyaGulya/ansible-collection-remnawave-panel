# Remnawave Ansible Collection

Ansible collection for managing [Remnawave](https://github.com/remnawave/panel) VPN panel resources.

**Collection version:** 2.5.3 (aligned with Remnawave API)

## Installation

```bash
ansible-galaxy collection install remnawave.panel
```

Or add to `requirements.yml`:

```yaml
collections:
  - name: remnawave.panel
    version: ">=2.5.3"
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

### Managing Nodes

```yaml
- name: Create a node
  remnawave.panel.node:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: present
    name: "edge-server-1"
    address: "192.168.1.100"
    port: 443
    config_profile:
      active_config_profile_uuid: "{{ profile_uuid }}"
      active_inbounds:
        - "{{ inbound_uuid }}"

- name: Delete a node
  remnawave.panel.node:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: absent
    name: "edge-server-1"
```

### Managing Config Profiles

```yaml
- name: Create a config profile
  remnawave.panel.config_profile:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: present
    name: "production-config"
    config:
      inbounds:
        - tag: "vless-tcp"
          protocol: "vless"
          port: 443
          # ... full xray inbound config

- name: Delete a config profile
  remnawave.panel.config_profile:
    api_url: "https://panel.example.com"
    api_token: "{{ api_token }}"
    state: absent
    name: "production-config"
```

### Using Environment Variables

```yaml
- name: Create node using environment credentials
  remnawave.panel.node:
    state: present
    name: "edge-server-1"
    address: "192.168.1.100"
    config_profile:
      active_config_profile_uuid: "{{ profile_uuid }}"
      active_inbounds: []
  environment:
    REMNAWAVE_API_URL: "https://panel.example.com"
    REMNAWAVE_API_TOKEN: "{{ vault_api_token }}"
```

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
