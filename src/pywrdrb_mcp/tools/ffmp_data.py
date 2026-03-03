"""Tools for querying FFMP operational constants, profiles, and lower basin policy data."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import extract_module_level_dict, extract_module_level_list

_OPS_DIR = PYWRDRB_ROOT / "data" / "operational_constants"


def _read_csv_as_dicts(filepath: Path, max_rows: int = 0) -> list[dict]:
    """Read a CSV into a list of dicts (one per row)."""
    rows = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break
            rows.append(dict(row))
    return rows


@mcp.tool()
def get_ffmp_data(
    category: str = "all",
) -> str:
    """Get FFMP operational constants, profiles, and lower basin policy data.

    Returns NYC operations configuration data used by the FFMP parameter classes.

    Args:
        category: What to return. Options:
            - "all" — Summary of all categories (default)
            - "constants" — MRF baselines, delivery limits, flood releases from constants.csv
            - "storage_zones" — Daily storage zone threshold profiles (drought level boundaries)
            - "mrf_daily" — Daily MRF release factor profiles per reservoir and drought level
            - "mrf_monthly" — Monthly MRF factors for Montague/Trenton by drought level
            - "lower_basin" — Lower basin reservoir policy data (DRBC rules)
    """
    if category == "constants":
        return _get_constants()
    elif category == "storage_zones":
        return _get_storage_zones()
    elif category == "mrf_daily":
        return _get_mrf_daily()
    elif category == "mrf_monthly":
        return _get_mrf_monthly()
    elif category == "lower_basin":
        return _get_lower_basin_policy()
    else:
        return _get_summary()


def _get_summary() -> str:
    """Overview of all available FFMP data categories."""
    lines = [
        "# FFMP Operational Data Summary\n",
        "## NYC Operations (from data/operational_constants/)\n",
        "| Category | Description | Tool call |",
        "|---|---|---|",
        '| `constants` | MRF baselines, delivery limits, flood max releases, drought-level delivery factors (30 values) | `get_ffmp_data("constants")` |',
        '| `storage_zones` | Daily storage zone threshold profiles — 6 drought levels x 366 days (fraction of capacity) | `get_ffmp_data("storage_zones")` |',
        '| `mrf_daily` | Daily MRF release factors — 7 levels x 3 reservoirs x 366 days | `get_ffmp_data("mrf_daily")` |',
        '| `mrf_monthly` | Monthly MRF factors for Montague & Trenton — 7 levels x 2 targets x 12 months | `get_ffmp_data("mrf_monthly")` |',
        '| `lower_basin` | DRBC lower basin reservoir policies — usable storage, max discharge, conservation releases, drought priorities | `get_ffmp_data("lower_basin")` |',
        "",
        "## Key FFMP concepts:",
        "- **Drought levels**: L1a (normal) → L5 (emergency). Storage zone thresholds define transitions.",
        "- **MRF baselines**: Montague=1131 MGD, Trenton=1939 MGD. Reduced by factors during drought.",
        "- **NYC delivery**: 800 MGD baseline, unconstrained at L1a-L2, reduced at L3 (85%), L4 (70%), L5 (65%).",
        "- **NJ delivery**: 100 MGD monthly avg baseline, reduced at L4 (90%) and L5 (80%).",
        "- **Flood max releases**: Cannonsville=4200 CFS, Pepacton=2400 CFS, Neversink=3400 CFS.",
    ]
    return "\n".join(lines)


def _get_constants() -> str:
    """Read constants.csv and return structured data."""
    csv_path = _OPS_DIR / "constants.csv"
    if not csv_path.exists():
        return "Error: constants.csv not found."

    rows = _read_csv_as_dicts(csv_path)
    constants = {r["parameter"]: {"value": r["value"], "units": r.get("units", "")} for r in rows}

    # Group by category for readability
    groups = {
        "mrf_baselines": {},
        "delivery_nyc": {},
        "delivery_nj": {},
        "flood_releases": {},
        "other": {},
    }

    for name, data in constants.items():
        if "mrf_baseline" in name:
            groups["mrf_baselines"][name] = data
        elif "nyc" in name or "delivery_nyc" in name:
            groups["delivery_nyc"][name] = data
        elif "nj" in name or "delivery_nj" in name:
            groups["delivery_nj"][name] = data
        elif "flood" in name:
            groups["flood_releases"][name] = data
        else:
            groups["other"][name] = data

    return json.dumps(groups, indent=2)


def _get_storage_zones() -> str:
    """Read storage zone profiles (daily thresholds for each drought level)."""
    csv_path = _OPS_DIR / "ffmp_reservoir_operation_daily_profiles.csv"
    if not csv_path.exists():
        return "Error: daily profiles CSV not found."

    zone_levels = ["level1b", "level1c", "level2", "level3", "level4", "level5"]
    rows = _read_csv_as_dicts(csv_path)

    zones = {}
    for row in rows:
        profile = row.get("profile", "")
        if profile in zone_levels:
            # Sample at monthly intervals for conciseness
            monthly_sample = {}
            for key in ["1-Jan", "1-Feb", "1-Mar", "1-Apr", "1-May", "1-Jun",
                         "1-Jul", "1-Aug", "1-Sep", "1-Oct", "1-Nov", "1-Dec"]:
                if key in row:
                    monthly_sample[key] = float(row[key])
            zones[profile] = monthly_sample

    lines = [
        "# Storage Zone Daily Profiles (sampled at month starts)\n",
        "Values are storage fraction (0-1) of total capacity.",
        "Level1a is implicitly 'above level1b'.\n",
    ]
    lines.append(json.dumps(zones, indent=2))
    lines.append("\nUse `get_file_contents('data/operational_constants/ffmp_reservoir_operation_daily_profiles.csv')` for full 366-day profiles.")
    return "\n".join(lines)


def _get_mrf_daily() -> str:
    """Read daily MRF factor profiles (per reservoir × drought level)."""
    csv_path = _OPS_DIR / "ffmp_reservoir_operation_daily_profiles.csv"
    if not csv_path.exists():
        return "Error: daily profiles CSV not found."

    rows = _read_csv_as_dicts(csv_path)

    mrf_profiles = {}
    for row in rows:
        profile = row.get("profile", "")
        if "_factor_mrf_" in profile:
            # Sample at monthly intervals
            monthly_sample = {}
            for key in ["1-Jan", "1-Feb", "1-Mar", "1-Apr", "1-May", "1-Jun",
                         "1-Jul", "1-Aug", "1-Sep", "1-Oct", "1-Nov", "1-Dec"]:
                if key in row:
                    monthly_sample[key] = float(row[key])
            mrf_profiles[profile] = monthly_sample

    lines = [
        "# Daily MRF Release Factor Profiles (sampled at month starts)\n",
        "Pattern: `{level}_factor_mrf_{reservoir}`",
        "Values are multipliers applied to the reservoir's MRF baseline.\n",
        json.dumps(mrf_profiles, indent=2),
        "\nUse `get_file_contents('data/operational_constants/ffmp_reservoir_operation_daily_profiles.csv')` for full daily data.",
    ]
    return "\n".join(lines)


def _get_mrf_monthly() -> str:
    """Read monthly MRF factor profiles for Montague and Trenton."""
    csv_path = _OPS_DIR / "ffmp_reservoir_operation_monthly_profiles.csv"
    if not csv_path.exists():
        return "Error: monthly profiles CSV not found."

    rows = _read_csv_as_dicts(csv_path)
    profiles = {}
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for row in rows:
        profile = row.get("profile", "")
        if "_factor_mrf_" in profile:
            profiles[profile] = {m: float(row[m]) for m in months if m in row}

    return json.dumps({
        "description": "Monthly MRF factors for Montague and Trenton by drought level",
        "profiles": profiles,
    }, indent=2)


def _get_lower_basin_policy() -> str:
    """Extract lower basin reservoir policy data from lower_basin_ffmp.py."""
    lb_file = PYWRDRB_ROOT / "parameters" / "lower_basin_ffmp.py"

    result: dict = {}

    # Pure literal dicts
    for name in [
        "drbc_max_usable_storages",
        "reservoirs_used_during_normal_conditions",
        "reservoirs_used_during_drought_conditions",
    ]:
        val = extract_module_level_dict(lb_file, name)
        if val is None:
            val = extract_module_level_list(lb_file, name)
        if val is not None:
            result[name] = val

    # priority_use_during_drought is a list of lists
    val = extract_module_level_list(lb_file, "priority_use_during_drought")
    if val is not None:
        result["priority_use_during_drought"] = {
            "description": "Staging priorities [priority_level, reservoir, storage_pct_lower_bound]",
            "data": val,
        }

    # Computed dicts (use cfs_to_mgd arithmetic) — provide hardcoded values
    cfs_to_mgd = 0.64631689
    result["conservation_releases_mgd"] = {
        "description": "Minimum releases (MGD) from DRBC Water Code Table 4",
        "blueMarsh": round(50 * cfs_to_mgd, 1),
        "beltzvilleCombined": round(35 * cfs_to_mgd, 1),
        "nockamixon": round(11 * cfs_to_mgd, 1),
        "fewalter": round(50 * cfs_to_mgd, 1),
    }
    result["max_discharges_mgd"] = {
        "description": "Maximum discharge per reservoir (MGD)",
        "blueMarsh": round(1500 * cfs_to_mgd, 1),
        "beltzvilleCombined": round(1500 * cfs_to_mgd, 1),
        "nockamixon": round(1000 * cfs_to_mgd, 1),
        "fewalter": round(2000 * cfs_to_mgd, 1),
    }
    result["lag_days_from_Trenton"] = {
        "blueMarsh": 2,
        "beltzvilleCombined": 2,
        "nockamixon": 1,
        "fewalter": 2,
    }

    return json.dumps(result, indent=2)
