"""Example playbook generation for the Remnawave Ansible Module Generator."""

from pathlib import Path
from typing import Any

from jinja2 import Environment

from .models import DiscoveredResource
from .schema import extract_fields_from_schema, get_schema_by_name


def load_snippet(snippet_name: str) -> str:
    """Load a snippet file from the templates/examples/snippets directory."""
    snippets_dir = Path(__file__).parent / "templates" / "examples" / "snippets"
    snippet_path = snippets_dir / snippet_name
    if snippet_path.exists():
        return snippet_path.read_text().rstrip()
    return ""


def get_example_fields_for_module(module_name: str, fields: list[dict[str, Any]]) -> dict[str, str]:
    """
    Get example field values for a specific module.

    Returns a dict with keys: create_fields, update_fields, lookup_field_var
    """
    # Try to load from snippet files
    create_snippet = load_snippet(f"{module_name}_create.yml")
    update_snippet = load_snippet(f"{module_name}_update.yml")

    if create_snippet and update_snippet:
        # Determine lookup_field_var based on module
        lookup_vars = {
            "config_profile": "config_profile_name",
            "node": "node_name",
        }
        return {
            "create_fields": create_snippet,
            "update_fields": update_snippet,
            "lookup_field_var": lookup_vars.get(module_name, "name"),
        }
    else:
        # Generic fallback - use required fields
        create_lines = []
        for field in fields:
            if field.get("required"):
                snake_name = field["snake_name"]
                create_lines.append(f'{snake_name}: "example_value"')
        return {
            "create_fields": "\n".join(create_lines) if create_lines else "# No required fields",
            "update_fields": "\n".join(create_lines) if create_lines else "# No required fields",
            "lookup_field_var": fields[0]["snake_name"] if fields else "name",
        }


def render_basic_examples(
    env: Environment,
    resources: list[DiscoveredResource],
    output_dir: Path,
    spec: dict[str, Any],
    config: dict[str, Any],
) -> list[Path]:
    """Render basic CRUD example playbooks for each module."""
    generated_files: list[Path] = []
    basic_dir = output_dir / "basic"
    basic_dir.mkdir(parents=True, exist_ok=True)

    create_template = env.get_template("examples/basic_create.yml.j2")
    update_template = env.get_template("examples/basic_update.yml.j2")
    delete_template = env.get_template("examples/basic_delete.yml.j2")

    global_read_only = config.get("read_only_fields", [])

    for resource in resources:
        module_name = resource.module_name
        resource_name = resource.resource_name
        lookup_field = resource.lookup_field

        # Get fields for this resource
        create_dto_name = resource.endpoints["create"].dto
        create_schema = get_schema_by_name(spec, create_dto_name) if create_dto_name else None
        fields = []
        if create_schema:
            fields = extract_fields_from_schema(create_schema, global_read_only)

        # Get example field values
        example_fields = get_example_fields_for_module(module_name, fields)

        # Render create example
        create_content = create_template.render(
            module_name=module_name,
            resource_name=resource_name,
            lookup_field=lookup_field,
            example_create_fields=example_fields["create_fields"],
        )
        create_path = basic_dir / f"{module_name}_create.yml"
        with open(create_path, "w") as f:
            f.write(create_content)
        generated_files.append(create_path)

        # Render update example
        update_content = update_template.render(
            module_name=module_name,
            resource_name=resource_name,
            lookup_field=lookup_field,
            example_update_fields=example_fields["update_fields"],
        )
        update_path = basic_dir / f"{module_name}_update.yml"
        with open(update_path, "w") as f:
            f.write(update_content)
        generated_files.append(update_path)

        # Render delete example
        delete_content = delete_template.render(
            module_name=module_name,
            resource_name=resource_name,
            lookup_field=lookup_field,
            lookup_field_var=example_fields["lookup_field_var"],
        )
        delete_path = basic_dir / f"{module_name}_delete.yml"
        with open(delete_path, "w") as f:
            f.write(delete_content)
        generated_files.append(delete_path)

    return generated_files


