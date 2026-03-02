"""Tool for querying Pywr-DRB parameter class details."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.index.ast_utils import extract_class_info
from pywrdrb_mcp.config import PYWRDRB_ROOT


@mcp.tool()
def get_parameter_class_info(class_name: str) -> str:
    """Get detailed information about a specific Pywr-DRB parameter class.

    Returns the class docstring, __init__ signature, all method names with
    signatures, base classes, and source module location.

    Args:
        class_name: Name of the parameter class (e.g., 'STARFITReservoirRelease', 'FfmpNycRunningAvgParameter').
    """
    # Look up in the cached index
    entry = index.parameter_index.get(class_name)
    if entry is None:
        # Try case-insensitive match
        for name, e in index.parameter_index.items():
            if name.lower() == class_name.lower():
                entry = e
                class_name = name
                break

    if entry is None:
        available = sorted(index.parameter_index.keys())
        return json.dumps({
            "error": f"Parameter class '{class_name}' not found.",
            "available_classes": available,
        }, indent=2)

    # On-demand: get full method details from AST
    filepath = index.parameter_files.get(class_name)
    if filepath is None:
        return json.dumps(entry, indent=2)

    classes = extract_class_info(filepath, class_name=class_name)
    if not classes:
        return json.dumps(entry, indent=2)

    cls = classes[0]
    result = {
        "name": cls["name"],
        "module": entry["module"],
        "line": cls["lineno"],
        "bases": cls["bases"],
        "docstring": cls["docstring"],
        "methods": [],
    }

    for m in cls["methods"]:
        args_str = ", ".join(
            a["name"] + (f": {a['annotation']}" if "annotation" in a else "")
            for a in m["args"]
        )
        result["methods"].append({
            "name": m["name"],
            "signature": f"{m['name']}({args_str})",
            "docstring": m["docstring"],
            "line": m["lineno"],
        })

    return json.dumps(result, indent=2)
