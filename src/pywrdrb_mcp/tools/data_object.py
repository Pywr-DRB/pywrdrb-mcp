"""Tools for querying the pywrdrb Data class structure and output schema."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import extract_class_info


@mcp.tool()
def get_data_object_info() -> str:
    """Get the structure of the pywrdrb Data object and how simulation results are stored.

    Returns the Data class hierarchy, available loading methods, results_set
    options per loader, and the storage access pattern.
    """
    # Get Data class methods via AST
    filepath = PYWRDRB_ROOT / "load" / "data_loader.py"
    methods_info = []
    try:
        classes = extract_class_info(filepath, class_name="Data")
        if classes:
            for m in classes[0]["methods"]:
                if not m["name"].startswith("_"):
                    doc = m["docstring"]
                    first = doc.strip().split("\n")[0] if doc else "(no description)"
                    methods_info.append({"name": m["name"], "description": first})
    except Exception:
        pass

    result = {
        "overview": (
            "The Data class is the unified interface for loading observations, "
            "simulation output, and hydrologic model data. All data is stored as "
            "pandas DataFrames organized by results_set, data source label, and scenario index."
        ),
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
                    "major_flow",
                    "reservoir_downstream_gage",
                    "res_storage",
                    "flood_gage_flow",
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
        "methods": methods_info,
    }

    return json.dumps(result, indent=2)
