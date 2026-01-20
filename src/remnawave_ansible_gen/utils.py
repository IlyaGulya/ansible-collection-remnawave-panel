"""Utility functions for the Remnawave Ansible Module Generator."""

import re
from pathlib import Path
from typing import Any


def to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def map_openapi_type(openapi_type: str, openapi_format: str | None = None) -> str:
    """Map OpenAPI types to Ansible argument spec types."""
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_mapping.get(openapi_type, "str")


def read_pyproject_version(project_root: Path) -> str:
    """Read version from pyproject.toml (source of truth)."""
    pyproject_path = project_root / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def extract_api_version(spec: dict[str, Any]) -> str:
    """Extract API version from OpenAPI spec info.version."""
    return str(spec.get("info", {}).get("version", "unknown"))
