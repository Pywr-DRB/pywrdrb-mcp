"""Tools for querying the pywrdrb Data class structure and output schema."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import extract_class_info


def _extract_loader_methods(rel_path: str, class_name: str) -> list[dict]:
    """Extract public method info from a loader class."""
    filepath = PYWRDRB_ROOT / rel_path
    if not filepath.exists():
        return []
    try:
        classes = extract_class_info(filepath, class_name=class_name)
        if not classes:
            return []
        methods = []
        for m in classes[0]["methods"]:
            if m["name"].startswith("_") and m["name"] != "__init__":
                continue
            doc = m["docstring"]
            first = doc.strip().split("\n")[0] if doc else "(no description)"
            args = [a["name"] for a in m["args"] if a["name"] != "self"]
            methods.append({"name": m["name"], "args": args, "description": first})
        return methods
    except Exception:
        return []


@mcp.tool()
def get_data_object_info() -> str:
    """Get the structure of the pywrdrb Data object and how simulation results are stored.

    Returns the Data class hierarchy, available loading methods, results_set
    options per loader, and the storage access pattern.
    """
    # Dynamically extract methods from each loader class
    loader_hierarchy = {}
    for rel_path, cls_name in [
        ("load/data_loader.py", "Data"),
        ("load/output_loader.py", "Output"),
        ("load/observation_loader.py", "Observation"),
        ("load/hydrologic_model_loader.py", "HydrologicModelFlow"),
    ]:
        methods = _extract_loader_methods(rel_path, cls_name)
        if methods:
            loader_hierarchy[cls_name] = {"file": rel_path, "methods": methods}

    result = {
        "overview": (
            "The Data class is the unified interface for loading observations, "
            "simulation output, and hydrologic model data. All data is stored as "
            "pandas DataFrames organized by results_set, data source label, and scenario index."
        ),
        "class_hierarchy": "AbstractDataLoader → Output, Observation, HydrologicModelFlow → Data",
        "access_pattern": {
            "syntax": "data.{results_set}['{source_label}'][scenario_id]",
            "example": 'data.major_flow["drb_output_nhmv10"][0]',
            "returns": "pd.DataFrame with datetime index and node-name columns",
        },
        "source_labels": {
            "output": "Derived from HDF5 filename stem (e.g., 'drb_output_nhmv10.hdf5' → 'drb_output_nhmv10')",
            "observations": "'obs'",
            "hydrologic_model": "The flowtype string (e.g., 'nhmv10', 'nwmv21')",
        },
        "loading_methods": {
            "load_output()": {
                "description": "Load Pywr-DRB HDF5 simulation results",
                "valid_results_sets": list(index.results_set_descriptions.keys()),
            },
            "load_observations()": {
                "description": "Load USGS observation data",
                "valid_results_sets": [
                    "major_flow", "reservoir_downstream_gage",
                    "res_storage", "flood_gage_flow",
                ],
            },
            "load_hydrologic_model_flow()": {
                "description": "Load raw hydrologic model inflow data (NHM, NWM, etc.)",
                "valid_results_sets": ["all", "major_flow", "reservoir_downstream_gage"],
            },
            "load_from_export()": {
                "description": "Load from a previously exported HDF5 file",
                "valid_results_sets": "Any (depends on what was exported)",
            },
            "export()": {
                "description": "Export loaded data to HDF5",
                "hdf5_structure": "/{results_set}/{source_label}/{scenario_id}",
            },
        },
        "hdf5_output_key_conventions": {
            "description": "Raw HDF5 output files use these naming patterns for variables",
            "patterns": {
                "reservoir_{name}": "Reservoir storage (e.g., reservoir_cannonsville)",
                "link_{name}": "Flow through a link/river node (e.g., link_delMontague)",
                "outflow_{name}": "Reservoir outflow/release (e.g., outflow_cannonsville)",
                "spill_{name}": "Reservoir spill (e.g., spill_cannonsville)",
                "catchment_{name}": "Catchment inflow (e.g., catchment_cannonsville)",
            },
            "note": "The results_set abstraction maps these raw keys to cleaner node-name columns",
        },
        "loader_classes": loader_hierarchy,
    }

    return json.dumps(result, indent=2)
