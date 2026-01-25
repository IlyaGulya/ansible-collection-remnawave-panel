"""API reference generation for the Remnawave Ansible Module Generator."""

import json
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment

from .models import DiscoveredResource
from .schema import extract_fields_from_schema, get_schema_by_name
from .utils import to_snake_case


def generate_example_value(field: dict[str, Any], example_values: dict[str, Any] | None = None) -> Any:
    """Generate an example value for a field based on its metadata."""
    snake_name = field["snake_name"]

    # Check config-provided example values first
    if example_values and snake_name in example_values:
        return example_values[snake_name]

    field_type = field["type"]
    name_lower = snake_name.lower()

    if field_type == "bool":
        if "active" in name_lower or "enabled" in name_lower or "tracking" in name_lower:
            return False
        return True

    if field_type == "float":
        return 1.0

    if field_type == "int":
        if "port" in name_lower:
            return 443
        if "percent" in name_lower:
            return 80
        if "bytes" in name_lower:
            return 10737418240
        if "day" in name_lower:
            if field.get("min"):
                return field["min"]
            return 1
        # Use minimum if available
        if field.get("min") is not None:
            return field["min"]
        return 0

    if field_type == "str":
        fmt = field.get("format", "")
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000001"
        max_len = field.get("max_length")
        if max_len and max_len == 2:
            return "US"
        if "name" in name_lower:
            return "example-name"
        if "address" in name_lower:
            return "203.0.113.10"
        if "code" in name_lower and max_len and max_len <= 5:
            return "US"
        return "example-value"

    if field_type == "list":
        elements = field.get("elements", "str")
        if elements == "str":
            if "tag" in name_lower or "inbound" in name_lower:
                fmt = ""
                # Check if items have uuid format from nested info
                if field.get("format") == "uuid":
                    return ["00000000-0000-0000-0000-000000000001"]
                return ["EXAMPLE_TAG"]
            return ["example-item"]
        return []

    if field_type == "dict":
        # Dicts without example_values get an empty dict
        return {}

    return "example-value"


def build_field_comment(field: dict[str, Any]) -> str:
    """Build a YAML comment string summarizing field constraints."""
    parts: list[str] = []

    if field.get("required"):
        parts.append("required")

    parts.append(field["type"])

    if field.get("format"):
        parts.append(f"format: {field['format']}")

    if field.get("min_length") is not None:
        parts.append(f"minLength: {field['min_length']}")
    if field.get("max_length") is not None:
        parts.append(f"maxLength: {field['max_length']}")
    if field.get("min") is not None:
        parts.append(f"min: {field['min']}")
    if field.get("max") is not None:
        parts.append(f"max: {field['max']}")
    if field.get("default") is not None:
        default_val = field["default"]
        if isinstance(default_val, bool):
            default_val = str(default_val).lower()
        parts.append(f"default: {default_val}")

    return ", ".join(parts)


def _format_yaml_value(value: Any, indent: int = 0) -> str:
    """Format a Python value as YAML string with proper indentation."""
    prefix = " " * indent

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        # Quote strings that could be misinterpreted
        if value in ("true", "false", "null", "yes", "no", "on", "off") or not value:
            return f'"{value}"'
        # Quote strings with special chars
        if any(c in value for c in ":#{}[]|>&*!%@`"):
            return f'"{value}"'
        return f'"{value}"'
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                # Format dict items in list
                dict_lines = _format_dict_as_yaml(item, indent + 2)
                # First line gets the "- " prefix
                first_line = dict_lines[0]
                lines.append(f"{prefix}- {first_line.strip()}")
                for dl in dict_lines[1:]:
                    lines.append(f"{prefix}  {dl.strip()}")
            else:
                formatted = _format_yaml_value(item)
                lines.append(f"{prefix}- {formatted}")
        return "\n" + "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = _format_dict_as_yaml(value, indent)
        return "\n" + "\n".join(f"{prefix}{line}" for line in lines)

    return str(value)


def _format_dict_as_yaml(d: dict[str, Any], indent: int = 0) -> list[str]:
    """Format a dict as YAML lines (without the leading newline)."""
    lines: list[str] = []
    for key, val in d.items():
        if isinstance(val, dict) and val:
            lines.append(f"{key}:")
            sub_lines = _format_dict_as_yaml(val, indent + 2)
            for sl in sub_lines:
                lines.append(f"  {sl}")
        elif isinstance(val, list) and val:
            lines.append(f"{key}:")
            for item in val:
                if isinstance(item, dict):
                    dict_lines = _format_dict_as_yaml(item, indent + 2)
                    lines.append(f"  - {dict_lines[0]}")
                    for dl in dict_lines[1:]:
                        lines.append(f"    {dl}")
                else:
                    formatted = _format_yaml_value(item)
                    lines.append(f"  - {formatted}")
        else:
            formatted = _format_yaml_value(val)
            lines.append(f"{key}: {formatted}")
    return lines


