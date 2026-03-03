# Example: Loading and Reviewing Simulation Results

This example shows how to use the MCP tools to understand Pywr-DRB
simulation output and the Data class that loads it.

## Understand the Data class structure

Ask:
> "How is simulation output organized in Pywr-DRB?"

The LLM calls `get_data_object_info()`, which explains:
- **Access pattern**: `data.{results_set}['{source_label}'][scenario_id]`
- **Example**: `data.major_flow["drb_output_nhmv10"][0]` returns a DataFrame
- **Source labels**: derived from HDF5 filename for output, `"obs"` for observations
- **Loading methods**: `load_output()`, `load_observations()`, `load_hydrologic_model_flow()`
- **HDF5 key conventions**: `reservoir_X`, `link_X`, `outflow_X`, etc.

## List available results sets

Ask:
> "What results sets can I load?"

The LLM calls `get_results_set_list()`:
- `major_flow` -- Streamflow at key river points (MGD)
- `res_storage` -- Reservoir storage volumes (MG)
- `res_release` -- Reservoir releases (MGD)
- `inflow` -- Inflows at each node (MGD)
- `ibt_diversions` -- NYC/NJ diversion deliveries (MGD)
- `mrf_targets` -- Montague/Trenton flow targets (MGD)
- `res_level` -- FFMP drought levels
- `flood_stage` -- Stage height at flood monitoring nodes (ft)

## Check available inflow types

Ask:
> "What inflow datasets are available?"

The LLM calls `get_inflow_type_list()`:
```
nhmv10:                  1983-10-01 to 2016-12-31
nwmv21:                  1983-10-01 to 2016-12-31
pub_nhmv10_BC_withObsScaled: 1945-01-01 to 2023-12-31
...
```

## Walk through the full output review workflow (guided prompt)

Ask:
> "Use the how_to_review_output prompt"

This guides you through:
1. Loading results with `Data(results_sets=[...], output_filenames=[...])`
2. Accessing DataFrames: `data.major_flow["output"]["output_0"]`
3. Comparing with observations: `data.load_observations()`
4. Exporting for later use: `data.export("results.hdf5")`
