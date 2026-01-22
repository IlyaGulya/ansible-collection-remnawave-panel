# Remnawave Ansible Collection

[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-ilyagulya.remnawave-blue.svg)](https://galaxy.ansible.com/ui/repo/published/ilyagulya/remnawave/)

Ansible collection for managing [Remnawave](https://github.com/remnawave/panel) VPN panel resources.

## Installation

### From Ansible Galaxy

```bash
ansible-galaxy collection install ilyagulya.remnawave
```

### Using requirements.yml

```yaml
collections:
  - name: ilyagulya.remnawave
    version: ">=0.1.0"
    source: https://galaxy.ansible.com
```

Then install:

```bash
ansible-galaxy collection install -r requirements.yml
```

## Modules

- `ilyagulya.remnawave.node` - Manage panel nodes
- `ilyagulya.remnawave.config_profile` - Manage configuration profiles

## Authentication

```yaml
- name: Example
  ilyagulya.remnawave.node:
    panel_url: "https://panel.example.com"  # or REMNAWAVE_PANEL_URL env
    api_token: "{{ api_token }}"            # or REMNAWAVE_API_TOKEN env
    state: present
    name: "my-node"
    address: "192.168.1.100"
    config_profile:
      active_config_profile: "my-profile"   # Reference by name
      active_inbound_tags:
        - "vless-tcp"                       # Reference by tag
```

## Requirements

- Ansible >= 2.15
- Python >= 3.11
- Remnawave Panel >= 2.5.0

## Repository

https://github.com/IlyaGulya/ansible-collection-remnawave-panel

## License

MIT
