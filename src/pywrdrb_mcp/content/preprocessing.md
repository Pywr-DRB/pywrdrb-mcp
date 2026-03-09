# Preprocessing & Inflow Prediction

Pywr-DRB includes preprocessing modules in `pre/` for preparing input data before simulation.

## Inflow Prediction (`pre/predict_inflows.py`)

The `PredictedInflowPreprocessor` generates lag-based inflow predictions at Montague and Trenton, used to determine NYC and lower basin reservoir release operations while accounting for travel time.

### Prediction Modes

| Mode | Description | Status |
|------|-------------|--------|
| `regression_disagg` | Autoregressive disaggregated predictions using trained regression models | Default, fully tested |
| `perfect_foresight` | Uses actual future observations as "predictions" | Fully tested, used as default in ModelBuilder |
| `moving_average` | 7-day rolling average of observed flows | Partial, not fully tested |
| `same_day` | Uses current day's observation as prediction | Partial, not fully tested |

### Travel Time Matrices

Predictions account for flow routing delays between nodes:
- **Node → Montague**: 0-2 day travel times
- **Node → Trenton**: 0-4 day travel times
- Predictions generate columns like: `delMontague_lag1_regression_disagg`, `delTrenton_lag4_perfect_foresight`

### Usage

```python
from pywrdrb.pre import PredictedInflowPreprocessor

predictor = PredictedInflowPreprocessor(
    flow_type="nhmv10",
    modes=("regression_disagg",),
    use_log=True,           # Log-transform for regression
)
predictor.process()
predictor.save()            # Writes to data/flows/{flow_type}/predicted_inflows_mgd.csv
```

### Ensemble Processing

`PredictedInflowEnsemblePreprocessor` extends the base class for MPI-parallelized ensemble processing:
- Reads ensemble HDF5 files with batch extraction
- Distributes across MPI ranks for efficiency
- Outputs to HDF5 format

## Flow Preprocessing (`pre/flows.py`)

Handles hydrologic model output preprocessing:
- Reads raw NHM/NWM/WRF-Hydro output files
- Disaggregates flows to catchment nodes using site-to-node mappings
- Applies observation scaling (`_withObsScaled` variants)
- Outputs standardized CSV files in `data/flows/{inflow_type}/`:
  - `catchment_inflow_mgd.csv` — incremental inflow at each catchment node (used as simulation input)
  - `gage_flow_mgd.csv` — total full natural (unmanaged) flow at USGS gage locations (used for prediction preprocessing and validation; *not* the same as USGS observed flow, which includes management effects)

## Diversion Processing

**`pre/extrapolate_nyc_nj_diversions.py`** — Extrapolates historical NYC and NJ diversion data:
- Uses historical USGS diversion records
- Fills gaps and extends time series
- Outputs `diversion_nyc_extrapolated_mgd.csv` and `diversion_nj_extrapolated_mgd.csv`

**`pre/predict_diversions.py`** — Predicts NYC/NJ diversions for simulation:
- Outputs `predicted_diversions_mgd.csv`

## Observation Data Retrieval (`pre/obs_data_retrieval.py`)

Downloads and processes USGS observation data:
- Streamflow gage data via `dataretrieval` package
- Reservoir storage observations
- Outputs to `data/observations/` directory

## Key Configuration

The `ModelBuilder.Options.flow_prediction_mode` field controls which prediction mode is used at runtime:
- `"perfect_foresight"` (default) — uses actual future flows
- `"regression_disagg"` — uses trained regression predictions

Preprocessing must be run before simulation if using `regression_disagg` mode.
