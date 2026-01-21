#!/usr/bin/env python3
"""
Version management for remnawave-ansible-gen.

Commands:
  show  - Display current versions
  check - Verify all versions are in sync
  sync  - Propagate version from pyproject.toml to all locations
"""

import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def read_pyproject_version() -> str:
    """Read version from pyproject.toml (source of truth)."""
    pyproject_path = get_project_root() / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def read_api_version() -> str:
    """Read Remnawave API version from OpenAPI spec."""
    spec_path = get_project_root() / "api-spec" / "api-1.yaml"
    with open(spec_path) as f:
        spec = cast(dict[str, Any], yaml.safe_load(f))
    return str(spec.get("info", {}).get("version", "unknown"))


def read_galaxy_version() -> str:
    """Read version from galaxy.yml."""
    galaxy_path = get_project_root() / "ansible_collections" / "ilyagulya" / "remnawave" / "galaxy.yml"
    with open(galaxy_path) as f:
        data = cast(dict[str, Any], yaml.safe_load(f))
    return str(data.get("version", "unknown"))


def read_init_version() -> str:
    """Read version from __init__.py."""
    init_path = get_project_root() / "src" / "remnawave_ansible_gen" / "__init__.py"
    content = init_path.read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        return "unknown"
    return match.group(1)


def read_readme_collection_version() -> str:
    """Read collection version from README.md."""
    readme_path = get_project_root() / "README.md"
    content = readme_path.read_text()
    # Match: **Collection version:** 0.1.0 (generated from Remnawave API 2.5.3)
    match = re.search(r"\*\*Collection version:\*\*\s*(\d+\.\d+\.\d+)", content)
    if not match:
        return "unknown"
    return match.group(1)


def read_readme_requirements_version() -> str:
    """Read requirements version from README.md."""
    readme_path = get_project_root() / "README.md"
    content = readme_path.read_text()
    # Match: version: ">=0.1.0"
    match = re.search(r'version:\s*">=(\d+\.\d+\.\d+)"', content)
    if not match:
        return "unknown"
    return match.group(1)


def read_version_info() -> dict[str, Any] | None:
    """Read version_info.yml if it exists."""
    version_info_path = get_project_root() / "ansible_collections" / "ilyagulya" / "remnawave" / "meta" / "version_info.yml"
    if not version_info_path.exists():
        return None
    with open(version_info_path) as f:
        return cast(dict[str, Any], yaml.safe_load(f))


def show_versions() -> None:
    """Display current versions from all locations."""
    print("Version Information")
    print("=" * 50)

    pyproject_version = read_pyproject_version()
    api_version = read_api_version()

    print("\nSource of Truth:")
    print(f"  pyproject.toml:          {pyproject_version}")
    print(f"  api-spec (API version):  {api_version}")

    print("\nDerived Locations:")
    print(f"  galaxy.yml:              {read_galaxy_version()}")
    print(f"  __init__.py:             {read_init_version()}")
    print(f"  README.md (collection):  {read_readme_collection_version()}")
    print(f"  README.md (requirements):{read_readme_requirements_version()}")

    version_info = read_version_info()
    if version_info:
        print("\nversion_info.yml:")
        print(f"  collection_version:      {version_info.get('collection_version', 'unknown')}")
        print(f"  remnawave_api_version:   {version_info.get('remnawave_api_version', 'unknown')}")
        print(f"  generator_version:       {version_info.get('generator_version', 'unknown')}")
    else:
        print("\nversion_info.yml: Not found (run 'uv run generate' to create)")


