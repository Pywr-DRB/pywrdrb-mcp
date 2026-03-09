"""PywrDRBIndex — one-time startup indexer that caches structured data about the Pywr-DRB codebase.

Built once when the MCP server starts; tools and resources read from it.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import (
    extract_class_info,
    extract_dataclass_fields,
    extract_dict_from_simple_script,
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
        self._build_reservoir_data()
        self._build_rating_curves()
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
        """Extract date ranges from utils/dates.py (built procedurally in source)."""
        dates_file = PYWRDRB_ROOT / "utils" / "dates.py"
        extracted = extract_dict_from_simple_script(dates_file, "model_date_ranges")
        if extracted:
            self.model_date_ranges = extracted
        else:
            log.warning("Could not extract model_date_ranges from dates.py, using fallback")
            self.model_date_ranges = {}

        # Also extract temperature prediction date range
        temp_range = extract_dict_from_simple_script(dates_file, "temp_pred_date_range")
        if isinstance(temp_range, tuple):
            self.temp_pred_date_range = temp_range
        else:
            # Try extracting as a module-level value
            val = extract_module_level_value(dates_file, "temp_pred_date_range")
            self.temp_pred_date_range = val if val is not _MISSING else None

    # ── Reservoir Data (from istarf CSV) ────────────────────────────

    def _build_reservoir_data(self) -> None:
        """Read reservoir capacity and STARFIT parameters from istarf_conus.csv."""
        istarf_path = PYWRDRB_ROOT / "data" / "operational_constants" / "istarf_conus.csv"
        self.reservoir_capacities: dict[str, float] = {}
        self.reservoir_mean_flows: dict[str, float] = {}
        self.reservoir_starfit_params: dict[str, dict] = {}

        if not istarf_path.exists():
            log.warning("istarf_conus.csv not found at %s", istarf_path)
            return

        try:
            with open(istarf_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("reservoir", "").strip()
                    if not name:
                        continue

                    # Capacity and mean flow
                    try:
                        self.reservoir_capacities[name] = float(row["Adjusted_CAP_MG"])
                    except (KeyError, ValueError):
                        pass
                    try:
                        self.reservoir_mean_flows[name] = float(row["Adjusted_MEANFLOW_MGD"])
                    except (KeyError, ValueError):
                        pass

                    # STARFIT harmonic coefficients
                    starfit_keys = [
                        "NORhi_alpha", "NORhi_beta", "NORhi_max", "NORhi_min", "NORhi_mu",
                        "NORlo_alpha", "NORlo_beta", "NORlo_max", "NORlo_min", "NORlo_mu",
                        "Release_alpha1", "Release_alpha2", "Release_beta1", "Release_beta2",
                        "Release_c", "Release_max", "Release_min", "Release_p1", "Release_p2",
                    ]
                    params = {}
                    for key in starfit_keys:
                        if key in row and row[key]:
                            try:
                                val = float(row[key])
                                # Skip sentinel values
                                if val not in (-99999, float("inf"), float("-inf")):
                                    params[key] = val
                            except ValueError:
                                pass
                    if params:
                        self.reservoir_starfit_params[name] = params
        except Exception as e:
            log.warning("Failed to read istarf_conus.csv: %s", e)

    # ── Rating Curves ────────────────────────────────────────────────

    def _build_rating_curves(self) -> None:
        """Parse USGS NWIS rating curve headers for flood monitoring gages."""
        rating_dir = PYWRDRB_ROOT / "data" / "rating_curves"
        self.rating_curve_metadata: dict[str, dict] = {}

        if not rating_dir.exists():
            return

        for txt_file in sorted(rating_dir.glob("*.txt")):
            site_no = txt_file.stem
            metadata: dict = {"site_number": site_no, "file": f"data/rating_curves/{txt_file.name}"}

            try:
                with open(txt_file, encoding="utf-8") as f:
                    stages = []
                    discharges = []
                    for line in f:
                        line = line.strip()
                        if line.startswith("#"):
                            # Parse header comments
                            if "STATION NAME=" in line:
                                metadata["station_name"] = line.split("STATION NAME=")[1].strip().strip('"')
                            elif "RATING EXPANSION=" in line:
                                metadata["expansion"] = line.split("RATING EXPANSION=")[1].strip().strip('"')
                            elif 'RATING_INDEP' in line and 'PARAMETER=' in line:
                                metadata["stage_units"] = line.split('PARAMETER=')[1].strip().strip('"')
                            elif 'RATING_DEP' in line and 'PARAMETER=' in line:
                                metadata["discharge_units"] = line.split('PARAMETER=')[1].strip().strip('"')
                            continue
                        # Data rows: INDEP  SHIFT  DEP  STOR
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            try:
                                stages.append(float(parts[0]))
                                discharges.append(float(parts[2]))
                            except ValueError:
                                continue

                    if stages:
                        metadata["stage_range"] = {"min": min(stages), "max": max(stages)}
                        metadata["discharge_range"] = {"min": min(discharges), "max": max(discharges)}
                        metadata["num_points"] = len(stages)

                self.rating_curve_metadata[site_no] = metadata
            except Exception as e:
                log.warning("Failed to parse rating curve %s: %s", txt_file.name, e)

    # ── Package Structure ─────────────────────────────────────────────

    def _build_package_structure(self) -> None:
        self.package_structure: dict[str, str | None] = get_package_structure()
