# STARFIT Reservoir Release Policy in Pywr-DRB

## Overview

STARFIT (Storage, Target, and Release Functional form for Inflow Targeting) is an empirical
reservoir operating policy derived by Turner et al. (2021) from observed storage and release
records for large reservoirs across the conterminous United States.

> Turner, S.W.D., Steyaert, J.C., Condon, L., & Voisin, N. (2021). Water storage and release
> policies for all large reservoirs of conterminous United States. *Environmental Modelling &
> Software*, 145, 105201. https://doi.org/10.1016/j.envsoft.2021.105201

In Pywr-DRB the policy is implemented as the `STARFITReservoirRelease` Pywr parameter
(`pywrdrb/parameters/starfit.py`). It is applied to the 14 non-NYC reservoirs listed below and
translates daily storage, inflow, and day-of-year into a constrained release decision.

---

## Reservoirs Using STARFIT

Use `get_reservoir_list()` for the current full list with type classifications. The STARFIT
reservoir list contains 14 reservoirs. Key subsets:

- **DRBC lower-basin reservoirs** (`beltzvilleCombined`, `blueMarsh`, `nockamixon`): R_max
  overridden by DRBC maximum discharge constraints.
- **Modified STARFIT reservoirs** (`blueMarsh`, `beltzvilleCombined`, `fewalter`): Use
  DRBC-adjusted capacity and mean flow values (prefixed `modified_` in `istarf_conus.csv`).
- The three NYC reservoirs (Cannonsville, Pepacton, Neversink) use separate NYC FFMP rules
  and are **not** governed by STARFIT.

Note: `fewalter` uses modified STARFIT parameters but is not in the DRBC lower-basin
reservoir list. `nockamixon` is in the DRBC lower-basin list but does not use modified
STARFIT parameters.

---

## Parameters File: `istarf_conus.csv`

Default STARFIT parameters are loaded from `istarf_conus.csv` (located under
`data/operational_constants/`). Use `get_data_file_list("operational_constants")` to see
available data files.

The file is indexed by reservoir name and contains the following column groups:

| Column group | Variables | Purpose |
|---|---|---|
| Capacity / mean flow | `Adjusted_CAP_MG`, `Adjusted_MEANFLOW_MGD` (or GRanD equivalents) | Storage capacity S_cap and long-term mean inflow I_bar |
| NOR upper bound | `NORhi_mu`, `NORhi_alpha`, `NORhi_beta`, `NORhi_min`, `NORhi_max` | Seasonal harmonic for NOR upper band |
| NOR lower bound | `NORlo_mu`, `NORlo_alpha`, `NORlo_beta`, `NORlo_min`, `NORlo_max` | Seasonal harmonic for NOR lower band |
| Harmonic release | `Release_alpha1`, `Release_alpha2`, `Release_beta1`, `Release_beta2` | Seasonal base-release harmonics |
| Adjustment | `Release_c`, `Release_p1`, `Release_p2` | Intercept and linear coefficients for storage/inflow adjustment |
| Physical bounds | `Release_min`, `Release_max` | Multipliers on I_bar for R_min and R_max |

For reservoirs in `modified_starfit_reservoir_list` the lookup key is prefixed with
`modified_` to use DRBC-adjusted capacity and flow values.

---

## Seasonal NOR Bands (Harmonic Functions)

The Normal Operating Range (NOR) defines the target storage band. Both the upper (NORhi) and
lower (NORlo) bounds vary seasonally via a two-term harmonic in day-of-year `d`:

```
c(d) = pi/365 * (d + offset)

NORhi(d) = clip( NORhi_mu + NORhi_alpha * sin(2c) + NORhi_beta * cos(2c),
                 NORhi_min, NORhi_max )

NORlo(d) = clip( NORlo_mu + NORlo_alpha * sin(2c) + NORlo_beta * cos(2c),
                 NORlo_min, NORlo_max )
```

Both bounds are expressed as fractions of storage capacity (0–1). The `clip` operation
enforces per-reservoir floor and ceiling values. Lookup tables for all 366 days are
pre-computed once per simulation to avoid repeated trigonometric evaluation.

---

## Release Equation

Daily release is computed in three stages.

### 1. Harmonic (seasonal) base release

A four-term harmonic captures the mean seasonal release pattern:

```
seasonal_release(d) = Release_alpha1 * sin(2c)
                    + Release_alpha2 * sin(4c)
                    + Release_beta1  * cos(2c)
                    + Release_beta2  * cos(4c)
```

This term is also pre-computed as a 366-element lookup table.

### 2. Storage and inflow adjustment

Standardized storage and inflow deviations are computed:

```
S_hat = S_t / S_cap                       # fractional storage (0–1)
I_hat = (I_t - I_bar) / I_bar             # standardized inflow anomaly

A_t   = (S_hat - NORlo_t) / NORhi_t      # position within NOR

epsilon = Release_c + Release_p1 * A_t + Release_p2 * I_hat
```

`epsilon` is an additive adjustment that increases releases when storage is high or inflow is
above average and reduces them when conditions are dry.

### 3. Target release (storage-zone logic)

The target release depends on which storage zone the reservoir currently occupies:

| Storage zone | Target release |
|---|---|
| Within NOR: NORlo <= S_hat <= NORhi | `min( I_bar * (seasonal_release + epsilon + 1), R_max )` |
| Above NOR: S_hat > NORhi | `min( (S_cap * (S_hat - NORhi) + I_t * 7) / 7, R_max )` — draws down surplus over one week |
| Below NOR: S_hat < NORlo | `R_min` (conservation floor; or a linearly scaled value if `linear_below_NOR=True`) |

---

## Physical Constraints

After the target release is computed, two additional bounds are enforced:

```
available_water  = I_t + S_t
min_required     = available_water - S_cap   # water that must be released to stay within capacity

release = max( min(target, available_water), min_required )
release = max(0.0, release)
```

This ensures the final release is non-negative, does not exceed the water available, and is
large enough to prevent the reservoir from exceeding capacity.

**R_min and R_max overrides:** For DRBC lower-basin reservoirs (`beltzvilleCombined`,
`blueMarsh`, `nockamixon`) the STARFIT-derived R_min and R_max values are replaced
by DRBC conservation-release and maximum-discharge constants defined in
`pywrdrb/parameters/lower_basin_ffmp.py`. Use `get_ffmp_data("lower_basin")` to see
current conservation release and max discharge values.

---

## Sensitivity Analysis Support

`STARFITReservoirRelease` supports scenario-based parameter sampling for sensitivity or
robustness analysis. When `run_starfit_sensitivity_analysis=True`, the parameter set for each
Pywr scenario is read from a scenario-specific group (`/starfit/scenario_{id}`) inside
`scenarios_data.h5` rather than from `istarf_conus.csv`. The mapping from Pywr scenario index
to sample ID is supplied at construction time via `sensitivity_analysis_scenarios`. Results
from each HDF5 group are cached with `lru_cache` to avoid redundant I/O across reservoirs
that share the same scenario draw.
