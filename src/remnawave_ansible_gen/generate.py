#!/usr/bin/env python3
"""
Remnawave Ansible Module Generator.

Generates Ansible modules from OpenAPI specification.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml
from jinja2 import Environment, FileSystemLoader
from prance import ResolvingParser


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
        return cast(dict[str, Any], yaml.safe_load(f))


def load_openapi_spec(spec_path: Path) -> dict[str, Any]:
    """Load and resolve the OpenAPI specification."""
    # Use flex backend which is more lenient with validation
    try:
        parser = ResolvingParser(str(spec_path), backend="flex")
        return cast(dict[str, Any], parser.specification)
    except Exception:
        # Fall back to plain YAML loading if flex fails
        with open(spec_path) as f:
            return cast(dict[str, Any], yaml.safe_load(f))


def get_schema_by_name(spec: dict[str, Any], schema_name: str) -> dict[str, Any] | None:
    """Get a schema by name from the OpenAPI spec."""
    schemas: dict[str, Any] = spec.get("components", {}).get("schemas", {})
    return cast(dict[str, Any] | None, schemas.get(schema_name))


# =============================================================================
# Auto-Discovery Functions
# =============================================================================


def classify_operation(method: str, path: str, operation: dict[str, Any]) -> str | None:
    """
    Classify an operation as create/update/get_all/get_one/delete.

    Returns None if the operation doesn't match a standard CRUD pattern.
    """
    method = method.lower()
    operation_id = operation.get("operationId", "").lower()

    # Check for path parameters and count path segments
    has_path_param = "{" in path
    path_segments = [s for s in path.split("/") if s]

    # Detect if path has extra segments beyond base + optional id param
    # e.g., /api/nodes = base, /api/nodes/{uuid} = base + id
    # but /api/nodes/{uuid}/restart = extra action, not CRUD
    base_segment_count = 2  # e.g., ['api', 'nodes']

    if has_path_param:
        # Count non-param segments after base
        extra_segments = [s for s in path_segments[base_segment_count:] if not s.startswith("{")]
        if extra_segments:
            # Has extra path segments after id param, skip (e.g., /computed-config)
            return None
    else:
        # For non-param paths, check if there are extra segments
        if len(path_segments) > base_segment_count:
            # Extra segments like /api/config-profiles/inbounds - skip
            return None

    # Extract method name from operationId (e.g., "Controller_createNode" -> "createnode")
    # Also handle simple operationIds like "createNode"
    method_name = operation_id.split("_")[-1] if "_" in operation_id else operation_id

    if method == "post" and not has_path_param:
        # POST to base path = create
        if "create" in method_name:
            return "create"
    elif method == "get":
        if has_path_param:
            # GET with path param = get_one
            # Match patterns: getOne*, get*ByUuid, get*By{Id}
            if "getone" in method_name or "byuuid" in method_name or "byname" in method_name:
                return "get_one"
        else:
            # GET to base path without param = get_all
            # Match patterns: getAll*, get{Resources} (plural)
            # Avoid sub-resource patterns
            if "getall" in method_name:
                return "get_all"
            # Also match "get{Resource}s" pattern (e.g., getConfigProfiles, getNodes)
            if method_name.startswith("get") and not any(
                x in method_name for x in ["tags", "inbound", "stats", "settings"]
            ):
                return "get_all"
    elif method == "patch" and not has_path_param:
        # PATCH to base path = update
        if "update" in method_name:
            return "update"
    elif method == "delete" and has_path_param:
        # DELETE with path param = delete
        if "delete" in method_name:
            return "delete"

    return None


def extract_dto_from_ref(ref: str | None) -> str | None:
    """Extract DTO name from $ref string."""
    if not ref:
        return None
    # $ref: "#/components/schemas/CreateNodeRequestDto"
    if ref.startswith("#/components/schemas/"):
        return ref.split("/")[-1]
    return None


def detect_id_param(path: str) -> str | None:
    """Detect the id parameter from a path with placeholder."""
    # Extract {uuid} or {name} from path like /api/nodes/{uuid}
    match = re.search(r"\{(\w+)\}", path)
    if match:
        return match.group(1)
    return None


def detect_lookup_field(create_schema: dict[str, Any]) -> str | None:
    """
    Detect the lookup field from Create DTO.

    The lookup field is typically the first required string field
    with constraints (minLength, maxLength, pattern).
    """
    properties: dict[str, Any] = create_schema.get("properties", {})
    required_fields = set(create_schema.get("required", []))

    # Prioritize 'name' if it exists and is required
    if "name" in properties and "name" in required_fields:
        prop = properties["name"]
        if prop.get("type") == "string":
            return "name"

    # Otherwise, find the first constrained string field
    for name, prop in properties.items():
        if name in required_fields and prop.get("type") == "string":
            # Check for constraints
            if any(k in prop for k in ["minLength", "maxLength", "pattern"]):
                return name

    return None


def compute_read_only_fields(
    create_schema: dict[str, Any],
    response_schema: dict[str, Any],
) -> list[str]:
    """
    Compute fields that are in the response but not in the create DTO.

    These are read-only fields that should be excluded from idempotency checks.
    """
    create_fields = set(create_schema.get("properties", {}).keys())

    # Response is typically wrapped in a 'response' property
    response_props = response_schema.get("properties", {})
    if "response" in response_props:
        inner = response_props["response"]
        response_fields = set(inner.get("properties", {}).keys())
    else:
        response_fields = set(response_props.keys())

    # Read-only fields are in response but not in create
    read_only = response_fields - create_fields
    return sorted(read_only)


def derive_resource_name_from_tag(tag: str) -> str:
    """
    Derive resource name from controller tag.

    "Nodes Controller" -> "Node"
    "Config Profiles Controller" -> "Config Profile"
    """
    # Remove " Controller" suffix
    name = tag.replace(" Controller", "").strip()
    # Handle plurals: "Nodes" -> "Node", "Config Profiles" -> "Config Profile"
    if name.endswith("s") and not name.endswith("ss"):
        name = name[:-1]
    return name


def derive_module_name_from_resource(resource_name: str) -> str:
    """
    Derive module name from resource name.

    "Node" -> "node"
    "Config Profile" -> "config_profile"
    """
    return to_snake_case(resource_name.replace(" ", ""))


def group_operations_by_controller(
    spec: dict[str, Any],
) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
    """
    Group operations by controller tag.

    Returns a dict mapping tag -> list of (path, method, operation).
    """
    controllers: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}

    for path, path_item in spec.get("paths", {}).items():
        for method in ["get", "post", "put", "patch", "delete"]:
            if method not in path_item:
                continue
            operation = path_item[method]
            tags = operation.get("tags", [])
            for tag in tags:
                if tag not in controllers:
                    controllers[tag] = []
                controllers[tag].append((path, method.upper(), operation))

    return controllers


def discover_resources(
    spec: dict[str, Any],
    config: dict[str, Any],
) -> list[DiscoveredResource]:
    """
    Main entry point for auto-discovery.

    Discovers resources from OpenAPI spec based on controller patterns.
    """
    discovery_config = config.get("discovery", {})
    include_controllers = set(discovery_config.get("include_controllers", []))
    exclude_controllers = set(discovery_config.get("exclude_controllers", []))
    module_overrides = config.get("module_overrides", {})
    global_read_only = config.get("read_only_fields", [])

    controllers = group_operations_by_controller(spec)
    resources: list[DiscoveredResource] = []

    for tag, operations in controllers.items():
        # Apply include/exclude filters
        if include_controllers and tag not in include_controllers:
            continue
        if tag in exclude_controllers:
            continue

        # Classify operations
        endpoints: dict[str, DiscoveredEndpoint] = {}
        base_path: str | None = None
        id_param: str | None = None

        for path, method, operation in operations:
            op_type = classify_operation(method, path, operation)
            if not op_type:
                continue

            # Extract DTO references
            dto = None
            response_dto = None

            # Request body DTO
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {}).get("application/json", {})
            schema = content.get("schema", {})
            dto = extract_dto_from_ref(schema.get("$ref"))

            # Response DTO
            responses = operation.get("responses", {})
            for status in ["200", "201"]:
                if status in responses:
                    resp_content = responses[status].get("content", {})
                    resp_schema = resp_content.get("application/json", {}).get("schema", {})
                    response_dto = extract_dto_from_ref(resp_schema.get("$ref"))
                    break

            endpoints[op_type] = DiscoveredEndpoint(
                path=path,
                method=method,
                dto=dto,
                response_dto=response_dto,
            )

            # Detect base path and id_param
            if op_type == "create":
                base_path = path
            elif op_type in ("get_one", "delete") and "{" in path:
                id_param = detect_id_param(path)

        # Skip if we don't have at least create and get_all
        if "create" not in endpoints or "get_all" not in endpoints:
            continue

        # Derive resource and module names
        resource_name = derive_resource_name_from_tag(tag)
        module_name = derive_module_name_from_resource(resource_name)

        # Get create DTO schema for field detection
        create_dto_name = endpoints["create"].dto
        if not create_dto_name:
            continue

        create_schema = get_schema_by_name(spec, create_dto_name)
        if not create_schema:
            continue

        # Detect lookup field
        lookup_field = detect_lookup_field(create_schema)
        if not lookup_field:
            lookup_field = "name"  # Default fallback

        # Compute read-only fields
        response_dto_name = endpoints["create"].response_dto
        resource_read_only: list[str] = []
        if response_dto_name:
            response_schema = get_schema_by_name(spec, response_dto_name)
            if response_schema:
                resource_read_only = compute_read_only_fields(create_schema, response_schema)

        # Build resource
        resource = DiscoveredResource(
            controller_tag=tag,
            resource_name=resource_name,
            module_name=module_name,
            base_path=base_path or "",
            id_param=id_param or "uuid",
            lookup_field=lookup_field,
            endpoints=endpoints,
            read_only_fields=resource_read_only,
        )

        # Apply overrides
        resource = apply_overrides(resource, module_overrides, global_read_only)

        resources.append(resource)

    return resources


def apply_overrides(
    resource: DiscoveredResource,
    overrides: dict[str, Any],
    global_read_only: list[str],
) -> DiscoveredResource:
    """Apply config overrides to a discovered resource."""
    module_override = overrides.get(resource.module_name, {})

    # Merge read-only fields: global + discovered + override
    all_read_only = set(global_read_only)
    all_read_only.update(resource.read_only_fields)
    if "read_only_fields" in module_override:
        all_read_only.update(module_override["read_only_fields"])

    resource.read_only_fields = sorted(all_read_only)

    # Apply other overrides
    if "lookup_field" in module_override:
        resource.lookup_field = module_override["lookup_field"]
    if "id_param" in module_override:
        resource.id_param = module_override["id_param"]
    if "description" in module_override:
        resource.description = module_override["description"]
    if module_override.get("resolve_uuid_by_name"):
        resource.resolve_uuid_by_name = True

    return resource


def discovered_to_module_config(resource: DiscoveredResource) -> dict[str, Any]:
    """Convert a DiscoveredResource to the legacy module config format."""
    endpoints = {}
    for op_type, endpoint in resource.endpoints.items():
        ep_config: dict[str, Any] = {
            "path": endpoint.path,
            "method": endpoint.method,
        }
        if endpoint.dto:
            ep_config["dto"] = endpoint.dto
        if endpoint.response_dto:
            ep_config["response_dto"] = endpoint.response_dto
        endpoints[op_type] = ep_config

    # Use description override if available, otherwise generate
    if resource.description:
        description = resource.description
    else:
        # Generate description: "Config Profile" -> "config profiles"
        resource_lower = resource.resource_name.lower()
        words = resource_lower.split()
        if len(words) > 1:
            # Pluralize last word
            words[-1] = words[-1] + "s"
            resource_plural = " ".join(words)
        else:
            resource_plural = resource_lower + "s"
        description = f"Manage Remnawave panel {resource_plural}"

    return {
        "name": resource.module_name,
        "resource_name": resource.resource_name,
        "description": description,
        "controller_tag": resource.controller_tag,
        "id_param": resource.id_param,
        "lookup_field": resource.lookup_field,
        "endpoints": endpoints,
        "resolve_uuid_by_name": resource.resolve_uuid_by_name,
    }


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
        resolve_uuid_by_name=module_config.get("resolve_uuid_by_name", False),
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


# =============================================================================
# Example Generation Functions
# =============================================================================


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
        files.extend([
            f"basic/{module_name}_create.yml",
            f"basic/{module_name}_update.yml",
            f"basic/{module_name}_delete.yml",
        ])

    return sorted(files)


def main() -> int:
    """Main entry point for the generator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate Ansible modules from OpenAPI specification.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered resources without generating files",
    )
    args = parser.parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent.parent

    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)

    # Load OpenAPI spec
    spec_path = project_root / config["general"]["spec_file"]
    print(f"Loading OpenAPI spec from {spec_path}...")
    spec = load_openapi_spec(spec_path)

    # Discover resources from OpenAPI spec
    resources = discover_resources(spec, config)

    if args.dry_run:
        print("\nDiscovered resources:")
        for resource in resources:
            print(f"\n  {resource.module_name}:")
            print(f"    controller_tag: {resource.controller_tag}")
            print(f"    resource_name: {resource.resource_name}")
            print(f"    base_path: {resource.base_path}")
            print(f"    id_param: {resource.id_param}")
            print(f"    lookup_field: {resource.lookup_field}")
            print(f"    endpoints: {list(resource.endpoints.keys())}")
            print(f"    read_only_fields: {resource.read_only_fields[:5]}...")

        # List example files that would be generated
        examples_config = config.get("examples", {})
        if examples_config.get("enabled", True):
            examples_dir = config.get("examples", {}).get("output_dir", "collection/examples")
            example_files = list_example_files(resources)
            print(f"\nExample files to generate in {examples_dir}/:")
            for example_file in example_files:
                print(f"  - {example_file}")

        return 0

    module_configs = [discovered_to_module_config(r) for r in resources]
    read_only_by_module = {r.module_name: r.read_only_fields for r in resources}
    read_only_fields = config.get("read_only_fields", [])

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

    # Generate shared module utilities
    print("Generating module_utils/remnawave.py...")
    utils_code = render_module_utils(env, config)
    utils_path = module_utils_dir / "remnawave.py"
    with open(utils_path, "w") as f:
        f.write(utils_code)
    format_code(utils_path)

    # Generate each module
    for module_config in module_configs:
        module_name = module_config["name"]
        print(f"Generating {module_name}.py...")

        # In discover mode, use per-resource read_only_fields
        module_read_only = read_only_by_module.get(module_name, read_only_fields)

        try:
            module_code = render_module(env, module_config, spec, module_read_only)
            module_path = modules_dir / f"{module_name}.py"

            with open(module_path, "w") as f:
                f.write(module_code)

            format_code(module_path)
            print(f"  -> Generated {module_path}")

        except Exception as e:
            print(f"  -> Error generating {module_name}: {e}")
            return 1

    # Generate example playbooks
    examples_config = config.get("examples", {})
    if examples_config.get("enabled", True):
        examples_dir = project_root / examples_config.get("output_dir", "collection/examples")
        print(f"\nGenerating example playbooks in {examples_dir}...")
        try:
            generated_examples = render_examples(env, resources, examples_dir, spec, config)
            for example_path in generated_examples:
                print(f"  -> Generated {example_path}")
        except Exception as e:
            print(f"  -> Error generating examples: {e}")
            return 1

    print("\nGeneration complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
