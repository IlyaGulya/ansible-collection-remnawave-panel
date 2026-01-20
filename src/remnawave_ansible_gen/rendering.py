"""Template rendering for the Remnawave Ansible Module Generator."""

import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .schema import extract_fields_from_schema, get_schema_by_name
from .utils import to_camel_case, to_snake_case


def create_jinja_environment(templates_dir: Path) -> Environment:
    """Create and configure a Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(templates_dir),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_module(
    env: Environment,
    module_config: dict[str, Any],
    spec: dict[str, Any],
    read_only_fields: list[str],
    collection_version: str,
    api_version: str,
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

    return str(template.render(
        module_name=module_config["name"],
        resource_name=module_config["resource_name"],
        description=module_config.get("description", f"Manage {module_config['resource_name']} resources"),
        id_param=module_config["id_param"],
        lookup_field=module_config["lookup_field"],
        endpoints=module_config["endpoints"],
        fields=fields,
        update_fields=update_fields if update_fields else fields,
        read_only_fields=read_only_fields,
        resolve_uuid_by_name=module_config.get("resolve_uuid_by_name", False),
        collection_version=collection_version,
        api_version=api_version,
        to_snake_case=to_snake_case,
        to_camel_case=to_camel_case,
    ))


def render_module_utils(env: Environment, config: dict[str, Any]) -> str:
    """Render the shared module utilities."""
    template = env.get_template("module_utils.py.j2")
    return str(template.render(
        read_only_fields=config.get("read_only_fields", []),
    ))


def format_code(file_path: Path, project_root: Path | None = None) -> None:
    """Format Python code using ruff via uvx.

    Args:
        file_path: Path to the file to format.
        project_root: Project root directory. If provided, ruff runs from there
                      so pyproject.toml config (like per-file-ignores) is picked up.
    """
    # Determine working directory and file path for ruff
    if project_root:
        cwd = str(project_root)
        # Use relative path so per-file-ignores patterns match
        try:
            target = str(file_path.relative_to(project_root))
        except ValueError:
            target = str(file_path)
    else:
        cwd = None
        target = str(file_path)

    try:
        subprocess.run(
            ["uvx", "ruff", "format", target],
            check=True,
            capture_output=True,
            cwd=cwd,
        )
        subprocess.run(
            ["uvx", "ruff", "check", "--fix", target],
            check=True,
            capture_output=True,
            cwd=cwd,
        )
    except subprocess.CalledProcessError as e:
        # Show stderr if present, otherwise stdout (ruff outputs errors to stdout)
        error_output = e.stderr.decode() if e.stderr else e.stdout.decode() if e.stdout else ""
        if error_output:
            print(f"Warning: ruff formatting failed for {file_path}: {error_output}")
    except FileNotFoundError:
        print("Warning: uvx not found, skipping formatting")
