"""Auto-discovery engine for the Remnawave Ansible Module Generator."""

import re
from typing import Any

from .models import DiscoveredEndpoint, DiscoveredResource
from .schema import get_schema_by_name
from .utils import to_snake_case


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
    if "field_renames" in module_override:
        resource.field_renames = module_override["field_renames"]

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
        "field_renames": resource.field_renames,
    }
