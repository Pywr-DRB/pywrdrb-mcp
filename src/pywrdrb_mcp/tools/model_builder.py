"""Tools for querying the ModelBuilder class and Options dataclass."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.index.ast_utils import (
    extract_class_info,
    extract_dataclass_fields,
    extract_method_source,
)
from pywrdrb_mcp.config import PYWRDRB_ROOT


_MB_FILE = PYWRDRB_ROOT / "model_builder.py"


@mcp.tool()
def get_model_builder_options() -> str:
    """Get all fields of the ModelBuilder Options dataclass.

    Returns field names, types, defaults, and descriptions for the Options
    dataclass that controls how Pywr-DRB simulations are configured.
    """
    fields = extract_dataclass_fields(_MB_FILE, "Options")
    if fields is None:
        return "Error: Could not extract Options dataclass fields."

    lines = ["# ModelBuilder Options\n"]
    lines.append("| Field | Type | Default | Description |")
    lines.append("|---|---|---|---|")
    for f in fields:
        default = f["default"] or "—"
        desc = f["description"] or ""
        lines.append(f"| `{f['name']}` | `{f['type']}` | `{default}` | {desc} |")

    return "\n".join(lines)


@mcp.tool()
def get_model_builder_method(method_name: str) -> str:
    """Get the full source code for a specific ModelBuilder method.

    Args:
        method_name: Name of the method (e.g., 'make_model', 'add_node_major_reservoir').
    """
    source = extract_method_source(_MB_FILE, "ModelBuilder", method_name)
    if source is None:
        # List available methods
        classes = extract_class_info(_MB_FILE, class_name="ModelBuilder")
        if classes:
            methods = [m["name"] for m in classes[0]["methods"]]
            return json.dumps({
                "error": f"Method '{method_name}' not found in ModelBuilder.",
                "available_methods": methods,
            }, indent=2)
        return f"Error: Method '{method_name}' not found and could not list available methods."

    return f"```python\n# ModelBuilder.{method_name}()\n{source}\n```"
