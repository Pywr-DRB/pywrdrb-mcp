# Post-Processing & Performance Metrics

Pywr-DRB includes two post-processing modules for evaluating simulation results:
- `post/metrics.py` — Hashimoto reliability/vulnerability and shortfall event analysis
- `post/calculate_error_metrics.py` — Statistical error metrics (NSE, KGE, FDC, autocorrelation)

## Hashimoto Performance Metrics (`post/metrics.py`)

Based on Hashimoto et al. (1982), these metrics evaluate how well simulated flows meet MRF targets.

### Core Functions

**`calculate_reliability(flow, target)`**
- Returns fraction of timesteps where `flow > target` (0 to 1)
- Input: pd.Series or np.ndarray for both flow and target

**`calculate_vulnerability(flow, target)`**
- Returns maximum single-day deficit magnitude: `max(target - flow)`
- Measures worst-case shortfall in flow units (MGD)

**`get_ensemble_hashimoto_metrics(major_flows, mrf_targets, model, node, lower_basin_mrf_contributions=None)`**
- Calculates reliability and vulnerability across all ensemble realizations
- Special handling for `delTrenton` (includes lagged Blue Marsh contributions)
- Returns: `(np.array[reliability], np.array[vulnerability])` per realization

### Shortfall Event Analysis

**`get_shortfall_metrics(...)`** — Comprehensive event-based drought analysis.

Key parameters:
- `shortfall_threshold` (default 0.95) — fraction of target considered "satisfied"
- `shortfall_break_length` (default 7) — non-shortfall days needed to end an event
- `units` — 'MG' or 'MCM'
- `start_date`, `end_date` — optional time subsetting

Returns nested dict: `results[node][model]` containing:
- `reliability` — % of time flow exceeds threshold (per realization for ensembles)
- `resiliency` — probability of recovering if currently below threshold
- `durations` — list of event durations (days)
- `severities` — list of cumulative deficits per event
- `intensities` — average deficit per day within each event
- `vulnerabilities` — max daily deficit within each event
- `event_starts`, `event_ends` — datetime boundaries of each event
- `realization_ids` — which ensemble member each event belongs to

### Routing Utilities

**`get_lagged_lower_basin_contributions(...)`**
- Applies cumulative travel-time lags to lower basin MRF contributions
- Accounts for Blue Marsh → Trenton routing (2-day lag)

**`add_blueMarsh_mrf_contribution_to_delTrenton(...)`**
- Adds lagged Blue Marsh releases to Trenton equivalent flow
- Required for regulatory compliance evaluation at Trenton

## Error Metrics (`post/calculate_error_metrics.py`)

**`calculate_error_metrics(reservoir_downstream_gages, major_flows, models, output, nodes, scenarios, ...)`**

Evaluates model performance across 4 timescales: Daily, Monthly, Yearly, Full-period.

### Metrics computed per timescale:
- **NSE** — Nash-Sutcliffe Efficiency
- **KGE** — Kling-Gupta Efficiency (and components: correlation, alpha, beta)
- **logNSE** — NSE on log-transformed flows (sensitive to low flows)
- **logKGE** — KGE on log-transformed flows
- **Autocorrelation** — 1-day and 7-day lag autocorrelation (relative to observed)
- **Roughness** — Variability metric in log space

### Flow Duration Curve (FDC) metrics:
- **FDC horizontal match** — Kolmogorov-Smirnov statistic
- **FDC vertical match** — Maximum vertical deviation
- **FDC slopes** — 25-75th percentile slope, 1-99th percentile slope, min-max slope (log space)

### Return format:
Multi-indexed DataFrame: `[node, model, scenario]` with 18+ metrics per timescale.

## Usage Example

```python
from pywrdrb.load import Data
from pywrdrb.post.metrics import get_shortfall_metrics

# Load results
data = Data(results_sets=['major_flow', 'mrf_targets', 'ibt_demands', 'ibt_diversions',
                          'lower_basin_mrf_contributions'])
data.load_output(output_filenames=['output.hdf5'])

# Calculate shortfall metrics
results = get_shortfall_metrics(
    major_flows=data.major_flow,
    lower_basin_mrf_contributions=data.lower_basin_mrf_contributions,
    mrf_targets=data.mrf_targets,
    ibt_demands=data.ibt_demands,
    ibt_diversions=data.ibt_diversions,
    models_mrf=['drb_output_nhmv10'],
    models_ibt=['drb_output_nhmv10'],
    nodes=['delMontague', 'delTrenton', 'nyc', 'nj'],
    shortfall_threshold=0.95,
)

# Access results
print(results['delMontague']['drb_output_nhmv10']['reliability'])
```
