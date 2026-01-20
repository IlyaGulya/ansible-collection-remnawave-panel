"""OpenAPI schema extraction for the Remnawave Ansible Module Generator."""

from typing import Any, cast

from .utils import map_openapi_type, to_snake_case


def get_schema_by_name(spec: dict[str, Any], schema_name: str) -> dict[str, Any] | None:
    """Get a schema by name from the OpenAPI spec."""
    schemas: dict[str, Any] = spec.get("components", {}).get("schemas", {})
    return cast(dict[str, Any] | None, schemas.get(schema_name))


def extract_fields_from_schema(
    schema: dict[str, Any],
    read_only_fields: list[str],
) -> list[dict[str, Any]]:
    """Extract fields from an OpenAPI schema definition."""
    fields = []
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    for name, prop in properties.items():
        if name in read_only_fields:
            continue

        field = {
            "name": name,
            "snake_name": to_snake_case(name),
            "type": map_openapi_type(prop.get("type", "string"), prop.get("format")),
            "required": name in required_fields,
            "description": prop.get("description", f"The {name} field"),
            "default": prop.get("default"),
        }

        # Handle nested objects
        if prop.get("type") == "object" and "properties" in prop:
            field["nested_fields"] = extract_fields_from_schema(prop, read_only_fields)

        # Handle arrays with items
        if prop.get("type") == "array" and "items" in prop:
            items = prop["items"]
            field["elements"] = map_openapi_type(items.get("type", "string"))

        # Handle nullable
        if prop.get("nullable"):
            field["required"] = False

        # Handle format for documentation
        if prop.get("format"):
            field["format"] = prop["format"]

        # Handle min/max constraints
        if "minimum" in prop:
            field["min"] = prop["minimum"]
        if "maximum" in prop:
            field["max"] = prop["maximum"]
        if "minLength" in prop:
            field["min_length"] = prop["minLength"]
        if "maxLength" in prop:
            field["max_length"] = prop["maxLength"]

        fields.append(field)

    return fields