def check_versions() -> bool:
    """Check if all versions are in sync. Returns True if all are in sync."""
    pyproject_version = read_pyproject_version()
    api_version = read_api_version()

    errors = []

    # Check galaxy.yml
    galaxy_version = read_galaxy_version()
    if galaxy_version != pyproject_version:
        errors.append(f"galaxy.yml: expected {pyproject_version}, got {galaxy_version}")

    # Check __init__.py
    init_version = read_init_version()
    if init_version != pyproject_version:
        errors.append(f"__init__.py: expected {pyproject_version}, got {init_version}")

    # Check README.md collection version
    readme_version = read_readme_collection_version()
    if readme_version != pyproject_version:
        errors.append(f"README.md (collection): expected {pyproject_version}, got {readme_version}")

    # Check README.md requirements version
    readme_req_version = read_readme_requirements_version()
    if readme_req_version != pyproject_version:
        errors.append(f"README.md (requirements): expected {pyproject_version}, got {readme_req_version}")

    # Check version_info.yml if it exists
    version_info = read_version_info()
    if version_info:
        if version_info.get("collection_version") != pyproject_version:
            errors.append(
                f"version_info.yml (collection): expected {pyproject_version}, "
                f"got {version_info.get('collection_version')}"
            )
        if version_info.get("generator_version") != pyproject_version:
            errors.append(
                f"version_info.yml (generator): expected {pyproject_version}, "
                f"got {version_info.get('generator_version')}"
            )
        if version_info.get("remnawave_api_version") != api_version:
            errors.append(
                f"version_info.yml (api): expected {api_version}, got {version_info.get('remnawave_api_version')}"
            )

    if errors:
        print("Version check FAILED:")
        for error in errors:
            print(f"  - {error}")
        print(f"\nExpected collection version: {pyproject_version}")
        print(f"Expected API version: {api_version}")
        print("\nRun 'uv run version sync' to fix.")
        return False
    else:
        print("Version check PASSED")
        print(f"  Collection version: {pyproject_version}")
        print(f"  API version: {api_version}")
        return True


def sync_versions() -> None:
    """Sync all version locations from pyproject.toml."""
    pyproject_version = read_pyproject_version()
    api_version = read_api_version()

    print("Syncing versions...")
    print(f"  Collection version: {pyproject_version}")
    print(f"  API version: {api_version}")
    print()

    # Update galaxy.yml
    galaxy_path = get_project_root() / "ansible_collections" / "ilyagulya" / "remnawave" / "galaxy.yml"
    with open(galaxy_path) as f:
        galaxy_data = yaml.safe_load(f)
    if galaxy_data.get("version") != pyproject_version:
        galaxy_data["version"] = pyproject_version
        with open(galaxy_path, "w") as f:
            yaml.dump(galaxy_data, f, default_flow_style=False, sort_keys=False)
        print("  Updated galaxy.yml")
    else:
        print("  galaxy.yml already up to date")

    # Update __init__.py
    init_path = get_project_root() / "src" / "remnawave_ansible_gen" / "__init__.py"
    content = init_path.read_text()
    new_content = re.sub(
        r'^__version__\s*=\s*"[^"]+"', f'__version__ = "{pyproject_version}"', content, flags=re.MULTILINE
    )
    if content != new_content:
        init_path.write_text(new_content)
        print("  Updated __init__.py")
    else:
        print("  __init__.py already up to date")

    # Update README.md
    readme_path = get_project_root() / "README.md"
    content = readme_path.read_text()

    # Update collection version line
    new_content = re.sub(
        r"(\*\*Collection version:\*\*\s*)\d+\.\d+\.\d+(\s*\(generated from Remnawave API\s*)\d+\.\d+\.\d+(\))",
        rf"\g<1>{pyproject_version}\g<2>{api_version}\3",
        content,
    )

    # Update requirements version
    new_content = re.sub(
        r'(version:\s*">=)\d+\.\d+\.\d+(")',
        rf"\g<1>{pyproject_version}\2",
        new_content,
    )

    if content != new_content:
        readme_path.write_text(new_content)
        print("  Updated README.md")
    else:
        print("  README.md already up to date")

    print()
    print("Sync complete. Run 'uv run generate' to regenerate modules with correct versions.")


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run version <command>")
        print()
        print("Commands:")
        print("  show  - Display current versions")
        print("  check - Verify all versions are in sync")
        print("  sync  - Propagate version from pyproject.toml to all locations")
        return 1

    command = sys.argv[1]

    if command == "show":
        show_versions()
        return 0
    elif command == "check":
        return 0 if check_versions() else 1
    elif command == "sync":
        sync_versions()
        return 0
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
