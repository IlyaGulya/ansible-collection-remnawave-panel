# Examples

Real-world playbooks for common Remnawave topologies.

## Prerequisites

Set the `REMNAWAVE_API_TOKEN` environment variable or pass `api_token` directly:

```bash
export REMNAWAVE_API_TOKEN="your-token-here"
```

## Playbooks

### `single_node.yml`

Simplest topology — one config profile with a VLESS inbound, one node.

```bash
ansible-playbook examples/single_node.yml -e panel_url=https://panel.example.com
```

### `multi_hop.yml`

Two-node chain: a relay node (RU) forwards traffic to an exit node (DE).

```bash
ansible-playbook examples/multi_hop.yml -e panel_url=https://panel.example.com
```

### `multi_region_multi_hop.yml`

Multiple exit nodes (DE, NL, US) each with a dedicated relay node (RU). Uses `loop` for DRY configuration.

```bash
ansible-playbook examples/multi_region_multi_hop.yml -e panel_url=https://panel.example.com
```

## Notes

- Replace placeholder keys (`YOUR_PRIVATE_KEY`, `EXIT_PUBLIC_KEY`, etc.) with real X25519 keys.
- The `PLACEHOLDER_UUID` in relay outbound configs is replaced at runtime by Remnawave when users are assigned.
- All examples are idempotent — running them again with the same values produces no changes.

## API Reference

For a complete list of all module options, see [`docs/api_reference/`](../docs/api_reference/).
