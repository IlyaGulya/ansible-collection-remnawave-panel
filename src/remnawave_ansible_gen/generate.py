#!/usr/bin/env python3
"""
Remnawave Ansible Module Generator.

Generates Ansible modules from OpenAPI specification.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader
from prance import ResolvingParser


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


def load_config(config_path: Path) -> dict[str, Any]:
    """Load the generator configuration file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Load and resolve the OpenAPI specification."""
    # Use flex backend which is more lenient with validation
    try:
        parser = ResolvingParser(str(spec_path), backend="flex")
        return parser.specification
    except Exception:
        # Fall back to plain YAML loading if flex fails
        with open(spec_path) as f:
            return yaml.safe_load(f)


def get_schema_by_name(spec: dict[str, Any], schema_name: str) -> dict[str, Any] | None:
    """Get a schema by name from the OpenAPI spec."""
    schemas = spec.get("components", {}).get("schemas", {})
    return schemas.get(schema_name)


def render_module(
    env: Environment,
    module_config: dict[str, Any],
    spec: dict[str, Any],
    read_only_fields: list[str],
) -> str:
    """Render an Ansible module from the template."""
    template = env.get_template("module.py.j2")

    # Extract fields from create DTO
    create_dto_name = module_config["endpoints"]["create"]["dto"]
    create_schema = get_schema_by_name(spec, create_dto_name)

    if not create_schema:
        raise ValueError(f"Schema {create_dto_name} not found in OpenAPI spec")

    fields = extract_fields_from_schema(create_schema, read_only_fields)

    # Get update DTO if different
    update_dto_name = module_config["endpoints"]["update"].get("dto")
    update_fields = []
    if update_dto_name and update_dto_name != create_dto_name:
        update_schema = get_schema_by_name(spec, update_dto_name)
        if update_schema:
            update_fields = extract_fields_from_schema(update_schema, read_only_fields)

    return template.render(
        module_name=module_config["name"],
        resource_name=module_config["resource_name"],
        description=module_config.get("description", f"Manage {module_config['resource_name']} resources"),
        id_param=module_config["id_param"],
        lookup_field=module_config["lookup_field"],
        endpoints=module_config["endpoints"],
        fields=fields,
        update_fields=update_fields if update_fields else fields,
        read_only_fields=read_only_fields,
        to_snake_case=to_snake_case,
        to_camel_case=to_camel_case,
    )


def render_module_utils(env: Environment, config: dict[str, Any]) -> str:
    """Render the shared module utilities."""
    template = env.get_template("module_utils.py.j2")
    return template.render(
        read_only_fields=config.get("read_only_fields", []),
    )


def format_code(file_path: Path) -> None:
    """Format Python code using ruff."""
    try:
        subprocess.run(
            ["ruff", "format", str(file_path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["ruff", "check", "--fix", str(file_path)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: ruff formatting failed for {file_path}: {e.stderr.decode()}")
    except FileNotFoundError:
        print("Warning: ruff not found, skipping formatting")


def main() -> int:
    """Main entry point for the generator."""
    # Determine project root
    project_root = Path(__file__).parent.parent.parent

    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)

    # Load OpenAPI spec
    spec_path = project_root / config["general"]["spec_file"]
    print(f"Loading OpenAPI spec from {spec_path}...")
    spec = load_openapi_spec(spec_path)

    # Set up Jinja2 environment
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Output directories
    modules_dir = project_root / config["general"]["output_dir"]
    module_utils_dir = project_root / config["general"]["module_utils_dir"]

    # Ensure directories exist
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_utils_dir.mkdir(parents=True, exist_ok=True)

    read_only_fields = config.get("read_only_fields", [])

    # Generate shared module utilities
    print("Generating module_utils/remnawave.py...")
    utils_code = render_module_utils(env, config)
    utils_path = module_utils_dir / "remnawave.py"
    with open(utils_path, "w") as f:
        f.write(utils_code)
    format_code(utils_path)

    # Generate each module
    for module_config in config["modules"]:
        module_name = module_config["name"]
        print(f"Generating {module_name}.py...")

        try:
            module_code = render_module(env, module_config, spec, read_only_fields)
            module_path = modules_dir / f"{module_name}.py"

            with open(module_path, "w") as f:
                f.write(module_code)

            format_code(module_path)
            print(f"  -> Generated {module_path}")

        except Exception as e:
            print(f"  -> Error generating {module_name}: {e}")
            return 1

    print("\nGeneration complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
