# FFMP Operational Rules in Pywr-DRB

## What is FFMP?

The **Flexible Flow Management Program (FFMP)** is the 2017 Delaware River Basin Commission framework governing how New York City's three upstream reservoirs — **Cannonsville**, **Pepacton**, and **Neversink** — release water to meet downstream flow targets, supply NYC and NJ, and manage floods and droughts. The FFMP replaced earlier static rules with adaptive, storage-based operating curves.

Reference: [FFMP 2018 Appendix A](https://webapps.usgs.gov/odrm/ffmp/Appendix_A_FFMP%2020180716%20Final.pdf)

Pywr-DRB implements FFMP rules via a set of custom Pywr `Parameter` subclasses in `src/pywrdrb/parameters/ffmp.py` and `src/pywrdrb/parameters/banks.py`, configured through `NYCOperationsConfig` and wired into the model by `ModelBuilder`.

---

## Drought Levels

The FFMP defines seven operational zones based on storage relative to seasonal rule curves:

| Level | Description         | Drought factor (NYC delivery) |
|-------|---------------------|-------------------------------|
| 1a    | Flood / spill zone  | 1e6 (unconstrained)           |
| 1b    | Spill mitigation    | 1e6 (unconstrained)           |
| 1c    | Upper normal        | 1e6 (unconstrained)           |
| 2     | Normal operations   | 1e6 (unconstrained)           |
| 3     | Watch               | 0.85                          |
| 4     | Warning             | 0.70                          |
| 5     | Emergency (drought) | 0.65                          |

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

Each reservoir has a **baseline MRF** (MGD) scaled by a seasonal drought-level factor:

| Reservoir     | Baseline MRF (MGD) |
|---------------|--------------------|
| Cannonsville  | 122.8              |
| Pepacton      | 64.63              |
| Neversink     | 48.47              |

Daily MRF factors (`level{N}_factor_mrf_{reservoir}`) are indexed by drought level and day of year (366 values). Example: `level2_factor_mrf_cannonsville` ranges 1.5–7.5 across the year.

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

An optional **flood curtailment mode** caps the release factor at the L2 daily profile when downstream stage at a reference gage exceeds FFMP action thresholds (Hale Eddy > 9 ft for Cannonsville, Fishs Eddy > 11 ft for Pepacton, Bridgeville > 12 ft for Neversink).

### Downstream Flow Targets

The FFMP also sets minimum flow targets at two downstream gages:

| Gage                     | Baseline (MGD) |
|--------------------------|----------------|
| Delaware at Montague, NJ | 1131.05        |
| Delaware at Trenton, NJ  | 1938.95        |

Monthly multiplier factors (`level{N}_factor_mrf_delMontague` / `delTrenton`) scale these baselines by drought level across 12 calendar months. For example, Montague Level 5 ranges 0.77–0.91 seasonally; Trenton Levels 3–5 all use 0.9 year-round.

---

## NYC and NJ Delivery Constraints

### NYC Delivery

- **Baseline limit:** 800 MGD (`max_flow_baseline_delivery_nyc`)
- **Drought factor** applied per aggregate drought level (see table above)
- **Running average constraint** (`FfmpNycRunningAvgParameter`): tracks cumulative delivery against a moving-average budget. The budget updates daily as:
  ```
  max_delivery_t = max_delivery_{t-1} - flow_{t-1} + max_avg_delivery
  ```
  On **May 31** each year the budget resets to the full baseline. Values cannot go negative.

### NJ Delivery

- **Daily baseline:** 120 MGD; **monthly average baseline:** 100 MGD
- **Drought factors** by level: `[1, 1, 1, 1, 1, 0.9, 0.8]` (Levels 1a–5)
- **Running average constraint** (`FfmpNjRunningAvgParameter`): similar to NYC but resets on the **first of each month** under normal conditions (factor = 1.0) and resets immediately whenever the drought factor changes between timesteps. Also capped by the daily limit.

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

Maximum flood releases (from FFMP Table 5, in CFS):

| Reservoir    | Max Flood Release (CFS) |
|--------------|------------------------|
| Cannonsville | 4200                   |
| Pepacton     | 2400                   |
| Neversink    | 3400                   |

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

The **Interim Excess Release Quantity (IERQ)** is a pool of pre-allocated water volume that can supplement Trenton equivalent flow targets beyond standard MRF obligations. Per FFMP Section 3.c, the total IERQ budget is 10,000 MG per year, split across four banks:

| Bank                     | Annual Volume |
|--------------------------|--------------|
| Trenton equivalent flow  | 6,090 MG     |
| Thermal mitigation       | 1,620 MG     |
| Rapid flow change        | 650 MG       |
| NJ diversion amelioration| 1,650 MG     |

Currently, only the **Trenton bank** is implemented (`IERQRelease_step1` in `banks.py`). The bank:

- Resets to its full 6,090 MG allocation on **June 1** each year.
- Each day, the allowable release is `min(bank_remaining, trenton_release_needed)`.
- The released volume is subtracted from `bank_remaining` after each timestep.
- When NYC is in drought, the bank should be set to 0 (not yet automated).

The remaining three banks (thermal mitigation, rapid flow change, NJ diversion amelioration) are stubbed out but not yet implemented.

---

## NYCOperationsConfig: Customizing FFMP Rules

`NYCOperationsConfig` (in `src/pywrdrb/parameters/nyc_operations_config.py`) is a configuration container that holds all FFMP parameters and can be passed to `ModelBuilder` to override defaults.

### Key attributes

| Attribute              | Content                                                  |
|------------------------|----------------------------------------------------------|
| `storage_zones_df`     | DataFrame of storage zone thresholds (366 cols × 6 rows)|
| `mrf_factors_daily_df` | Daily MRF release factor profiles (366 cols)             |
| `mrf_factors_monthly_df`| Monthly downstream flow factor profiles (12 cols)       |
| `constants`            | Dict of scalar parameters (baselines, limits, factors)   |

### Loading defaults

```python
from pywrdrb.parameters.nyc_operations_config import NYCOperationsConfig

config = NYCOperationsConfig.from_defaults()          # from package CSVs
config = NYCOperationsConfig.from_defaults(data_dir='path/to/csvs')  # custom CSVs
```

### Updating parameters

```python
# Delivery limits
config.update_delivery_constraints(max_nyc_delivery=850, max_nj_daily=130)

# MRF baselines (MGD)
config.update_mrf_baselines(cannonsville=135.0, montague=1200.0)

# Seasonal storage zone (366 values, fractions of capacity)
config.update_storage_zones(level='level2', daily_values=new_array)

# Daily MRF factor for a specific reservoir × drought level
config.update_mrf_factors(reservoir='cannonsville', level='level2', daily_factors=arr)

# Flood release caps (CFS)
config.update_flood_limits(max_release_cannonsville=5000)
```

### Passing to ModelBuilder

```python
from pywrdrb.model_builder import ModelBuilder

model = ModelBuilder(
    start_date="2000-01-01",
    end_date="2010-12-31",
    inflow_type="nhmv10_withObsScaled",
    nyc_operations_config=config
)
```

If `nyc_operations_config=None` (the default), `ModelBuilder` calls `NYCOperationsConfig.from_defaults()` internally, preserving backward compatibility.

### Validation and export

- `_validate()` is called after every update: checks for 366 daily columns, 12 monthly columns, required constant keys, and all 7 drought-level delivery factors. Raises errors for structural problems; warns for missing optional keys.
- Semantic consistency (e.g., `level2 > level3`) is **not** enforced automatically.
- `config.copy()` returns a deep copy; `config.to_csv(dir)` exports all DataFrames and constants to the standard CSV filenames.

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

All default parameters are loaded from `src/pywrdrb/data/operational_constants/`:

- **`constants.csv`**: ~31 scalar parameters (MRF baselines, delivery limits, drought factors, flood caps, reset dates).
- **`ffmp_reservoir_operation_daily_profiles.csv`**: ~32 profiles × 366 day-of-year columns (storage zone thresholds + daily MRF factors).
- **`ffmp_reservoir_operation_monthly_profiles.csv`**: ~16 profiles × 12 month columns (Montague and Trenton downstream flow factors).

---

## Known Limitations

- **May 31 reset date**: The `delivery_reset_month`/`delivery_reset_day` constants in `constants.csv` are not yet read by `FfmpNycRunningAvgParameter`; the date is currently hardcoded in `after()`.
- **7-day flood window**: Hardcoded in `NYCFloodRelease`.
- **4-step lag structure**: Travel times to Montague/Trenton are hardcoded in the balancing methods.
- **IERQ banks**: Only the Trenton bank (6,090 MG) is active; thermal mitigation, rapid flow change, and NJ diversion amelioration banks are stubbed but not implemented.
- **Drought-zero IERQ**: The rule that sets IERQ to 0 during drought is noted but not yet automated.
