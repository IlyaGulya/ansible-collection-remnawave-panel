#!/usr/bin/env python3
"""CLI entry point for the Remnawave Ansible Module Generator."""

import argparse
import shutil
import sys
from pathlib import Path

import yaml

from .api_reference import list_api_reference_files, render_api_reference
from .config import load_config, load_openapi_spec
from .discovery import discover_resources, discovered_to_module_config
from .rendering import create_jinja_environment, format_code, render_module, render_module_utils
from .utils import extract_api_version, read_pyproject_version


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate Ansible modules from OpenAPI specification.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discovered resources without generating files",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the generator."""
    args = parse_args()

    # Determine project root
    project_root = Path(__file__).parent.parent.parent

    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)

    # Load OpenAPI spec
    spec_path = project_root / config["general"]["spec_file"]
    print(f"Loading OpenAPI spec from {spec_path}...")
    spec = load_openapi_spec(spec_path)

    # Extract versions
    collection_version = read_pyproject_version(project_root)
    api_version = extract_api_version(spec)
    print(f"Collection version: {collection_version}")
    print(f"Remnawave API version: {api_version}")

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

        # List API reference files that would be generated
        api_ref_dir = config.get("api_reference", {}).get(
            "output_dir", "ansible_collections/ilyagulya/remnawave/docs/api_reference"
        )
        api_ref_files = list_api_reference_files(resources)
        print(f"\nAPI reference files to generate in {api_ref_dir}/:")
        for ref_file in api_ref_files:
            print(f"  - {ref_file}")

        return 0

    module_configs = [discovered_to_module_config(r) for r in resources]
    read_only_by_module = {r.module_name: r.read_only_fields for r in resources}
    read_only_fields = config.get("read_only_fields", [])

    # Set up Jinja2 environment
    templates_dir = Path(__file__).parent / "templates"
    env = create_jinja_environment(templates_dir)

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
    format_code(utils_path, project_root)

    # Generate each module
    for module_config in module_configs:
        module_name = module_config["name"]
        print(f"Generating {module_name}.py...")

        # In discover mode, use per-resource read_only_fields
        module_read_only = read_only_by_module.get(module_name, read_only_fields)

        try:
            module_code = render_module(env, module_config, spec, module_read_only, collection_version, api_version)
            module_path = modules_dir / f"{module_name}.py"

            with open(module_path, "w") as f:
                f.write(module_code)

            format_code(module_path, project_root)
            print(f"  -> Generated {module_path}")

        except Exception as e:
            print(f"  -> Error generating {module_name}: {e}")
            return 1

    # Generate API reference
    api_ref_config = config.get("api_reference", {})
    api_ref_output = project_root / api_ref_config.get(
        "output_dir", "ansible_collections/ilyagulya/remnawave/docs/api_reference"
    )
    print(f"\nGenerating API reference in {api_ref_output}...")
    try:
        generated_refs = render_api_reference(env, resources, api_ref_output, spec, config)
        for ref_path in generated_refs:
            print(f"  -> Generated {ref_path}")
    except Exception as e:
        print(f"  -> Error generating API reference: {e}")
        return 1

    # Generate version_info.yml manifest
    meta_dir = project_root / "ansible_collections" / "ilyagulya" / "remnawave" / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    version_info_path = meta_dir / "version_info.yml"
    version_info = {
        "collection_version": collection_version,
        "remnawave_api_version": api_version,
        "generator_version": collection_version,
    }
    print(f"\nGenerating {version_info_path}...")
    with open(version_info_path, "w") as f:
        f.write("# Auto-generated - DO NOT EDIT\n")
        yaml.dump(version_info, f, default_flow_style=False, sort_keys=False)
    print(f"  -> Generated {version_info_path}")

    # Copy LICENSE file to collection
    license_src = project_root / "LICENSE"
    license_dst = project_root / "ansible_collections" / "ilyagulya" / "remnawave" / "LICENSE"
    if license_src.exists():
        shutil.copy(license_src, license_dst)
        print(f"  -> Copied {license_dst}")

    print("\nGeneration complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
