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
    """All 17 reservoirs with type classification (NYC / STARFIT / Lower Basin)."""
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
        })
    return json.dumps(reservoirs, indent=2)


@mcp.resource("pywrdrb://topology/node-list")
def node_list_resource() -> str:
    """Major flow nodes and flood monitoring nodes."""
    return json.dumps({
        "major_flow_nodes": index.majorflow_list,
        "flood_monitoring_nodes": index.flood_monitoring_nodes,
        "all_nodes": index.all_node_names,
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
    """Data class methods and results_set options."""
    from pywrdrb_mcp.index.ast_utils import extract_class_info

    filepath = PYWRDRB_ROOT / "load" / "data_loader.py"
    classes = extract_class_info(filepath, class_name="Data")

    lines = ["# Data Loader API\n"]

    if classes:
        cls = classes[0]
        lines.append(f"**Docstring:** {(cls['docstring'] or '').strip().split(chr(10))[0]}\n")
        lines.append("## Methods\n")
        for m in cls["methods"]:
            if m["name"].startswith("__") and m["name"] != "__init__":
                continue
            doc = m["docstring"]
            first = doc.strip().split("\n")[0] if doc else "(no description)"
            lines.append(f"- **{m['name']}()** — {first}")

    lines.append("\n## Results Set Options\n")
    lines.append("| results_set | Description |")
    lines.append("|---|---|")
    for rs, desc in index.results_set_descriptions.items():
        lines.append(f"| `{rs}` | {desc} |")

    return "\n".join(lines)


@mcp.resource("pywrdrb://data/inflow-types")
def inflow_types() -> str:
    """Available inflow types with date ranges."""
    return json.dumps(index.model_date_ranges, indent=2)


@mcp.resource("pywrdrb://data/results-sets")
def results_sets() -> str:
    """All results_set options with descriptions."""
    return json.dumps(index.results_set_descriptions, indent=2)


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


@mcp.resource("pywrdrb://project/getting-started")
def getting_started() -> str:
    """Getting started guide with example workflow."""
    return _read_content("getting_started.md")
