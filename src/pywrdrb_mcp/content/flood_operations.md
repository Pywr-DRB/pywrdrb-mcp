# Flood Monitoring and Operations in Pywr-DRB

## Overview

Pywr-DRB includes optional flood monitoring and flood-responsive reservoir operations
for NYC reservoir tailwater locations. This feature implements provisions from the 2017
Flexible Flow Management Program (FFMP) Appendix A, Section G.4.e-g and is disabled by
default to preserve backward compatibility.

Enable with:

```python
from pywrdrb.model_builder import Options
options = Options(enable_nyc_flood_operations=True)
```

---

## Primary Flood Monitoring Nodes

Three USGS gage locations are added to the model network when flood operations are enabled.
Each sits immediately downstream of an NYC reservoir system. Use `get_node_list()` or
`get_node_topology("01426500", include_flood_topology=True)` for current network details.

| USGS Site | Location | Downstream of |
|-----------|----------|---------------|
| 01426500 | Hale Eddy, NY | Cannonsville (West Branch Delaware) |
| 01421000 | Fishs Eddy, NY | Pepacton (East Branch Delaware) |
| 01436690 | Bridgeville, NY | Neversink Reservoir |

Network routing when enabled:

```
West Branch:  01425000 (Stilesville) → 01426500 (Hale Eddy)  → delLordville
East Branch:  01417000 (Harvard)     → 01421000 (Fishs Eddy) → delLordville
Neversink:    01436000 (Release)     → 01436690 (Bridgeville) → delMontague
```

---

## Flood Stage Categories and Thresholds

Stage thresholds are in feet above gage datum, sourced from NWS AHPS and FFMP Appendix A.

| Category | Level | Description |
|----------|-------|-------------|
| Normal   | 0 | Below action stage; no flood operations triggered |
| Action   | 1 | Flood operations may activate; Zone L1 releases suppressed |
| Minor    | 2 | NWS flood stage reached |
| Moderate | 3 | NWS moderate flood stage |
| Major    | 4 | NWS major flood stage |

Threshold values per location are defined in `pywrdrb/flood_thresholds.py`. Use
`search_codebase("flood_stage_thresholds")` or `get_file_contents("flood_thresholds.py")`
to retrieve current threshold values for all locations.

---

## Stage Computation from Discharge

Stage at each monitoring location is computed from simulated discharge using USGS rating
curves via the `StageFromDischargeParameter` class (`pywrdrb.parameters.flood_stage`).

- Rating curves contain 2,187-2,369 data points per site (6,832 total), covering flows
  from approximately 0.5 to 96,800 cfs. Use `get_data_file_list("rating_curves")` to
  see available rating curve files.
- Interpolation uses log-log transformation for accuracy across the full flow range.
- Discharge values outside the rating curve bounds use endpoint extrapolation; a warning
  is issued once per site to avoid excessive log output in ensemble runs.
- Rating curves are loaded once at class level and cached for efficiency.

```python
# StageFromDischargeParameter usage (JSON model definition)
{
    "type": "StageFromDischargeParameter",
    "node": "01426500",
    "site_no": "01426500"   # optional, defaults to node name
}
```

---

## FloodLevelIndicator: Integer Encoding

`FloodLevelIndicator` (`pywrdrb.parameters.flood_stage`) wraps a stage parameter and
returns an integer category (0-4) each timestep for use in operational rules and output.

```
0 = Normal       (stage < action threshold)
1 = Action stage (action <= stage < minor)
2 = Minor flood  (minor  <= stage < moderate)
3 = Moderate     (moderate <= stage < major)
4 = Major        (stage >= major threshold)
```

Thresholds are read from `pywrdrb.flood_thresholds.flood_stage_thresholds` using the
location key (e.g., `"01426500"` or `"delMontague"`).

---

## Flood-Responsive Operations

When `enable_nyc_flood_operations=True`, the `NYCFloodRelease` parameter gains two
additional attributes: `downstream_stage_parameter` and `flood_operations_enabled`.
The operational effect is:

- Zone L1 supplemental releases from NYC reservoirs are suppressed when the downstream
  monitoring gage exceeds action stage (level >= 1).
- This prevents reservoir releases from compounding flood conditions in the tailwater.
- All other FFMP release rules remain active; only the L1 component is gated.

---

## Additional Monitoring: delMontague and delTrenton

Delaware River mainstem flood thresholds are defined for Montague, NJ (USGS 01438500)
and Trenton, NJ (USGS 01463500) in `flood_stage_thresholds`. These are used for
downstream situational awareness. Full rating-curve-based stage computation for these
sites is planned for a future phase; at present they appear in the threshold table and
can be referenced by `FloodLevelIndicator` if stage data are supplied externally.

---

## Results Output

| Results set | Content |
|-------------|---------|
| `flood_stage` | Stage height (ft) at each monitoring location per timestep |
| `flood_level` | Integer flood category (0-4) at each monitoring location |

```python
data = pywrdrb.Data()
data.load_output(output_filenames=['model_output.hdf5'],
                 results_sets=['flood_stage', 'flood_level'])
stage_df = data.flood_stage["model_output"][0]
level_df = data.flood_level["model_output"][0]
```

---

## References

- 2017 FFMP Appendix A, Section G.4.e-g
- NWS Advanced Hydrologic Prediction Service (AHPS): flood stage thresholds
- USGS NWIS: rating curve data (`waterdata.usgs.gov/nwis`)
