"""MCP prompt templates for guided Pywr-DRB workflows."""

from __future__ import annotations

from fastmcp.prompts import Message

from pywrdrb_mcp.server import mcp


@mcp.prompt()
def add_new_parameter() -> list[Message]:
    """Guide for adding a new custom Pywr Parameter to the Pywr-DRB model.

    Walks through the pattern: inherit from pywr.parameters.Parameter,
    implement required methods, and register with Pywr.
    """
    return [
        Message(
            role="user",
            content=(
                "I want to add a new custom parameter to Pywr-DRB. "
                "Walk me through the implementation pattern."
            ),
        ),
        Message(
            role="assistant",
            content="""\
# Adding a New Pywr Parameter to Pywr-DRB

## Step 1: Create a new file or add to an existing module

Place your parameter in `pywrdrb/parameters/`. If it's related to an existing
domain (FFMP, flood ops, etc.), add it to that file. Otherwise create a new module.

## Step 2: Inherit from `pywr.parameters.Parameter`

```python
from pywr.parameters import Parameter

class MyCustomParameter(Parameter):
    \"\"\"One-line description of what this parameter computes.

    Detailed explanation of the logic, data sources, and how it fits
    into the Pywr-DRB model.
    \"\"\"

    def __init__(self, model, node_name, other_params, **kwargs):
        super().__init__(model, **kwargs)
        self.node_name = node_name
        # Store references to other parameters, nodes, etc.

    def setup(self):
        \"\"\"Called once before the simulation starts.\"\"\"
        super().setup()
        # Allocate arrays, resolve parameter references
        # self.children contains parameters added via self.parents

    def value(self, ts, scenario_index):
        \"\"\"Called every timestep — return the parameter value.\"\"\"
        # ts.index = timestep index, scenario_index for ensemble
        return computed_value

    def after(self):
        \"\"\"Called after each timestep — store state for next step.\"\"\"
        super().after()

    def reset(self):
        \"\"\"Called when the model resets.\"\"\"
        super().reset()

    @classmethod
    def load(cls, model, data):
        \"\"\"Factory method for JSON-based model loading.\"\"\"
        # Parse the 'data' dict from the model JSON
        return cls(model, **parsed_args)

# Register with Pywr's parameter registry
MyCustomParameter.register()
```

## Step 3: Key patterns from existing Pywr-DRB parameters

- **Cross-parameter references**: Use `model.parameters[param_name]` to find other parameters.
  Add them as children with `self.children.add(param)` for proper dependency ordering.
- **Storage access**: Use `model.nodes[node_name].volume[scenario_index.global_id]`
- **Previous-step values**: Store in arrays via `setup()` and update in `after()`
- **Ensemble support**: All `value()` calls receive `scenario_index` — index arrays with
  `scenario_index.global_id` for ensemble-aware behavior.

## Step 4: Reference these existing classes as examples

- **Simple**: `LaggedReservoirRelease` in `parameters/general.py`
- **Medium**: `STARFITReservoirRelease` in `parameters/starfit.py`
- **Complex**: `VolBalanceNYCDownstreamMRF_step1` in `parameters/ffmp.py`

## Step 5: Export and integrate

1. Add to `parameters/__init__.py`
2. Reference in `model_builder.py` where appropriate
3. Register the class: `MyCustomParameter.register()`

Use the `get_parameter_class_info` tool to inspect any existing class for detailed signatures.
""",
        ),
    ]


@mcp.prompt()
def debug_simulation() -> list[Message]:
    """Step-by-step guide for debugging a Pywr-DRB simulation that fails or produces unexpected results."""
    return [
        Message(
            role="user",
            content="My Pywr-DRB simulation is failing or producing unexpected results. Help me debug it.",
        ),
        Message(
            role="assistant",
            content="""\
# Debugging a Pywr-DRB Simulation

## Step 1: Check the model build

```python
mb = ModelBuilder(start_date, end_date, inflow_type, options=options)
mb.make_model()
mb.write_model("debug_model.json")
```

- Inspect the generated JSON for missing nodes or parameters
- Check that `inflow_type` matches an available dataset (use `get_data_file_list` tool)
- Verify date ranges match the inflow data (use `pywrdrb://data/inflow-types` resource)

## Step 2: Verify inflow data exists

Common date ranges:
- `nhmv10`, `nwmv21`: 1983-10-01 to 2016-12-31
- `wrfaorc_calib_nlcd2016`: 1979-10-01 to 2021-12-31
- `pub_nhmv10_BC_withObsScaled`: 1945-01-01 to 2023-12-31

## Step 3: Check parameter initialization errors

- Look for `KeyError` in parameter `setup()` — usually means a node or parameter name
  doesn't match the model JSON
- Check `value()` returns — NaN propagation can cause silent failures
- For FFMP parameters: verify `NYCOperationsConfig` is properly initialized

## Step 4: Examine output recorder

- `OutputRecorder` writes to HDF5 — check if the output file was created
- Use `Data.load_output()` to inspect results
- Common issues: wrong `results_set` name, file path errors

## Step 5: Common error patterns

| Error | Likely Cause |
|---|---|
| `KeyError: 'node_name'` | Node not added to model, or name mismatch |
| `ValueError: negative storage` | Release constraints too loose, or inflow data issue |
| `FileNotFoundError: *.csv` | Missing inflow/diversion preprocessed data |
| `IndexError` in ensemble parameter | `NSCENARIOS` doesn't match ensemble data dimensions |
| LP infeasibility | Conflicting constraints — check MRF targets vs available flow |

## Step 6: Use the MCP tools

- `search_codebase("error_pattern")` — find where errors originate
- `get_parameter_class_info("ClassName")` — check parameter signatures
- `get_model_builder_method("add_node_major_reservoir")` — see how nodes are built
- `get_node_topology("node_name")` — verify network connections
""",
        ),
    ]


