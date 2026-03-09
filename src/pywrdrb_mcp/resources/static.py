"""MCP resource registrations — pre-computed reference data and parameterized templates."""

from __future__ import annotations

import json
from pathlib import Path

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.config import PYWRDRB_ROOT


# ── Content directory for hand-written domain knowledge ──────────────
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def _read_content(filename: str) -> str:
    """Read a markdown file from the content/ directory."""
    path = CONTENT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"(Content file '{filename}' not found)"


# ═══════════════════════════════════════════════════════════════════════
# AUTO-GENERATED RESOURCES (built from index data)
# ═══════════════════════════════════════════════════════════════════════


@mcp.resource("pywrdrb://topology/network-graph")
def network_graph() -> str:
    """Full river network topology as JSON.

    Contains upstream_nodes, immediate_downstream, and downstream_lags
    for every node in the Pywr-DRB model.
    """
    return json.dumps({
        "upstream_nodes": index.upstream_nodes,
        "immediate_downstream": index.immediate_downstream,
        "downstream_lags": index.downstream_lags,
    }, indent=2)


@mcp.resource("pywrdrb://topology/reservoir-list")
def reservoir_list_resource() -> str:
    """All 17 reservoirs with type classification, downstream connectivity, and gage info."""
    reservoirs = []
    for r in index.reservoir_list:
        rtype = "NYC" if r in index.reservoir_list_nyc else "STARFIT"
        if r in index.drbc_lower_basin_reservoirs:
            rtype = "Lower Basin (modified STARFIT)"
        reservoirs.append({
            "name": r,
            "type": rtype,
            "is_nyc": r in index.reservoir_list_nyc,
            "is_starfit": r in index.starfit_reservoir_list,
            "is_lower_basin": r in index.drbc_lower_basin_reservoirs,
            "is_independent_starfit": r in index.independent_starfit_reservoirs,
            "capacity_mg": index.reservoir_capacities.get(r),
            "downstream_node": index.immediate_downstream.get(r),
            "downstream_gage": index.reservoir_link_pairs.get(r),
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


@mcp.resource("pywrdrb://topology/node-list")
def node_list_resource() -> str:
    """All nodes in the Pywr-DRB river network, organized by type."""
    return json.dumps({
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
    }, indent=2)


@mcp.resource("pywrdrb://api/parameter-class-index")
def parameter_class_index() -> str:
    """Index of all parameter classes with module, base class, and one-line description."""
    lines = ["# Pywr-DRB Parameter Class Index\n"]
    lines.append("| Class | Module | Base | Description |")
    lines.append("|---|---|---|---|")

    for name in sorted(index.parameter_index.keys()):
        entry = index.parameter_index[name]
        bases = ", ".join(entry["bases"]) if entry["bases"] else "—"
        doc = entry["docstring"] or ""
        first_line = doc.strip().split("\n")[0][:120] if doc else "(no description)"
        lines.append(f"| `{name}` | `{entry['module']}` | {bases} | {first_line} |")

    return "\n".join(lines)


@mcp.resource("pywrdrb://api/model-builder-api")
def model_builder_api() -> str:
    """ModelBuilder class method summary."""
    from pywrdrb_mcp.index.ast_utils import extract_class_info

    classes = extract_class_info(PYWRDRB_ROOT / "model_builder.py", class_name="ModelBuilder")
    if not classes:
        return "Could not parse ModelBuilder class."

    cls = classes[0]
    lines = [
        "# ModelBuilder API\n",
        f"**Docstring:** {(cls['docstring'] or '').strip().split(chr(10))[0]}\n",
        "## Methods\n",
    ]

    for m in cls["methods"]:
        doc = m["docstring"]
        first = doc.strip().split("\n")[0] if doc else "(no description)"
        lines.append(f"- **{m['name']}()** — {first}")

    return "\n".join(lines)


@mcp.resource("pywrdrb://api/data-loader-api")
def data_loader_api() -> str:
    """Data class hierarchy, methods, and results_set options."""
    from pywrdrb_mcp.index.ast_utils import extract_class_info

    lines = ["# Data Loader API\n"]

    # Show the loader hierarchy
    loader_files = [
        ("load/abstract_loader.py", "AbstractDataLoader"),
        ("load/output_loader.py", "Output"),
        ("load/observation_loader.py", "Observation"),
        ("load/hydrologic_model_loader.py", "HydrologicModelFlow"),
        ("load/data_loader.py", "Data"),
    ]

    for rel_path, cls_name in loader_files:
        filepath = PYWRDRB_ROOT / rel_path
        if not filepath.exists():
            continue
        classes = extract_class_info(filepath, class_name=cls_name)
        if not classes:
            continue
        cls = classes[0]
        bases = ", ".join(cls["bases"]) if cls["bases"] else ""
        doc_first = (cls["docstring"] or "").strip().split("\n")[0]
        lines.append(f"## {cls_name}({bases})")
        if doc_first:
            lines.append(f"_{doc_first}_\n")
        for m in cls["methods"]:
            if m["name"].startswith("_") and m["name"] != "__init__":
                continue
            doc = m["docstring"]
            first = doc.strip().split("\n")[0] if doc else "(no description)"
            lines.append(f"- **{m['name']}()** — {first}")
        lines.append("")

    lines.append("## Results Set Options\n")
    lines.append("| results_set | Description |")
    lines.append("|---|---|")
    for rs, desc in index.results_set_descriptions.items():
        lines.append(f"| `{rs}` | {desc} |")

    lines.append("\n## Valid Results Sets by Loader\n")
    lines.append("- **load_output()**: All results_sets")
    lines.append("- **load_observations()**: major_flow, reservoir_downstream_gage, res_storage, flood_gage_flow")
    lines.append("- **load_hydrologic_model_flow()**: all, major_flow, reservoir_downstream_gage")

    return "\n".join(lines)


@mcp.resource("pywrdrb://api/post-processing-api")
def post_processing_api() -> str:
    """Post-processing function signatures from metrics.py and calculate_error_metrics.py."""
    from pywrdrb_mcp.index.ast_utils import extract_function_info

    lines = ["# Post-Processing API\n"]

    for rel_path, label in [
        ("post/metrics.py", "Performance Metrics"),
        ("post/calculate_error_metrics.py", "Error Metrics"),
    ]:
        filepath = PYWRDRB_ROOT / rel_path
        if not filepath.exists():
            continue
        functions = extract_function_info(filepath)
        if not functions:
            continue
        lines.append(f"## {label} (`{rel_path}`)\n")
        for fn in functions:
            doc = fn["docstring"]
            first = doc.strip().split("\n")[0] if doc else "(no description)"
            args = ", ".join(a["name"] for a in fn["args"])
            lines.append(f"- **{fn['name']}**({args}) — {first}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("pywrdrb://api/preprocessing-api")
def preprocessing_api() -> str:
    """Preprocessing class and function signatures from pre/ modules."""
    from pywrdrb_mcp.index.ast_utils import extract_class_info, extract_function_info

    lines = ["# Preprocessing API\n"]

    modules = [
        ("pre/predict_inflows.py", "Inflow Prediction"),
        ("pre/predict_timeseries.py", "Base Prediction"),
        ("pre/flows.py", "Flow Preprocessing"),
        ("pre/predict_diversions.py", "Diversion Prediction"),
        ("pre/obs_data_retrieval.py", "Observation Data Retrieval"),
    ]

    for rel_path, label in modules:
        filepath = PYWRDRB_ROOT / rel_path
        if not filepath.exists():
            continue

        lines.append(f"## {label} (`{rel_path}`)\n")

        classes = extract_class_info(filepath)
        for cls in classes:
            bases = ", ".join(cls["bases"]) if cls["bases"] else ""
            doc_first = (cls["docstring"] or "").strip().split("\n")[0]
            lines.append(f"### {cls['name']}({bases})")
            if doc_first:
                lines.append(f"_{doc_first}_\n")
            for m in cls["methods"]:
                if m["name"].startswith("_") and m["name"] != "__init__":
                    continue
                doc = m["docstring"]
                first = doc.strip().split("\n")[0] if doc else "(no description)"
                lines.append(f"- **{m['name']}()** — {first}")
            lines.append("")

        functions = extract_function_info(filepath)
        for fn in functions:
            doc = fn["docstring"]
            first = doc.strip().split("\n")[0] if doc else "(no description)"
            lines.append(f"- **{fn['name']}()** — {first}")
        if functions:
            lines.append("")

    return "\n".join(lines)


@mcp.resource("pywrdrb://api/nyc-operations-config")
def nyc_operations_config_api() -> str:
    """NYCOperationsConfig class structure and methods for modifying FFMP rules."""
    from pywrdrb_mcp.index.ast_utils import extract_class_info

    filepath = PYWRDRB_ROOT / "parameters" / "nyc_operations_config.py"
    classes = extract_class_info(filepath, class_name="NYCOperationsConfig")

    if not classes:
        return "Could not parse NYCOperationsConfig class."

    cls = classes[0]
    lines = [
        "# NYCOperationsConfig API\n",
        f"_{(cls['docstring'] or '').strip().split(chr(10))[0]}_\n",
        "## Methods\n",
    ]

    for m in cls["methods"]:
        if m["name"].startswith("_") and m["name"] != "__init__":
            continue
        doc = m["docstring"]
        first = doc.strip().split("\n")[0] if doc else "(no description)"
        args = ", ".join(
            f"{a['name']}: {a.get('annotation', '')}" if a.get("annotation") else a["name"]
            for a in m["args"]
            if a["name"] != "self"
        )
        lines.append(f"- **{m['name']}**({args}) — {first}")

    return "\n".join(lines)


@mcp.resource("pywrdrb://data/inflow-types")
def inflow_types() -> str:
    """Available inflow types with date ranges and usage guidance."""
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


@mcp.resource("pywrdrb://data/results-sets")
def results_sets() -> str:
    """All results_set options with descriptions and valid data sources per loader."""
    return json.dumps({
        "results_sets": index.results_set_descriptions,
        "total_count": len(index.results_set_descriptions),
        "valid_by_loader": {
            "load_output": "All results_sets listed above",
            "load_observations": ["major_flow", "reservoir_downstream_gage", "res_storage", "flood_gage_flow"],
            "load_hydrologic_model_flow": ["all", "major_flow", "reservoir_downstream_gage"],
        },
        "usage": "Pass as results_sets=['major_flow', 'res_storage'] to Data()",
    }, indent=2)


@mcp.resource("pywrdrb://domain/constants")
def constants_resource() -> str:
    """Unit conversion constants used throughout Pywr-DRB."""
    return json.dumps(index.constants, indent=2)


@mcp.resource("pywrdrb://project/package-structure")
def package_structure() -> str:
    """Pywr-DRB package file tree with module descriptions."""
    lines = ["# Pywr-DRB Package Structure\n"]
    for path, docstring in sorted(index.package_structure.items()):
        doc_summary = ""
        if docstring:
            doc_summary = f" — {docstring.strip().split(chr(10))[0][:100]}"
        lines.append(f"- `{path}`{doc_summary}")
    return "\n".join(lines)


@mcp.resource("pywrdrb://project/repo-status")
def repo_status_resource() -> str:
    """Current git branch, recent commits, and modified files for the Pywr-DRB source repo."""
    from pywrdrb_mcp.tools.data import get_repo_status
    return get_repo_status()


# ═══════════════════════════════════════════════════════════════════════
# PARAMETERIZED RESOURCE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════


@mcp.resource("pywrdrb://parameter/{class_name}")
def parameter_resource(class_name: str) -> str:
    """Detailed information for a specific parameter class."""
    from pywrdrb_mcp.tools.parameters import get_parameter_class_info
    return get_parameter_class_info(class_name)


@mcp.resource("pywrdrb://reservoir/{reservoir_name}")
def reservoir_resource(reservoir_name: str) -> str:
    """Detailed information for a specific reservoir."""
    from pywrdrb_mcp.tools.topology import get_reservoir_details
    return get_reservoir_details(reservoir_name)


# ═══════════════════════════════════════════════════════════════════════
# HAND-WRITTEN CONTENT RESOURCES
# ═══════════════════════════════════════════════════════════════════════


@mcp.resource("pywrdrb://domain/rating-curves")
def rating_curves_resource() -> str:
    """USGS rating curve metadata for flood monitoring gages (stage-discharge conversion)."""
    # Map site numbers to node names for context
    site_to_node = {
        "01426500": "cannonsville (Hale Eddy)",
        "01421000": "pepacton (Fishs Eddy)",
        "01436690": "neversink (Bridgeville)",
    }
    result = {}
    for site_no, meta in index.rating_curve_metadata.items():
        entry = dict(meta)
        entry["downstream_of_reservoir"] = site_to_node.get(site_no, "unknown")
        result[site_no] = entry
    return json.dumps(result, indent=2)


@mcp.resource("pywrdrb://domain/ffmp-rules-summary")
def ffmp_rules() -> str:
    """Comprehensive FFMP rules: drought levels, storage zones, MRF targets, delivery constraints."""
    return _read_content("ffmp_rules.md")


@mcp.resource("pywrdrb://domain/starfit-rules-summary")
def starfit_rules() -> str:
    """STARFIT reservoir release policy: harmonic terms, storage factors, constraints."""
    return _read_content("starfit_rules.md")


@mcp.resource("pywrdrb://domain/flood-operations-summary")
def flood_operations() -> str:
    """Flood monitoring stages, rating curves, thresholds, and flood-responsive operations."""
    return _read_content("flood_operations.md")


@mcp.resource("pywrdrb://domain/post-processing-guide")
def post_processing_guide() -> str:
    """Performance metrics, shortfall analysis, and error metrics guide."""
    return _read_content("post_processing.md")


@mcp.resource("pywrdrb://domain/preprocessing-guide")
def preprocessing_guide() -> str:
    """Inflow prediction, flow preprocessing, and data retrieval guide."""
    return _read_content("preprocessing.md")


@mcp.resource("pywrdrb://domain/data-loading-guide")
def data_loading_guide() -> str:
    """Data loading patterns, results_set descriptions, and HDF5 conventions."""
    return _read_content("data_loading.md")


@mcp.resource("pywrdrb://project/getting-started")
def getting_started() -> str:
    """Getting started guide with example workflow."""
    return _read_content("getting_started.md")
