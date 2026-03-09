"""Tools for querying the Pywr-DRB river network topology."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index


@mcp.tool()
def get_node_topology(
    node_name: str,
    include_flood_topology: bool = False,
) -> str:
    """Look up the river network topology for a specific node.

    Returns upstream nodes, downstream node, travel time lag, and optionally
    USGS/NHM/NWM gage IDs for the given node.

    Args:
        node_name: Name of a river network node (e.g., 'delMontague', 'cannonsville').
        include_flood_topology: If True, also include flood monitoring info.
    """
    if node_name not in index.all_node_names:
        # Try case-insensitive lookup
        matches = [n for n in index.all_node_names if n.lower() == node_name.lower()]
        if matches:
            node_name = matches[0]
        else:
            return json.dumps({
                "error": f"Node '{node_name}' not found.",
                "available_nodes": index.all_node_names,
            }, indent=2)

    result: dict = {
        "node": node_name,
        "upstream_nodes": index.upstream_nodes.get(node_name, []),
        "downstream_node": index.immediate_downstream.get(node_name),
        "downstream_lag_days": index.downstream_lags.get(node_name),
        "gage_ids": {
            "usgs_obs": index.obs_site_matches.get(node_name),
            "usgs_pub": index.obs_pub_site_matches.get(node_name),
            "nhm": index.nhm_site_matches.get(node_name),
            "nwm": index.nwm_site_matches.get(node_name),
            "wrf_hydro": index.wrf_hydro_site_matches.get(node_name),
        },
    }

    if node_name in index.storage_gauge_map:
        result["storage_gauge"] = index.storage_gauge_map[node_name]

    if include_flood_topology:
        if node_name in index.flood_stage_thresholds:
            result["flood_thresholds"] = index.flood_stage_thresholds[node_name]
        # Include rating curve metadata if available for this node's gage
        gage_ids = result.get("gage_ids", {})
        obs_ids = gage_ids.get("usgs_obs") or []
        for site_no in obs_ids:
            if site_no in index.rating_curve_metadata:
                result["rating_curve"] = index.rating_curve_metadata[site_no]
                break

    is_flood_node = node_name in index.flood_monitoring_nodes
    result["is_flood_monitoring_node"] = is_flood_node

    return json.dumps(result, indent=2)


@mcp.tool()
def get_reservoir_details(reservoir_name: str) -> str:
    """Get aggregated details for a specific reservoir.

    Returns reservoir type (NYC/STARFIT/lower basin), downstream node, gage IDs
    across all data sources, and list classifications.

    Args:
        reservoir_name: Name of a reservoir (e.g., 'cannonsville', 'blueMarsh').
    """
    if reservoir_name not in index.reservoir_list:
        matches = [r for r in index.reservoir_list if r.lower() == reservoir_name.lower()]
        if matches:
            reservoir_name = matches[0]
        else:
            return json.dumps({
                "error": f"Reservoir '{reservoir_name}' not found.",
                "available_reservoirs": index.reservoir_list,
            }, indent=2)

    # Classify
    res_type = "NYC" if reservoir_name in index.reservoir_list_nyc else "STARFIT"
    classifications = []
    if reservoir_name in index.reservoir_list_nyc:
        classifications.append("nyc")
    if reservoir_name in index.starfit_reservoir_list:
        classifications.append("starfit")
    if reservoir_name in index.drbc_lower_basin_reservoirs:
        classifications.append("drbc_lower_basin")
        res_type = "Lower Basin (modified STARFIT)"
    if reservoir_name in index.modified_starfit_reservoir_list:
        classifications.append("modified_starfit")
    if reservoir_name in index.independent_starfit_reservoirs:
        classifications.append("independent_starfit")

    result = {
        "reservoir": reservoir_name,
        "type": res_type,
        "classifications": classifications,
        "capacity_mg": index.reservoir_capacities.get(reservoir_name),
        "mean_flow_mgd": index.reservoir_mean_flows.get(reservoir_name),
        "downstream_node": index.immediate_downstream.get(reservoir_name),
        "downstream_lag_days": index.downstream_lags.get(reservoir_name),
        "downstream_gage": index.reservoir_link_pairs.get(reservoir_name),
        "gage_ids": {
            "usgs_obs": index.obs_site_matches.get(reservoir_name),
            "usgs_pub": index.obs_pub_site_matches.get(reservoir_name),
            "nhm": index.nhm_site_matches.get(reservoir_name),
            "nwm": index.nwm_site_matches.get(reservoir_name),
            "wrf_hydro": index.wrf_hydro_site_matches.get(reservoir_name),
            "storage_gauge": index.storage_gauge_map.get(reservoir_name),
        },
        "upstream_nodes": index.upstream_nodes.get(reservoir_name, []),
    }

    if reservoir_name in index.reservoir_starfit_params:
        result["starfit_params"] = index.reservoir_starfit_params[reservoir_name]

    if reservoir_name in index.flood_stage_thresholds:
        result["flood_thresholds"] = index.flood_stage_thresholds[reservoir_name]

    return json.dumps(result, indent=2)