@mcp.prompt()
def understand_node(node_name: str = "delMontague") -> list[Message]:
    """Gather all information about a specific node in the river network.

    Args:
        node_name: The node to investigate (default: delMontague).
    """
    return [
        Message(
            role="user",
            content=f"Help me understand everything about the node '{node_name}' in the Pywr-DRB model.",
        ),
        Message(
            role="assistant",
            content=f"""\
# Understanding Node: {node_name}

I'll gather all available information about this node. Let me use the MCP tools:

## 1. Network topology
Use `get_node_topology("{node_name}", include_flood_topology=True)` to get:
- Upstream contributing nodes
- Downstream receiving node
- Travel time lag (days)
- Associated gage IDs (USGS, NHM, NWM, WRF-Hydro)

## 2. Parameters that reference this node
Use `search_codebase("{node_name}")` to find all parameter classes and model builder
methods that reference this node.

## 3. If it's a reservoir
Use `get_reservoir_details("{node_name}")` to get:
- Reservoir type (NYC / STARFIT / Lower Basin)
- Operational rule classifications
- Storage gauge info

## 4. Data sources
Check what observation and model data is available:
- `get_data_file_list("observations")` — look for matching USGS gage data
- Check the gage IDs from the topology lookup

## 5. Operational constraints
- If NYC reservoir: check FFMP rules (`pywrdrb://domain/ffmp-rules-summary`)
- If STARFIT reservoir: check STARFIT rules (`pywrdrb://domain/starfit-rules-summary`)
- If flood monitoring node: check flood operations (`pywrdrb://domain/flood-operations-summary`)

Let me start by pulling the topology data for {node_name}.
""",
        ),
    ]


@mcp.prompt()
def modify_ffmp_rules() -> list[Message]:
    """Guide for modifying FFMP operational parameters using NYCOperationsConfig."""
    return [
        Message(
            role="user",
            content="I want to modify the FFMP operational rules for a scenario. How do I do that?",
        ),
        Message(
            role="assistant",
            content="""\
# Modifying FFMP Rules via NYCOperationsConfig

The `NYCOperationsConfig` class (`parameters/nyc_operations_config.py`) centralizes all
tunable FFMP parameters. You can modify rules **without editing core source code**.

## Step 1: Create a custom config

```python
from pywrdrb.parameters.nyc_operations_config import NYCOperationsConfig

# Start from defaults
config = NYCOperationsConfig.from_defaults()
```

## Step 2: Modify specific rule categories

### Storage zones (drought level boundaries)
```python
config.update_storage_zones(
    level="L1b",                # Drought level to modify
    profile_type="monthly",     # "daily", "weekly", or "monthly"
    values=[...],               # New boundary values (12 monthly or 365 daily)
)
```

### MRF targets (Montague/Trenton minimum flows)
```python
config.update_mrf_factors(
    target="montague",          # "montague" or "trenton"
    level="L1a",                # Drought level
    factor=0.85,                # Multiplier on base MRF
)
```

### Delivery constraints (NYC/NJ diversion limits)
```python
config.update_delivery_constraints(
    entity="nyc",               # "nyc" or "nj"
    level="L1a",                # Drought level
    running_avg_limit=800.0,    # MGD running average limit
)
```

### Flood release limits
```python
config.update_flood_limits(
    reservoir="cannonsville",
    max_release=2000.0,         # MGD
)
```

## Step 3: Pass to ModelBuilder

```python
from pywrdrb.model_builder import ModelBuilder, Options

options = Options(enable_nyc_flood_operations=True)
mb = ModelBuilder(
    start_date="2000-01-01",
    end_date="2010-12-31",
    inflow_type="nhmv10",
    options=options,
    nyc_operations_config=config,
)
mb.make_model()
```

## Step 4: Key methods to inspect
Use `get_parameter_class_info("NYCOperationsConfig")` to see all available methods.

The config object is validated internally — it will raise errors if values are
out of acceptable ranges.
""",
        ),
    ]