def _format_json_block(value: Any, base_indent: int) -> str:
    """Format a value as a JSON block indented under a YAML key."""
    json_str = json.dumps(value, indent=2, ensure_ascii=False)
    prefix = " " * base_indent
    lines = json_str.split("\n")
    indented_lines = [f"{prefix}{line}" for line in lines]
    return "\n" + "\n".join(indented_lines)


def _render_field_line(
    snake_name: str,
    value: Any,
    comment: str,
    base_indent: int,
    json_format: bool = False,
) -> str:
    """Render a single field as a YAML line with comment."""
    indent = " " * base_indent

    if json_format and isinstance(value, dict) and value:
        # Render as JSON block (for freeform dict fields like xray config)
        formatted = _format_json_block(value, base_indent + 2)
        comment_str = f"  # {comment}" if comment else ""
        return f"{indent}{snake_name}:{comment_str}{formatted}"
    elif isinstance(value, (dict, list)) and value:
        # Multi-line values in YAML format
        formatted = _format_yaml_value(value, base_indent + 2)
        comment_str = f"  # {comment}" if comment else ""
        return f"{indent}{snake_name}:{comment_str}{formatted}"
    else:
        formatted = _format_yaml_value(value)
        comment_str = f"  # {comment}" if comment else ""
        return f"{indent}{snake_name}: {formatted}{comment_str}"


def prepare_fields_block(
    fields: list[dict[str, Any]],
    example_values: dict[str, Any] | None,
    base_indent: int = 8,
) -> str:
    """Prepare the YAML block for all fields with values and comments."""
    lines: list[str] = []

    for field in fields:
        snake_name = field["snake_name"]
        value = generate_example_value(field, example_values)
        comment = build_field_comment(field)
        json_format = field.get("json_format", False)
        line = _render_field_line(snake_name, value, comment, base_indent, json_format=json_format)
        lines.append(line)

    return "\n".join(lines)


def render_api_reference(
    env: Environment,
    resources: list[DiscoveredResource],
    output_dir: Path,
    spec: dict[str, Any],
    config: dict[str, Any],
) -> list[Path]:
    """Render API reference files for all resources."""
    # Clean stale output
    if output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files: list[Path] = []
    module_overrides = config.get("module_overrides", {})

    for resource in resources:
        # Get the create DTO schema
        create_endpoint = resource.endpoints.get("create")
        if not create_endpoint or not create_endpoint.dto:
            continue

        create_schema = get_schema_by_name(spec, create_endpoint.dto)
        if not create_schema:
            continue

        # Extract fields (excluding read-only)
        fields = extract_fields_from_schema(create_schema, resource.read_only_fields)

        # Apply field renames
        for field in fields:
            original_name = field["name"]
            if original_name in resource.field_renames:
                renamed = resource.field_renames[original_name]
                field["snake_name"] = to_snake_case(renamed)

        # Get example values from config
        override = module_overrides.get(resource.module_name, {})
        example_values = override.get("example_values")

        # Handle nested fields with format info from spec
        _enrich_fields_from_spec(fields, create_schema)

        # Build the fields block
        fields_block = prepare_fields_block(fields, example_values)

        # Render template
        template = env.get_template("api_reference/all_options.yml.j2")
        content = template.render(
            resource_name=resource.resource_name,
            module_name=resource.module_name,
            fields_block=fields_block,
        )

        output_path = output_dir / f"{resource.module_name}_all_options.yml"
        output_path.write_text(content)
        generated_files.append(output_path)

    return generated_files


def _enrich_fields_from_spec(fields: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    """Enrich field metadata with additional info from the raw schema."""
    properties = schema.get("properties", {})
    for field in fields:
        prop = properties.get(field["name"], {})
        # Freeform objects (type: object with empty or no properties) use JSON format
        if field["type"] == "dict" and prop.get("type") == "object":
            defined_props = prop.get("properties", {})
            if not defined_props:
                field["json_format"] = True
        # For arrays, check items format
        if field["type"] == "list" and "items" in prop:
            items = prop["items"]
            if items.get("format"):
                field["format"] = items["format"]
            if items.get("pattern"):
                field["pattern"] = items["pattern"]
            if items.get("maxLength"):
                field["item_max_length"] = items["maxLength"]
        # For arrays at field level
        if "maxItems" in prop:
            field["max_items"] = prop["maxItems"]


def list_api_reference_files(resources: list[DiscoveredResource]) -> list[str]:
    """List API reference files that would be generated (for dry-run)."""
    files = []
    for resource in resources:
        if resource.endpoints.get("create"):
            files.append(f"{resource.module_name}_all_options.yml")
    return sorted(files)
