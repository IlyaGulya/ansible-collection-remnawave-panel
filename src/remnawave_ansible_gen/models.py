"""Data models for the Remnawave Ansible Module Generator."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveredEndpoint:
    """Discovered endpoint configuration."""

    path: str
    method: str
    dto: str | None = None
    response_dto: str | None = None


@dataclass
class DiscoveredResource:
    """Auto-discovered resource from OpenAPI spec."""

    controller_tag: str
    resource_name: str  # "Node"
    module_name: str  # "rw_node"
    base_path: str  # "/api/nodes"
    id_param: str  # "uuid" or "name"
    lookup_field: str  # "name"
    description: str | None = None  # Override from config
    endpoints: dict[str, DiscoveredEndpoint] = field(default_factory=dict)
    fields: list[dict[str, Any]] = field(default_factory=list)
    read_only_fields: list[str] = field(default_factory=list)
    resolve_uuid_by_name: bool = False  # Enable config profile name resolution
