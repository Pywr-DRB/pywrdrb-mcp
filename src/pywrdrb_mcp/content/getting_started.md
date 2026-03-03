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

Pass an `Options` instance to `ModelBuilder` to override defaults. Use
`get_model_builder_options()` for the complete list of fields with types,
defaults, and descriptions.

```python
opts = pywrdrb.Options(
    NSCENARIOS=1,
    nyc_nj_demand_source="historical",
    initial_volume_frac=0.8,
    flow_prediction_mode="perfect_foresight",
    enable_nyc_flood_operations=False,
    use_trimmed_model=False,
)

mb = pywrdrb.ModelBuilder(
    inflow_type='nhmv10_withObsScaled',
    start_date="1983-10-01",
    end_date="2016-12-31",
    options=opts,
)
```

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

Use `get_results_set_list()` for the full list of available `results_sets` options.

---

## Common Inflow Types and Date Ranges

Use `get_inflow_type_list()` for the complete and up-to-date list of available inflow
types with their date ranges.

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