@mcp.prompt()
def add_inflow_source() -> list[Message]:
    """Walkthrough for adding a new inflow data source to Pywr-DRB."""
    return [
        Message(
            role="user",
            content="I want to add a new hydrologic model inflow source to Pywr-DRB.",
        ),
        Message(
            role="assistant",
            content="""\
# Adding a New Inflow Source to Pywr-DRB

## Overview
Inflow data in Pywr-DRB comes from hydrologic models (NHM, NWM, WRF-Hydro) and observations.
Each source needs: preprocessed CSV data, site-to-node mappings, and date range configuration.

## Step 1: Prepare data files

Create a directory: `pywrdrb/data/flows/{your_inflow_type}/`

Required files:
- `catchment_inflow_mgd.csv` — Inflows at each catchment node (columns = node names)
- `gage_flow_mgd.csv` — Flows at gage locations
- `predicted_inflows_mgd.csv` — Predicted inflows at Montague/Trenton (optional)

All flows should be in MGD (million gallons per day). Index should be datetime.

## Step 2: Add site-to-node mappings

Edit `pywr_drb_node_data.py` to add a new `{source}_site_matches` dictionary:
```python
my_source_site_matches = {
    "cannonsville": ["site_id_1"],
    "pepacton": ["site_id_2"],
    # ... one entry per node
}
```

## Step 3: Create a preprocessor (optional)

If you need to transform raw model output, create a preprocessor in `pywrdrb/pre/flows.py`:
- Inherit from the base preprocessor pattern
- Implement flow disaggregation and scaling logic
- See existing `NhmV10FlowPreprocessor` as a reference

## Step 4: Register the date range

Add to `utils/dates.py`:
```python
model_date_ranges["your_inflow_type"] = ("start_date", "end_date")
```

## Step 5: Test

```python
from pywrdrb.model_builder import ModelBuilder
mb = ModelBuilder("start", "end", "your_inflow_type")
mb.make_model()
```

## Key files to inspect:
- `get_module_overview("pre/flows.py")` — Existing preprocessors
- `get_file_contents("pywr_drb_node_data.py")` — Site mapping dictionaries
- `get_data_file_list("flows")` — See existing inflow directories
""",
        ),
    ]


@mcp.prompt()
def review_model_output() -> list[Message]:
    """Guide for loading and interpreting Pywr-DRB simulation results."""
    return [
        Message(
            role="user",
            content="I've run a simulation. How do I load and interpret the results?",
        ),
        Message(
            role="assistant",
            content="""\
# Reviewing Pywr-DRB Simulation Output

## Step 1: Load results with the Data class

```python
from pywrdrb.load import Data

data = Data(
    results_sets=["major_flow", "res_storage", "res_release"],
    output_filenames=["path/to/output.hdf5"],
    units="MG",    # or "MCM", "CFS", etc.
)
data.load_output()
```

## Step 2: Access result DataFrames

Results are organized by `results_set` → data type → scenario:
```python
# Major flows at key points (Montague, Trenton, etc.)
flows = data.major_flow["output"]["output_0"]  # DataFrame: dates × nodes

# Reservoir storage
storage = data.res_storage["output"]["output_0"]

# Reservoir releases
releases = data.res_release["output"]["output_0"]
```

## Step 3: Compare with observations

```python
data.load_observations()
obs_flows = data.major_flow["obs"]["obs"]
```

## Step 4: Available results_set options

Use `pywrdrb://data/results-sets` resource for the full list. Key ones:
- `major_flow` — Streamflow at key river points (MGD)
- `res_storage` — Reservoir storage volumes (MG)
- `res_release` — Reservoir releases (MGD)
- `inflow` — Inflows at each node (MGD)
- `ibt_diversions` — NYC/NJ diversion deliveries (MGD)
- `mrf_targets` — Montague/Trenton flow targets (MGD)
- `res_level` — FFMP drought levels
- `flood_stage` — Stage height at flood monitoring nodes (ft)
- `temperature` — Water temperature data
- `salinity` — Salt front location

## Step 5: Export for later use

```python
data.export("results_export.hdf5")

# Reload later:
data2 = Data()
data2.load_from_export("results_export.hdf5", results_sets=["major_flow"])
```

## Key tools:
- `get_parameter_class_info("OutputRecorder")` — How results are saved
- `pywrdrb://api/data-loader-api` — Full Data class API
""",
        ),
    ]
