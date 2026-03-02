# Getting Started with Pywr-DRB

## What is Pywr-DRB?

Pywr-DRB is an open-source Python model for water availability and drought risk
assessment in the Delaware River Basin (DRB). It is built on the
[Pywr](https://github.com/pywr/pywr) network-flow simulation framework and
represents the DRB water system including NYC and NJ reservoir operations,
minimum flow requirements, and downstream diversions.
Reference: Hamilton et al. (2024), *Env. Modelling & Software*, https://doi.org/10.1016/j.envsoft.2024.106185

---

## Step 1 — Build a Model

Use `pywrdrb.ModelBuilder` to configure and generate the model. The two required
arguments are `inflow_type` and the simulation date range.

```python
import pywrdrb
import os

wd = r"/path/to/your/working/directory"

mb = pywrdrb.ModelBuilder(
    inflow_type='nwmv21_withObsScaled',   # hybrid NWM v2.1 inflows
    start_date="1983-10-01",
    end_date="1985-12-31",
)

mb.make_model()

model_filename = os.path.join(wd, "my_model.json")
mb.write_model(model_filename)
```

`make_model()` assembles the full Pywr network topology. `write_model()` serialises it to a JSON file that Pywr reads at runtime.

### Key `Options` Fields

Pass an `Options` instance to `ModelBuilder` to override defaults:

```python
opts = pywrdrb.Options(
    NSCENARIOS=1,
    nyc_nj_demand_source="historical",   # "historical" | "custom" | "constant_max"
    initial_volume_frac=0.8,             # starting reservoir storage fraction
    flow_prediction_mode="perfect_foresight",  # or "regression_disagg"
    enable_nyc_flood_operations=False,
    use_trimmed_model=False,             # True cuts runtime ~50-70%
)

mb = pywrdrb.ModelBuilder(
    inflow_type='nhmv10_withObsScaled',
    start_date="1983-10-01",
    end_date="2016-12-31",
    options=opts,
)
```

`flow_prediction_mode`: `"perfect_foresight"` uses actual future observations (default, best for retrospective runs); `"regression_disagg"` uses autoregressive predictions (more operationally realistic).

---

## Step 2 — Load the Model and Attach a Recorder

```python
model = pywrdrb.Model.load(model_filename)

output_filename = os.path.join(wd, "my_model.hdf5")

recorder = pywrdrb.OutputRecorder(
    model=model,
    output_filename=output_filename,
    parameters=[p for p in model.parameters if p.name],
)
```

The `OutputRecorder` captures every named parameter to an HDF5 file during the run.

---

## Step 3 — Run the Simulation

```python
stats = model.run()
```

---

## Step 4 — Load and Examine Results

Use `pywrdrb.Data` to read the HDF5 output back into pandas DataFrames.

```python
data = pywrdrb.Data()

results_sets = ['major_flow', 'res_storage']
data.load_output(output_filenames=[output_filename], results_sets=results_sets)

# DataFrames are stored at data.<results_set>[model_label][scenario_index]
df_major_flow = data.major_flow["my_model"][0]
df_res_storage = data.res_storage["my_model"][0]

# Example columns
print(df_major_flow[['delMontague', 'delTrenton']].head())
print(df_res_storage[['cannonsville', 'pepacton', 'neversink']].head())
```

### Other Data Methods

| Method | Purpose |
|---|---|
| `data.load_observations()` | Load USGS/observed streamflows and storage |
| `data.load_output(...)` | Load pywrdrb simulation HDF5 output |
| `data.export(path)` | Save all loaded data to a single HDF5 file |
| `data.load_from_export(path)` | Reload previously exported data |

Full list of `results_sets` options: https://pywr-drb.github.io/Pywr-DRB/results_set_options.html

---

## Common Inflow Types and Date Ranges

| `inflow_type` | Available Range | Notes |
|---|---|---|
| `nhmv10` | 1983-10-01 – 2016-12-31 | NHM v1.0 streamflow |
| `nhmv10_withObsScaled` | 1983-10-01 – 2016-12-31 | NHM v1.0 with observed scaling |
| `nwmv21` | 1983-10-01 – 2016-12-31 | NWM v2.1 streamflow |
| `nwmv21_withObsScaled` | 1983-10-01 – 2016-12-31 | NWM v2.1 with observed scaling (recommended) |
| `wrfaorc_withObsScaled` | 1979-10-01 – 2021-12-31 | WRF-Hydro AORC-forced, obs-scaled |
| `pub_nhmv10_BC_withObsScaled` | 1945-01-01 – 2023-12-31 | Long-record reconstruction dataset |

`_withObsScaled` variants blend hydrologic model output with observed streamflow
and are generally preferred for retrospective analysis.

---

## Key Source Files

| File | Purpose |
|---|---|
| `src/pywrdrb/model_builder.py` | `ModelBuilder` class and `Options` dataclass |
| `src/pywrdrb/load/data_loader.py` | `Data` class — load outputs and observations |
| `src/pywrdrb/utils/dates.py` | `model_date_ranges` lookup dict |
| `src/pywrdrb/utils/lists.py` | Node name lists (reservoirs, major flows, etc.) |
| `src/pywrdrb/utils/results_sets.py` | Valid `results_sets` string constants |
| `simple_run.py` | End-to-end example: build → run → plot |