def render_workflow_examples(env: Environment, output_dir: Path) -> list[Path]:
    """Render workflow example playbooks."""
    generated_files: list[Path] = []
    workflows_dir = output_dir / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Basic setup workflow
    setup_template = env.get_template("examples/workflow_setup.yml.j2")
    setup_content = setup_template.render()
    setup_path = workflows_dir / "setup_infrastructure.yml"
    with open(setup_path, "w") as f:
        f.write(setup_content)
    generated_files.append(setup_path)

    # Basic teardown workflow
    teardown_template = env.get_template("examples/workflow_teardown.yml.j2")
    teardown_content = teardown_template.render()
    teardown_path = workflows_dir / "teardown_infrastructure.yml"
    with open(teardown_path, "w") as f:
        f.write(teardown_content)
    generated_files.append(teardown_path)

    # Production setup workflow (multi-region, multi-profile)
    production_setup_template = env.get_template("examples/workflow_production_setup.yml.j2")
    production_setup_content = production_setup_template.render()
    production_setup_path = workflows_dir / "production_setup.yml"
    with open(production_setup_path, "w") as f:
        f.write(production_setup_content)
    generated_files.append(production_setup_path)

    # Production teardown workflow
    production_teardown_template = env.get_template("examples/workflow_production_teardown.yml.j2")
    production_teardown_content = production_teardown_template.render()
    production_teardown_path = workflows_dir / "production_teardown.yml"
    with open(production_teardown_path, "w") as f:
        f.write(production_teardown_content)
    generated_files.append(production_teardown_path)

    return generated_files


def render_advanced_examples(env: Environment, output_dir: Path) -> list[Path]:
    """Render advanced example playbooks."""
    generated_files: list[Path] = []
    advanced_dir = output_dir / "advanced"
    advanced_dir.mkdir(parents=True, exist_ok=True)

    # Check mode example
    check_mode_template = env.get_template("examples/advanced_check_mode.yml.j2")
    check_mode_content = check_mode_template.render()
    check_mode_path = advanced_dir / "check_mode.yml"
    with open(check_mode_path, "w") as f:
        f.write(check_mode_content)
    generated_files.append(check_mode_path)

    # Multi-region example
    multi_region_template = env.get_template("examples/advanced_multi_region.yml.j2")
    multi_region_content = multi_region_template.render()
    multi_region_path = advanced_dir / "multi_region_nodes.yml"
    with open(multi_region_path, "w") as f:
        f.write(multi_region_content)
    generated_files.append(multi_region_path)

    return generated_files


def render_vars_file(env: Environment, output_dir: Path) -> list[Path]:
    """Render example variables files."""
    generated_files: list[Path] = []
    vars_dir = output_dir / "vars"
    vars_dir.mkdir(parents=True, exist_ok=True)

    # Basic example vars
    vars_template = env.get_template("examples/vars_example.yml.j2")
    vars_content = vars_template.render()
    vars_path = vars_dir / "example_vars.yml"
    with open(vars_path, "w") as f:
        f.write(vars_content)
    generated_files.append(vars_path)

    # Production vars (multi-region, multi-profile)
    production_vars_template = env.get_template("examples/vars_production.yml.j2")
    production_vars_content = production_vars_template.render()
    production_vars_path = vars_dir / "production_vars.yml"
    with open(production_vars_path, "w") as f:
        f.write(production_vars_content)
    generated_files.append(production_vars_path)

    return generated_files


def render_example_readme(env: Environment, output_dir: Path) -> Path:
    """Render the examples README file."""
    readme_template = env.get_template("examples/README.md.j2")
    readme_content = readme_template.render()
    readme_path = output_dir / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    return readme_path


def render_examples(
    env: Environment,
    resources: list[DiscoveredResource],
    output_dir: Path,
    spec: dict[str, Any],
    config: dict[str, Any],
) -> list[Path]:
    """
    Main entry point for example generation.

    Generates all example playbooks and returns a list of generated file paths.
    """
    generated_files: list[Path] = []

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate vars file
    generated_files.extend(render_vars_file(env, output_dir))

    # Generate basic CRUD examples
    generated_files.extend(render_basic_examples(env, resources, output_dir, spec, config))

    # Generate workflow examples
    generated_files.extend(render_workflow_examples(env, output_dir))

    # Generate advanced examples
    generated_files.extend(render_advanced_examples(env, output_dir))

    # Generate README
    readme_path = render_example_readme(env, output_dir)
    generated_files.append(readme_path)

    return generated_files


def list_example_files(resources: list[DiscoveredResource]) -> list[str]:
    """List all example files that would be generated (for dry-run)."""
    files = [
        "vars/example_vars.yml",
        "vars/production_vars.yml",
        "README.md",
        "workflows/setup_infrastructure.yml",
        "workflows/teardown_infrastructure.yml",
        "workflows/production_setup.yml",
        "workflows/production_teardown.yml",
        "advanced/check_mode.yml",
        "advanced/multi_region_nodes.yml",
    ]

    for resource in resources:
        module_name = resource.module_name
        files.extend(
            [
                f"basic/{module_name}_create.yml",
                f"basic/{module_name}_update.yml",
                f"basic/{module_name}_delete.yml",
            ]
        )

    return sorted(files)
