"""Tools for listing available parameter classes."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index


@mcp.tool()
def get_parameter_list() -> str:
    """Get a concise list of all Pywr-DRB parameter classes, grouped by module.

    Returns class names, base classes, and one-line descriptions for every
    parameter class in the codebase.
    """
    by_module: dict[str, list] = {}
    for name in sorted(index.parameter_index.keys()):
        entry = index.parameter_index[name]
        module = entry["module"]
        doc = entry["docstring"] or ""
        first_line = doc.strip().split("\n")[0][:150] if doc else "(no description)"
        by_module.setdefault(module, []).append({
            "name": name,
            "bases": entry["bases"],
            "description": first_line,
            "method_count": entry["method_count"],
        })

    return json.dumps({
        "parameter_classes": by_module,
        "total_count": len(index.parameter_index),
    }, indent=2)
