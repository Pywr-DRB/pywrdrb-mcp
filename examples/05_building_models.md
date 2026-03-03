# Example: Building and Configuring Models

This example shows how to use the MCP tools to understand and configure
the Pywr-DRB ModelBuilder.

## View all ModelBuilder options

Ask:
> "What options can I set when building a Pywr-DRB model?"

The LLM calls `get_model_builder_options()`, which returns every field of
the `Options` dataclass with its type, default value, and description:
- `inflow_type` -- Which hydrologic model to use
- `enable_nyc_flood_operations` -- Toggle flood release logic
- `enable_lower_basin_ffmp` -- Toggle lower basin DRBC rules
- `nscenarios` -- Number of ensemble scenarios
- And many more...

## Inspect a specific ModelBuilder method

Ask:
> "Show me how reservoirs are added to the model"

The LLM calls `get_model_builder_method("add_node_major_reservoir")`,
returning the full source code of that method.

## Check what data files exist

Ask:
> "What inflow data is on disk?"

The LLM calls `get_data_file_list("flows")` to list all subdirectories
under `pywrdrb/data/flows/`, showing which inflow types have preprocessed
data ready to use.

## Add a new inflow source (guided prompt)

Ask:
> "Use the how_to_add_inflow_source prompt"

This walks through:
1. Preparing CSV data files in `pywrdrb/data/flows/{type}/`
2. Adding site-to-node mappings in `pywr_drb_node_data.py`
3. Creating a preprocessor (optional)
4. Registering the date range in `utils/dates.py`
5. Testing with `ModelBuilder`

## Debug a failing simulation (guided prompt)

Ask:
> "Use the how_to_debug_simulation prompt"

This provides a systematic debugging checklist:
1. Check the model build (inspect generated JSON)
2. Verify inflow data exists and date ranges match
3. Check parameter initialization errors
4. Examine output recorder and HDF5 files
5. Common error patterns table
6. Relevant MCP tools for each debugging step
