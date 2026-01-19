# Remnawave Ansible Collection

Ansible collection for managing [Remnawave](https://github.com/remnawave/panel) VPN panel resources.

## Installation

```bash
ansible-galaxy collection install remnawave.panel
```

## Modules

- `remnawave.panel.node` - Manage panel nodes
- `remnawave.panel.config_profile` - Manage configuration profiles

## Authentication

```yaml
- name: Example
  remnawave.panel.node:
    api_url: "https://panel.example.com"  # or REMNAWAVE_API_URL env
    api_token: "{{ api_token }}"          # or REMNAWAVE_API_TOKEN env
    state: present
    name: "my-node"
    address: "192.168.1.100"
    config_profile:
      active_config_profile_uuid: "..."
      active_inbounds: []
```

## Requirements

- Ansible >= 2.14
- Python >= 3.9
- Remnawave Panel >= 2.5.0

## License

MIT
