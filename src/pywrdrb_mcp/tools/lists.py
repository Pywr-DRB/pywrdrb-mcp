"""Tools for listing available nodes, reservoirs, parameters, and variables."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index


@mcp.tool()
def get_node_list() -> str:
    """Get all nodes in the Pywr-DRB river network, organized by type.

    Returns major flow nodes, reservoir nodes, flood monitoring nodes,
    and gage nodes with brief descriptions of each category.
    """
    result = {
        "reservoir_nodes": {
            "nyc": index.reservoir_list_nyc,
            "starfit": index.starfit_reservoir_list,
            "lower_basin": index.drbc_lower_basin_reservoirs,
        },
        "major_flow_nodes": index.majorflow_list,
        "flood_monitoring_nodes": [
            {"id": "01426500", "name": "Hale Eddy", "downstream_of": "cannonsville"},
            {"id": "01421000", "name": "Fishs Eddy", "downstream_of": "pepacton"},
            {"id": "01436690", "name": "Bridgeville", "downstream_of": "neversink"},
        ],
        "all_nodes": index.all_node_names,
        "total_count": len(index.all_node_names),
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def get_reservoir_list() -> str:
    """Get all 17 reservoirs with type classification and key attributes.

    Each reservoir includes its type (NYC/STARFIT/Lower Basin), downstream
    node, whether it has a downstream gage, and list memberships.
    """
    reservoirs = []
    for r in index.reservoir_list:
        rtype = "NYC" if r in index.reservoir_list_nyc else "STARFIT"
        if r in index.drbc_lower_basin_reservoirs:
            rtype = "Lower Basin (modified STARFIT)"

        reservoirs.append({
            "name": r,
            "type": rtype,
            "downstream_node": index.immediate_downstream.get(r),
            "downstream_gage": index.reservoir_link_pairs.get(r),
            "is_independent_starfit": r in index.independent_starfit_reservoirs,
        })

    return json.dumps({
        "reservoirs": reservoirs,
        "counts": {
            "total": len(index.reservoir_list),
            "nyc": len(index.reservoir_list_nyc),
            "starfit": len(index.starfit_reservoir_list),
            "lower_basin": len(index.drbc_lower_basin_reservoirs),
        },
    }, indent=2)


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


@mcp.tool()
def get_results_set_list() -> str:
    """Get all available results_set options for loading simulation output.

    Results sets define what data categories can be loaded from Pywr-DRB
    output files (e.g., 'major_flow', 'res_storage', 'res_release').
    Each results_set maps to specific model node/parameter names.
    """
    return json.dumps({
        "results_sets": index.results_set_descriptions,
        "total_count": len(index.results_set_descriptions),
        "usage": "Pass these as results_sets=['major_flow', 'res_storage'] to Data()",
    }, indent=2)


@mcp.tool()
def get_inflow_type_list() -> str:
    """Get all available inflow data types with their date ranges.

    Inflow types correspond to different hydrologic model sources (NHM, NWM,
    WRF-Hydro) and processed variants (observation-scaled, reconstructions).
    """
    inflows = []
    for name, (start, end) in sorted(index.model_date_ranges.items()):
        inflows.append({
            "inflow_type": name,
            "start_date": start,
            "end_date": end,
        })

    return json.dumps({
        "inflow_types": inflows,
        "total_count": len(inflows),
        "usage": "Pass as inflow_type to ModelBuilder(start, end, inflow_type)",
    }, indent=2)