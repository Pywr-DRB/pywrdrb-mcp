# Data Loading & Results Interpretation

## The Data Class

`pywrdrb.load.Data` is the unified interface for loading all types of data:

```python
from pywrdrb.load import Data

data = Data(
    results_sets=["major_flow", "res_storage", "res_release"],
    output_filenames=["path/to/drb_output_nhmv10.hdf5"],
    units="MG",  # or "MCM", "CFS"
)
```

## Loading Data

### Simulation output
```python
data.load_output()
flows = data.major_flow["drb_output_nhmv10"][0]  # DataFrame: dates × nodes
```

### Observations (USGS)
```python
data.load_observations()
obs = data.major_flow["obs"]["obs"]  # DataFrame: dates × nodes
```

### Raw hydrologic model data
```python
data.load_hydrologic_model_flow(flowtypes=["nhmv10"])
raw = data.major_flow["nhmv10"]["nhmv10"]
```

## Access Pattern

All loaded data follows the same structure:
```
data.{results_set}["{source_label}"][scenario_id] → pd.DataFrame
```

- **results_set**: What type of data (e.g., `major_flow`, `res_storage`)
- **source_label**: Where the data came from:
  - Output: HDF5 filename stem (e.g., `"drb_output_nhmv10"`)
  - Observations: `"obs"`
  - Hydrologic model: flowtype string (e.g., `"nhmv10"`)
- **scenario_id**: Integer for ensemble members, or string key

## Results Set Categories

### Flow & Storage
| results_set | Description |
|---|---|
| `major_flow` | Streamflow at key river points (MGD) |
| `reservoir_downstream_gage` | Flow at downstream gages below reservoirs |
| `res_storage` | Reservoir storage volume (MG) |
| `res_release` | Reservoir releases (MGD) |
| `inflow` | Inflows at each node (MGD) |

### Operations
| results_set | Description |
|---|---|
| `res_level` | FFMP drought level per reservoir |
| `mrf_target` | MRF targets at Montague/Trenton |
| `downstream_release_target` | Release targets at Montague/Trenton |
| `nyc_release_components` | NYC releases by type |
| `lower_basin_mrf_contributions` | Lower basin MRF contributions |

### Diversions
| results_set | Description |
|---|---|
| `ibt_demands` | Diversion demands (NYC/NJ) |
| `ibt_diversions` | Actual diversion deliveries |

### Flood Monitoring
| results_set | Description |
|---|---|
| `flood_stage` | Stage height at flood gages (ft) |
| `flood_level` | Flood level category (0-4) |
| `flood_gage_flow` | Observed flow at flood USGS gages |

### Withdrawals
| results_set | Description |
|---|---|
| `catchment_withdrawal` | Withdrawal at each catchment |
| `catchment_consumption` | Consumption at each catchment |

## Export & Reload

```python
# Export for later use
data.export("results_export.hdf5")

# Reload with optional filtering
data2 = Data()
data2.load_from_export(
    "results_export.hdf5",
    results_sets=["major_flow"],  # Load only what you need
    realizations=[0, 1, 2],       # Subset of ensemble members
)
```

## Input Data File Types

Hydrologic model input data is stored in `pywrdrb/data/flows/{inflow_type}/` with two distinct file types:

| File | Contents | Represents |
|---|---|---|
| `catchment_inflow_mgd.csv` | Incremental inflow at each catchment node | Local runoff contribution entering the network at a single node |
| `gage_flow_mgd.csv` | Total streamflow at USGS gage locations | Full natural (unmanaged) flow — the flow that *would* occur at a gage if there were no reservoirs, diversions, or other human management |

**Important distinction:** USGS observed streamflow (loaded via `load_observations()`) reflects *managed* conditions — it includes the effects of reservoir operations, diversions, and withdrawals. In contrast, `gage_flow_mgd.csv` in the `data/flows/` directories always represents **full natural flow** (i.e., no management effects). This difference matters when comparing model inputs to observations or when calibrating against gage records.

The simulation uses `catchment_inflow_mgd.csv` as the actual input; `gage_flow_mgd.csv` is used for prediction preprocessing (e.g., inflow prediction at Montague/Trenton) and validation.

## HDF5 File Structure

### Raw output (from OutputRecorder)
```
/{variable_name}  →  dataset with shape (timesteps, scenarios)
/time             →  datetime index
```
Variable naming: `reservoir_{name}`, `link_{name}`, `outflow_{name}`, `spill_{name}`, `catchment_{name}`

### Exported data
```
/{results_set}/{source_label}/{scenario_id}  →  DataFrame as HDF5 dataset
```

## Valid Results Sets by Loader

| Loader | Valid results_sets |
|---|---|
| `load_output()` | All 26 results_sets |
| `load_observations()` | major_flow, reservoir_downstream_gage, res_storage, flood_gage_flow |
| `load_hydrologic_model_flow()` | all, major_flow, reservoir_downstream_gage |
