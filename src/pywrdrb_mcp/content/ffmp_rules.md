# FFMP Operational Rules in Pywr-DRB

## What is FFMP?

The **Flexible Flow Management Program (FFMP)** is the 2017 Delaware River Basin Commission framework governing how New York City's three upstream reservoirs — **Cannonsville**, **Pepacton**, and **Neversink** — release water to meet downstream flow targets, supply NYC and NJ, and manage floods and droughts. The FFMP replaced earlier static rules with adaptive, storage-based operating curves.

Reference: [FFMP 2018 Appendix A](https://webapps.usgs.gov/odrm/ffmp/Appendix_A_FFMP%2020180716%20Final.pdf)

Pywr-DRB implements FFMP rules via a set of custom Pywr `Parameter` subclasses in `src/pywrdrb/parameters/ffmp.py` and `src/pywrdrb/parameters/banks.py`, configured through `NYCOperationsConfig` and wired into the model by `ModelBuilder`.

---

## Drought Levels

The FFMP defines seven operational zones based on storage relative to seasonal rule curves:

| Level | Description         |
|-------|---------------------|
| 1a    | Flood / spill zone  |
| 1b    | Spill mitigation    |
| 1c    | Upper normal        |
| 2     | Normal operations   |
| 3     | Watch               |
| 4     | Warning             |
| 5     | Emergency (drought) |

NYC delivery drought factors per level are available via `get_ffmp_data("constants")`.

Two drought level indices are tracked at every timestep:

- **Aggregate NYC level** (`drought_level_agg_nyc`): based on combined storage across all three reservoirs. Drives delivery constraints and the MRF release factor formula.
- **Individual reservoir level** (`drought_level_{reservoir}`): based on each reservoir's own storage fraction. Drives flood control releases and per-reservoir release factors in Levels 1a–1c.

Both are implemented as Pywr `ControlCurveIndex` parameters using six seasonal threshold profiles (level1b through level5), each containing 366 daily fractional-storage values loaded from `ffmp_reservoir_operation_daily_profiles.csv`.

---

## Storage Zones and Rule Curves

Each threshold level is expressed as a **fraction of usable capacity**, varying seasonally. For example:

- `level2` (top of normal operations zone): ranges ~0.75–1.0 across the year
- `level5` (bottom of drought emergency zone): a lower seasonal floor

The six boundary profiles stored in `NYCOperationsConfig.storage_zones_df` are:

```
level1b, level1c, level2, level3, level4, level5
```

Level 1a is implicitly above level1b (full pool / spill). The drought level integer index returned by `ControlCurveIndex` maps as: 0 = above 1b (Level 1a), 1 = 1b–1c, 2 = 1c–2, 3 = 2–3, 4 = 3–4, 5 = 4–5, 6 = below 5 (Level 5).

---

## Minimum Required Flow (MRF) Targets

### Reservoir-Specific Conservation Releases

Each reservoir has a **baseline MRF** (MGD) scaled by a seasonal drought-level factor.
Use the `get_ffmp_data("constants")` tool for current baseline values, or
`get_ffmp_data("mrf_daily")` for the full daily factor profiles.

Daily MRF factors (`level{N}_factor_mrf_{reservoir}`) are indexed by drought level and day of year (366 values).

**Final reservoir MRF target:**
```
mrf_target_individual_{reservoir} = mrf_baseline × combined_release_factor
```

The **combined release factor** is computed by `NYCCombinedReleaseFactor` using a weighted blend of the aggregate and individual storage drought factors:

```python
factor = min(max(D_agg - 2, 0), 1) * factor_agg
       + min(max(3 - D_agg, 0), 1) * factor_indiv
```

When the system is in Level 2 or deeper drought (`D_agg >= 3`), the aggregate factor fully applies. When in Level 1 (flood zone, `D_agg < 2`), the individual reservoir factor fully applies. Between Levels 1 and 2, the two factors blend linearly. This allows flood control to be driven by each reservoir's own storage while drought operations use system-wide storage.

An optional **flood curtailment mode** caps the release factor at the L2 daily profile when downstream stage at a reference gage exceeds the FFMP action threshold. Use `get_file_contents("flood_thresholds.py")` for current threshold values per location.

### Downstream Flow Targets

The FFMP also sets minimum flow targets at two downstream gages (Montague and Trenton).
Use `get_ffmp_data("constants")` for baseline values, and `get_ffmp_data("mrf_monthly")`
for the monthly multiplier factors that scale these baselines by drought level and calendar month.

---

## NYC and NJ Delivery Constraints

### NYC Delivery

- **Running average constraint** (`FfmpNycRunningAvgParameter`): tracks cumulative delivery against a moving-average budget. The budget updates daily as:
  ```
  max_delivery_t = max_delivery_{t-1} - flow_{t-1} + max_avg_delivery
  ```
  The budget resets annually (see `delivery_reset_month`/`delivery_reset_day` in constants). Values cannot go negative.

### NJ Delivery

- **Running average constraint** (`FfmpNjRunningAvgParameter`): similar to NYC but resets on the **first of each month** under normal conditions (factor = 1.0) and resets immediately whenever the drought factor changes between timesteps. Also capped by the daily limit.

Use `get_ffmp_data("constants")` for current NYC/NJ delivery baselines, limits, and drought factors.

---

## Release Types

### Conservation Releases
Standard mandatory minimum releases from each reservoir based on `mrf_target_individual_{reservoir}` (baseline × combined factor). These occur at all drought levels.

### Flood Control Releases (`NYCFloodRelease`)
Triggered when a reservoir's individual storage is in Zone L1 **and** the combined NYC storage is also in Zone L1. The target is to return storage to the 1b/1c boundary over **7 days**:

```python
excess_volume = current_volume - level1c_volume + weekly_rolling_mean_inflow * 7
flood_release = max(min(excess_volume / 7 - mrf_target, max_release - mrf_target), 0)
```

Maximum flood releases are defined in FFMP Table 5.
Use `get_ffmp_data("constants")` for current max flood release values per reservoir.

When downstream stage exceeds the action threshold during Zone L1, the excess flood release is suppressed (returns 0) and the MRF factor is separately capped at the L2 level by `NYCCombinedReleaseFactor`.

### Directed Releases for Downstream MRF
Additional releases beyond conservation flows needed to meet Montague and Trenton targets, distributed across reservoirs via the volume-balancing algorithm described below.

---

## Volume Balancing Across NYC Reservoirs

Releases to meet downstream MRF targets are distributed across Cannonsville, Pepacton, and Neversink using a **4-step staggered process** that accounts for travel-time lags to the downstream gages:

| Step | Reservoirs contributing     | Lag to Montague | Lag to Trenton |
|------|-----------------------------|-----------------|----------------|
| 1    | Cannonsville, Pepacton      | 2 days          | 4 days         |
| 2    | Neversink                   | 1 day           | 3 days         |
| 3–4  | Lower-basin reservoirs      | varies          | varies         |

**`TotalReleaseNeededForDownstreamMRF`** computes the total release gap at each step after accounting for predicted natural flows and prior-step contributions.

**`VolBalanceNYCDownstreamMRF_step1`** and **`_step2`** then distribute each step's release requirement proportionally:

1. Calculate each reservoir's proportional target based on its relative current storage fraction.
2. Enforce non-negativity and per-reservoir max release constraints.
3. Iteratively adjust allocations if the sum does not match the total requirement.

**`VolBalanceNYCDemand`** distributes the total NYC water supply delivery across the three reservoirs, targeting proportional storage equity while respecting individual diversion limits and MRF obligations.

---

## IERQ / Bank Storage

The **Interim Excess Release Quantity (IERQ)** is a pool of pre-allocated water volume that can supplement Trenton equivalent flow targets beyond standard MRF obligations. Per FFMP Section 3.c, the total IERQ budget is approximately 10,000 MG per year, split across four banks (Trenton, thermal mitigation, rapid flow change, NJ diversion amelioration).

Use `get_parameter_class_info("IERQRelease_step1")` to see current bank volume allocations.

Currently, only the **Trenton bank** is implemented (`IERQRelease_step1` in `banks.py`). The bank:

- Resets to its full allocation on **May 31** each year (same as NYC delivery reset).
- Each day, the allowable release is `min(bank_remaining, trenton_release_needed)`.
- The released volume is subtracted from `bank_remaining` after each timestep.
- When NYC is in drought, the bank should be set to 0 (not yet automated).

The remaining three banks (thermal mitigation, rapid flow change, NJ diversion amelioration) are stubbed out but not yet implemented.

---

## NYCOperationsConfig: Customizing FFMP Rules

`NYCOperationsConfig` (in `src/pywrdrb/parameters/nyc_operations_config.py`) is a configuration container that holds all FFMP parameters and can be passed to `ModelBuilder` to override defaults.

Use `get_parameter_class_info("NYCOperationsConfig")` for the full API, including all
method signatures and parameter types. Key methods:

- `from_defaults(data_dir=None)` — Load default configuration from package CSVs
- `update_storage_zones(...)` — Modify seasonal storage zone thresholds
- `update_mrf_factors(...)` — Modify MRF release factors (daily or monthly)
- `update_delivery_constraints(...)` — Modify NYC/NJ delivery limits and drought factors
- `update_flood_limits(...)` — Modify maximum flood release caps
- `update_mrf_baselines(...)` — Modify minimum required flow baselines
- `to_csv(output_dir)` — Export configuration to CSV files
- `copy()` — Create a deep copy

If `nyc_operations_config=None` (the default), `ModelBuilder` calls `NYCOperationsConfig.from_defaults()` internally, preserving backward compatibility.

Validation (`_validate()`) checks for 366 daily columns, 12 monthly columns, required constant keys, and all 7 drought-level delivery factors. Semantic consistency (e.g., `level2 > level3`) is **not** enforced automatically.

---

## Parameter Class Summary

All custom Pywr parameters in `ffmp.py` and `banks.py` must be registered before use (`ClassName.register()`):

| Class                               | Role                                                      |
|-------------------------------------|-----------------------------------------------------------|
| `FfmpNycRunningAvgParameter`        | NYC delivery running-average budget; resets May 31        |
| `FfmpNjRunningAvgParameter`         | NJ delivery running-average budget; monthly/factor resets |
| `NYCCombinedReleaseFactor`          | Weighted aggregate/individual MRF release factor          |
| `NYCFloodRelease`                   | Flood-zone excess release over 7-day window               |
| `TotalReleaseNeededForDownstreamMRF`| 4-step lagged MRF gap calculation at Montague/Trenton     |
| `VolBalanceNYCDownstreamMRF_step1`  | Cannonsville/Pepacton share of step-1 MRF release         |
| `VolBalanceNYCDownstreamMRF_step2`  | Neversink share of step-2 MRF release                     |
| `VolBalanceNYCDemand`               | NYC delivery distribution across 3 reservoirs             |
| `IERQRelease_step1`                 | Trenton IERQ bank drawdown and annual reset               |

---

## Data Sources

All default parameters are loaded from `src/pywrdrb/data/operational_constants/`.
Use the `get_ffmp_data` tool to query any of these data sources:

- `get_ffmp_data("constants")` — Scalar parameters (MRF baselines, delivery limits, drought factors, flood caps, reset dates)
- `get_ffmp_data("storage_zones")` — Daily storage zone threshold profiles (366 day-of-year values)
- `get_ffmp_data("mrf_daily")` — Daily MRF release factor profiles per reservoir × drought level
- `get_ffmp_data("mrf_monthly")` — Monthly downstream flow factors for Montague and Trenton

---

## Known Limitations

- **May 31 reset date**: The `delivery_reset_month`/`delivery_reset_day` constants in `constants.csv` are not yet read by `FfmpNycRunningAvgParameter`; the date is currently hardcoded in `after()`.
- **7-day flood window**: Hardcoded in `NYCFloodRelease`.
- **4-step lag structure**: Travel times to Montague/Trenton are hardcoded in the balancing methods.
- **IERQ banks**: Only the Trenton bank (6,090 MG) is active; thermal mitigation, rapid flow change, and NJ diversion amelioration banks are stubbed but not implemented.
- **Drought-zero IERQ**: The rule that sets IERQ to 0 during drought is noted but not yet automated.
