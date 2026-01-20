"""Configuration loading for the Remnawave Ansible Module Generator."""

from pathlib import Path
from typing import Any, cast

import yaml
from prance import ResolvingParser


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
    except Exception as e:
        # Fall back to plain YAML loading if flex fails
        print(f"Warning: ResolvingParser failed ({e}), falling back to plain YAML loading")
        with open(spec_path) as f:
            return cast(dict[str, Any], yaml.safe_load(f))
