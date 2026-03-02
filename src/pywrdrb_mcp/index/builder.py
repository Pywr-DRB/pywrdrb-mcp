"""PywrDRBIndex — one-time startup indexer that caches structured data about the Pywr-DRB codebase.

Built once when the MCP server starts; tools and resources read from it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import (
    extract_class_info,
    extract_dataclass_fields,
    extract_module_level_dict,
    extract_module_level_list,
    extract_module_level_value,
    _MISSING,
)
from pywrdrb_mcp.index.file_utils import get_package_structure

log = logging.getLogger(__name__)


class PywrDRBIndex:
    """Cached index of the Pywr-DRB codebase, built from static analysis."""

    def __init__(self) -> None:
        log.info("Building PywrDRBIndex from %s ...", PYWRDRB_ROOT)
        self._build()
        log.info("PywrDRBIndex ready.")

    def _build(self) -> None:
        self._build_topology()
        self._build_lists()
        self._build_constants()
        self._build_flood_thresholds()
        self._build_parameter_index()
        self._build_results_sets()
        self._build_date_ranges()
        self._build_package_structure()

    def rebuild(self) -> dict:
        """Rebuild the entire index. Returns a summary of changes."""
        old_param_names = set(self.parameter_index.keys())
        old_file_count = len(self.package_structure)
        self._build()
        new_param_names = set(self.parameter_index.keys())
        new_file_count = len(self.package_structure)
        return {
            "added_parameters": sorted(new_param_names - old_param_names),
            "removed_parameters": sorted(old_param_names - new_param_names),
            "file_count_before": old_file_count,
            "file_count_after": new_file_count,
        }

    # ── Topology ──────────────────────────────────────────────────────

    def _build_topology(self) -> None:
        node_data = PYWRDRB_ROOT / "pywr_drb_node_data.py"

        self.upstream_nodes: dict = extract_module_level_dict(node_data, "upstream_nodes_dict") or {}
        self.immediate_downstream: dict = extract_module_level_dict(node_data, "immediate_downstream_nodes_dict") or {}
        self.downstream_lags: dict = extract_module_level_dict(node_data, "downstream_node_lags") or {}

        # Data source site matches
        self.obs_pub_site_matches: dict = extract_module_level_dict(node_data, "obs_pub_site_matches") or {}
        self.obs_site_matches: dict = extract_module_level_dict(node_data, "obs_site_matches") or {}
        self.nhm_site_matches: dict = extract_module_level_dict(node_data, "nhm_site_matches") or {}
        self.nwm_site_matches: dict = extract_module_level_dict(node_data, "nwm_site_matches") or {}
        self.wrf_hydro_site_matches: dict = extract_module_level_dict(node_data, "wrf_hydro_site_matches") or {}
        self.storage_gauge_map: dict = extract_module_level_dict(node_data, "storage_gauge_map") or {}
        self.nyc_reservoirs_from_node_data: list = extract_module_level_list(node_data, "nyc_reservoirs") or []

        # All node names (union of topology dict keys + site match keys + lists)
        all_nodes = set()
        all_nodes.update(self.upstream_nodes.keys())
        all_nodes.update(self.immediate_downstream.keys())
        all_nodes.update(self.obs_site_matches.keys())
        all_nodes.update(self.nhm_site_matches.keys())
        self.all_node_names = sorted(all_nodes)

    # ── Lists ─────────────────────────────────────────────────────────

    def _build_lists(self) -> None:
        lists_file = PYWRDRB_ROOT / "utils" / "lists.py"

        # Pure literals — extract directly
        self.reservoir_list: list = extract_module_level_list(lists_file, "reservoir_list") or []
        self.majorflow_list: list = extract_module_level_list(lists_file, "majorflow_list") or []
        self.majorflow_list_figs: list = extract_module_level_list(lists_file, "majorflow_list_figs") or []
        self.flood_monitoring_nodes: list = extract_module_level_list(lists_file, "flood_monitoring_nodes") or []
        self.reservoir_link_pairs: dict = extract_module_level_dict(lists_file, "reservoir_link_pairs") or {}
        self.starfit_reservoir_list: list = extract_module_level_list(lists_file, "starfit_reservoir_list") or []
        self.modified_starfit_reservoir_list: list = extract_module_level_list(lists_file, "modified_starfit_reservoir_list") or []
        self.drbc_lower_basin_reservoirs: list = extract_module_level_list(lists_file, "drbc_lower_basin_reservoirs") or []

        # Derived lists — computed from extracted base data
        self.reservoir_list_nyc: list = self.reservoir_list[:3]
        self.independent_starfit_reservoirs: list = [
            r for r in self.starfit_reservoir_list
            if r not in self.drbc_lower_basin_reservoirs
        ]
        self.required_model_reservoirs: list = self.reservoir_list_nyc + self.drbc_lower_basin_reservoirs
        self.seasons_dict: dict = {
            m: "DJF" if m in (12, 1, 2)
            else "MAM" if m in (3, 4, 5)
            else "JJA" if m in (6, 7, 8)
            else "SON"
            for m in range(1, 13)
        }

    # ── Constants ─────────────────────────────────────────────────────

    def _build_constants(self) -> None:
        constants_file = PYWRDRB_ROOT / "utils" / "constants.py"
        self.constants: dict[str, float] = {}

        # Pure literals
        for name in ("cms_to_mgd", "mcm_to_mg", "cfs_to_mgd", "epsilon", "ACRE_FEET_TO_MG"):
            val = extract_module_level_value(constants_file, name)
            if val is not _MISSING:
                self.constants[name] = val

        # Computed constants — evaluate manually
        self.constants["cm_to_mg"] = 264.17 / 1e6
        self.constants["mg_to_mcm"] = 1.0 / 264.17
        self.constants["GAL_TO_MG"] = 1 / 1_000_000

    # ── Flood Thresholds ──────────────────────────────────────────────

    def _build_flood_thresholds(self) -> None:
        ft_file = PYWRDRB_ROOT / "flood_thresholds.py"
        self.flood_stage_thresholds: dict = extract_module_level_dict(ft_file, "flood_stage_thresholds") or {}

    # ── Parameter Class Index ─────────────────────────────────────────

    def _build_parameter_index(self) -> None:
        """Scan all parameters/*.py files and build a class index."""
        self.parameter_index: dict[str, dict] = {}
        self.parameter_files: dict[str, Path] = {}  # class_name -> filepath

        params_dir = PYWRDRB_ROOT / "parameters"
        if not params_dir.exists():
            return

        for py_file in sorted(params_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            try:
                classes = extract_class_info(py_file)
            except Exception as e:
                log.warning("Failed to parse %s: %s", py_file.name, e)
                continue

            module_rel = f"parameters/{py_file.name}"
            for cls in classes:
                entry = {
                    "module": module_rel,
                    "name": cls["name"],
                    "bases": cls["bases"],
                    "docstring": cls["docstring"],
                    "method_count": len(cls["methods"]),
                    "methods_summary": [m["name"] for m in cls["methods"]],
                    "lineno": cls["lineno"],
                }
                self.parameter_index[cls["name"]] = entry
                self.parameter_files[cls["name"]] = py_file

    # ── Results Sets ──────────────────────────────────────────────────

    def _build_results_sets(self) -> None:
        rs_file = PYWRDRB_ROOT / "utils" / "results_sets.py"
        self.results_set_descriptions: dict = extract_module_level_dict(rs_file, "pywrdrb_results_set_descriptions") or {}

    # ── Date Ranges ───────────────────────────────────────────────────

    def _build_date_ranges(self) -> None:
        """Hard-coded date ranges (the source builds them procedurally)."""
        self.model_date_ranges: dict[str, tuple[str, str]] = {}
        for nxm in ["nhmv10", "nwmv21"]:
            self.model_date_ranges[nxm] = ("1983-10-01", "2016-12-31")
            self.model_date_ranges[f"{nxm}_withObsScaled"] = ("1983-10-01", "2016-12-31")
        self.model_date_ranges["wrf1960s_calib_nlcd2016"] = ("1959-10-01", "1969-12-31")
        self.model_date_ranges["wrf2050s_calib_nlcd2016"] = ("1959-10-01", "1969-12-31")
        self.model_date_ranges["wrfaorc_calib_nlcd2016"] = ("1979-10-01", "2021-12-31")
        self.model_date_ranges["wrfaorc_withObsScaled"] = ("1979-10-01", "2021-12-31")
        self.model_date_ranges["pub_nhmv10_BC_withObsScaled"] = ("1945-01-01", "2023-12-31")

    # ── Package Structure ─────────────────────────────────────────────

    def _build_package_structure(self) -> None:
        self.package_structure: dict[str, str | None] = get_package_structure()
