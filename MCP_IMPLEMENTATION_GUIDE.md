# Pywr-DRB MCP Server: Implementation Guide

This document provides complete instructions for building a custom MCP (Model Context Protocol) server that gives LLMs efficient access to the Pywr-DRB water resource model codebase. It is intended to be used as a reference by a Claude Code session working in this directory.

---

## Goal

Build a standalone MCP server (`pywrdrb-mcp`) that exposes the Pywr-DRB model's structure, topology, operational rules, and codebase to LLMs via the Model Context Protocol. The server should enable Claude Code (or any MCP-compatible client) to quickly understand and work with the Pywr-DRB model without needing to manually search through dozens of source files.

---

## Critical Constraints

1. **Separate project**: The MCP server lives at `Pywr-DRB\pywrdrb-mcp\`, a sibling folder to the source code at `Pywr-DRB\Pywr-DRB\`. It is its own Python package with its own `pyproject.toml`.
2. **No edits to Pywr-DRB source code**: The `Pywr-DRB\Pywr-DRB\` repo must not be modified in any way. The MCP server reads from it but never writes to it.
3. **No importing pywrdrb at runtime**: Pywr-DRB has heavy dependencies (`pywr==1.27.4`, `torch`, `mpi4py`, `scipy`). The MCP server must NOT import `pywrdrb` or any of its modules. Instead, use Python's `ast` module to parse source files and extract information statically.
4. **Minimal dependencies**: The only required dependency is `fastmcp>=2.0`. Use Python standard library for everything else (`ast`, `csv`, `pathlib`, `re`, `json`). No numpy, pandas, or other scientific packages.
5. **Use `uv`** for package management and running the server.
6. **Efficiency**: Use agents for parallelizable research/exploration tasks. Use `sonnet` or `haiku` model for straightforward implementation tasks (file creation, simple tool implementations). Reserve `opus` for complex design decisions and domain-knowledge content writing.

---

## Background: Pywr-DRB Codebase

The source package is located at `Pywr-DRB\Pywr-DRB\src\pywrdrb\`. Key modules and what they contain:

### Core Modules
- **`model_builder.py`** — `ModelBuilder` class with `Options` dataclass (25+ methods for constructing the Pywr simulation model). Options include: `NSCENARIOS`, `inflow_ensemble_indices`, `nyc_nj_demand_source`, `flow_prediction_mode`, `enable_nyc_flood_operations`, `use_trimmed_model`, temperature/salinity model configs.
- **`pywr_drb_node_data.py`** — Module-level dictionaries defining the river network topology: `upstream_nodes_dict`, `immediate_downstream_nodes_dict`, `downstream_node_lags`, plus data source mappings (`obs_site_matches`, `nhm_site_matches`, `nwm_site_matches`, `wrf_hydro_site_matches`). Also contains a `TopologyDictionaries` class. **NOTE**: This file imports `pywrdrb.path_manager` at the top, so it cannot be executed — but the dictionaries are pure string/list literals extractable via `ast.literal_eval`.
- **`recorder.py`** — `OutputRecorder` class for saving simulation results to HDF5.
- **`path_manager.py`** — PathNavigator-based directory management (`get_pn_object()`).
- **`flood_thresholds.py`** — Flood stage threshold dictionaries for monitoring nodes.

### Parameters (`parameters/`)
30+ custom Pywr `Parameter` subclasses implementing DRB operational rules:
- **`ffmp.py`** (~2000 lines) — NYC FFMP operations: `FfmpNycRunningAvgParameter`, `NYCCombinedReleaseFactor`, `NYCFloodRelease`, `TotalReleaseNeededForDownstreamMRF`, `VolBalanceNYCDownstreamMRF_step1/step2`, `VolBalanceNYCDemand`, etc.
- **`starfit.py`** — `STARFITReservoirRelease` for non-NYC reservoirs (Turner et al. 2021 model).
- **`general.py`** — `LaggedReservoirRelease` for historical release reconstruction.
- **`ensemble.py`** — `FlowEnsemble`, `PredictionEnsemble` for ensemble HDF5 data access.
- **`lower_basin_ffmp.py`** — `LowerBasinMaxMRFContribution` and related classes for lower basin reservoirs (Beltzville, Blue Marsh, Nockamixon).
- **`banks.py`** — `IERQRelease_step1` for tracking Trenton Equivalent Flow banks.
- **`flood_stage.py`** — `StageFromDischargeParameter`, `FloodLevelIndicator` for flood monitoring.
- **`water_temperature.py`** — LSTM temperature model coupling.
- **`salt_front_location.py`** — LSTM salinity model coupling.
- **`nyc_operations_config.py`** — `NYCOperationsConfig` centralized operations configuration.
- **`rating_curves.py`** — USGS rating curve data for stage-discharge conversion.

### Data Loading (`load/`)
- **`data_loader.py`** — `Data` class: unified interface for loading observations, simulation outputs, and hydrologic model data. Methods: `load_observations()`, `load_output()`, `export()`.
- **`output_loader.py`** — `Output` class for HDF5 simulation results.
- **`observation_loader.py`** — `Observation` class for USGS gage data.
- **`hydrologic_model_loader.py`** — `HydrologicModelFlow` for NHM/NWM data.

### Preprocessing (`pre/`)
- **`flows.py`** — Flow data preprocessors for NHM, NWM, WRF-Hydro, observation-scaled variants.
- **`predict_inflows.py`** — `PredictedInflowPreprocessor`: regression-based inflow predictions at Montague & Trenton (modes: "regression_disagg", "perfect_foresight").
- **`predict_diversions.py`** — NJ diversion predictions.
- **`extrapolate_nyc_nj_diversions.py`** — Historical diversion extrapolation.
- **`obs_data_retrieval.py`** — USGS API data retrieval functions.

### Utilities (`utils/`)
- **`lists.py`** — `reservoir_list` (17 reservoirs), `reservoir_list_nyc` (3 NYC), `majorflow_list`, `starfit_reservoir_list` (14), `flood_monitoring_nodes`, `drbc_lower_basin_reservoirs`, `independent_starfit_reservoirs`, etc.
- **`constants.py`** — Unit conversions: `cfs_to_mgd`, `cms_to_mgd`, `mcm_to_mg`, etc.
- **`dates.py`** — Date utilities and `model_date_ranges` dict.
- **`results_sets.py`** — Definitions for output data categories (major_flow, res_storage, etc.).

### Data Files (`data/`)
- `observations/` — USGS gage flows, reservoir storage CSVs.
- `flows/{inflow_type}/` — Catchment inflow data (CSV/HDF5) per inflow source.
- `diversions/` — NYC/NJ diversion CSVs.
- `operational_constants/` — FFMP profiles CSVs, constants.csv, istarf_conus.csv.
- `rating_curves/` — USGS rating curve CSVs per site.

### Key Domain Concepts
- **17 reservoirs**: 3 NYC (cannonsville, pepacton, neversink) + 14 STARFIT-operated.
- **River network**: DAG with ~30+ nodes, travel time lags (0-2 days), convergence points at delLordville, delMontague, delDRCanal, delTrenton.
- **FFMP**: Flexible Flow Management Program — drought levels (1a-5), storage zones, delivery constraints, minimum required flows (Montague: 1750 MGD, Trenton: 3000 MGD).
- **STARFIT**: Seasonal, storage-based release policy for non-NYC reservoirs.
- **Flood monitoring**: 3 optional USGS gage nodes (01426500 Hale Eddy, 01421000 Fishs Eddy, 01436690 Bridgeville).
- **Inflow types**: nhmv10, nwmv21, wrf variants, observation-scaled variants, each with different date ranges.

---

## MCP Technology Stack

- **SDK**: `fastmcp>=2.0` (PyPI package, wraps the official `mcp` SDK)
  - Docs: https://gofastmcp.com
  - Uses Python type hints and docstrings to auto-generate tool definitions
  - Decorator-based: `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()`
- **Transport**: STDIO (standard for Claude Code integration)
- **Registration with Claude Code**:
  ```bash
  claude mcp add --transport stdio pywrdrb-mcp -- uv run --directory "C:/Users/tjame/Desktop/Research/DRB/Pywr-DRB/pywrdrb-mcp" python -m pywrdrb_mcp.server
  ```

### MCP Primitives
- **Tools**: Executable functions the LLM calls on-demand with parameters. Use for dynamic queries (topology lookups, code search, class info).
- **Resources**: Read-only structured data available for reference. Use for static/pre-computed knowledge (network graph, constant tables, operational rule summaries).
- **Prompts**: Reusable templates for common workflows. Use for guided multi-step tasks (adding parameters, debugging simulations).

---

## Project Structure

Create at `Pywr-DRB\pywrdrb-mcp\`:

```
pywrdrb-mcp/
├── pyproject.toml
├── README.md
├── src/
│   └── pywrdrb_mcp/
│       ├── __init__.py
│       ├── server.py               # FastMCP entry point with main()
│       ├── config.py               # PYWRDRB_ROOT path config (env var with default)
│       ├── index/
│       │   ├── __init__.py
│       │   ├── builder.py          # PywrDRBIndex class: one-time startup indexer
│       │   ├── ast_utils.py        # AST parsing utilities
│       │   └── file_utils.py       # Path validation, file reading, regex search
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── topology.py         # get_node_topology, get_reservoir_details
│       │   ├── code.py             # search_codebase, get_file_contents, get_module_overview
│       │   ├── parameters.py       # get_parameter_class_info
│       │   ├── model_builder.py    # get_model_builder_options, get_model_builder_method
│       │   └── data.py             # get_operational_constants
│       ├── resources/
│       │   ├── __init__.py
│       │   └── static.py           # Resource registration
│       ├── prompts/
│       │   ├── __init__.py
│       │   └── templates.py        # Prompt definitions
│       └── content/                # Hand-written domain knowledge
│           ├── ffmp_rules.md
│           ├── starfit_rules.md
│           ├── flood_operations.md
│           └── getting_started.md
└── tests/
    ├── test_ast_utils.py
    ├── test_index.py
    └── test_tools.py
```

---

## Implementation Phases

### Phase 1: Core Infrastructure

Set up the project skeleton and core indexing engine.

1. **Create `pyproject.toml`** with `uv`-compatible config:
   - name: `pywrdrb-mcp`
   - requires-python: `>=3.10`
   - dependencies: `["fastmcp>=2.0"]`
   - entry point script: `pywrdrb-mcp = "pywrdrb_mcp.server:main"`
   - Build system: hatchling

2. **Implement `config.py`**:
   - `PYWRDRB_ROOT`: Path to `Pywr-DRB\Pywr-DRB\src\pywrdrb\`, configurable via `PYWRDRB_ROOT` env var.
   - Default value: `C:\Users\tjame\Desktop\Research\DRB\Pywr-DRB\Pywr-DRB\src\pywrdrb`

3. **Implement `index/ast_utils.py`** — The most critical module. Functions needed:
   - `extract_module_level_dict(filepath, variable_name)` — Parse a .py file with `ast.parse()`, find an `ast.Assign` targeting `variable_name`, extract the value via `ast.literal_eval` on the source segment. Used for topology dicts in `pywr_drb_node_data.py`.
   - `extract_module_level_list(filepath, variable_name)` — Similar but for lists from `utils/lists.py`.
   - `extract_class_info(filepath, class_name=None)` — AST-walk a file, find `ast.ClassDef` nodes, extract: class name, docstring (first `ast.Expr` with `ast.Constant`), method names and argument lists, base classes. If `class_name` is None, return all classes.
   - `extract_function_info(filepath)` — Extract top-level function names, signatures, and docstrings.
   - `extract_method_source(filepath, class_name, method_name)` — Return the raw source code lines for a specific method within a class.
   - `extract_dataclass_fields(filepath, class_name)` — Special handling for `@dataclass` classes like `Options`: extract field names, types, defaults, and docstring descriptions.

4. **Implement `index/file_utils.py`**:
   - `validate_path(relative_path)` — Ensure path is within PYWRDRB_ROOT, prevent directory traversal.
   - `read_file(relative_path, start_line=1, end_line=0)` — Read file with line number bounds.
   - `search_files(root, query, file_pattern, max_results)` — Regex search using `pathlib.rglob` and `re.search`.
   - `get_package_structure(root)` — Walk directory tree, build dict of {path: module_docstring}.

5. **Implement `index/builder.py`** — `PywrDRBIndex` class:
   - Built once at server startup, results cached in instance attributes.
   - Indexes: topology dicts (from `pywr_drb_node_data.py`), reservoir/node lists (from `utils/lists.py`), parameter class index (AST-scan all `parameters/*.py`), constants (from `utils/constants.py`), flood thresholds (from `flood_thresholds.py`), package structure map.
   - Handle derived lists: `reservoir_list_nyc = reservoir_list[:3]` must be computed in the indexer from the extracted `reservoir_list`.

6. **Implement `server.py`**:
   - Create `FastMCP` instance with descriptive name and instructions.
   - Build `PywrDRBIndex` at module level (startup).
   - Import and register tools, resources, prompts.
   - `main()` function calls `mcp.run()`.

### Phase 2: Tools

Implement 8 tools in order of impact. Each tool is a function decorated with `@mcp.tool()` that takes typed parameters and returns a string (usually JSON or formatted text).

**Tools to implement:**

1. **`get_node_topology(node_name, include_flood_topology=False)`** — Returns upstream nodes, downstream node, travel time lag, and optionally USGS/NHM/NWM gage IDs. Uses cached topology from the index.

2. **`get_parameter_class_info(class_name)`** — Returns docstring, `__init__` signature, all method names with signatures, base classes, and module location. Uses on-demand AST parsing of the parameter file.

3. **`get_file_contents(relative_path, start_line=1, end_line=0)`** — General-purpose file reader. Path must be within pywrdrb source tree.

4. **`search_codebase(query, file_pattern="*.py", max_results=20)`** — Regex search across pywrdrb source. Returns matching lines with file paths and line numbers.

5. **`get_reservoir_details(reservoir_name)`** — Aggregated info: reservoir type (NYC/STARFIT/lower basin), downstream node, gage IDs across all data sources, list classification. Pulls from multiple cached index sources.

6. **`get_module_overview(module_path)`** — Module docstring + list of all public classes and functions with one-line descriptions. Uses AST parsing.

7. **`get_model_builder_options()`** — Returns all fields of the `Options` dataclass with types, defaults, and descriptions. Uses AST dataclass field extraction.

8. **`get_model_builder_method(method_name)`** — Returns the full source code for a specific `ModelBuilder` method. Uses AST method source extraction.

9. **`get_repo_status()`** — Returns the current git branch, recent commit history, and modified files for the Pywr-DRB source repo (`Pywr-DRB\Pywr-DRB\`). Uses `subprocess.run` to call `git` commands (`git branch --show-current`, `git log --oneline -10`, `git status --short`). This lets the LLM know which branch's code it's reading.

10. **`get_data_file_list(data_subdir="")`** — Enumerates actual data files under `pywrdrb/data/` (or a subdirectory like `"flows"` or `"observations"`). Returns file names, sizes, and modification dates. Useful for discovering which inflow types, diversion files, and rating curves are actually present on disk rather than relying on hard-coded assumptions.

11. **`refresh_index()`** — Rebuilds the `PywrDRBIndex` cache without restarting the server. Useful after switching branches, pulling changes, or modifying data files mid-session. Returns a summary of what changed (new/removed files, updated topology, etc.).

**Tool design guidelines:**
- Each tool function should have a clear docstring — FastMCP uses this as the tool description shown to the LLM.
- Use type hints for all parameters — FastMCP auto-generates JSON schemas from these.
- Return structured text (JSON for data, markdown for explanations).
- Handle errors gracefully (return helpful error messages, not exceptions).
- Keep tool output concise — LLMs have context limits. Paginate or summarize large results.

### Phase 3: Resources

Implement 14 resources. Resources are registered with `@mcp.resource("uri")` and return string content.

**Auto-generated resources** (built from index data):
- `pywrdrb://topology/network-graph` — JSON dump of the full topology.
- `pywrdrb://topology/reservoir-list` — JSON: all 17 reservoirs with type classification.
- `pywrdrb://topology/node-list` — JSON: major flow nodes, flood monitoring nodes.
- `pywrdrb://api/parameter-class-index` — Markdown table of all parameter classes with module, one-line description.
- `pywrdrb://api/model-builder-api` — Markdown: all ModelBuilder method names with one-line descriptions.
- `pywrdrb://api/data-loader-api` — Markdown: Data class methods and results_set options.
- `pywrdrb://data/inflow-types` — JSON: available inflow types.
- `pywrdrb://data/results-sets` — JSON or markdown: all results_set options with descriptions.
- `pywrdrb://domain/constants` — JSON: unit conversion constants.
- `pywrdrb://project/package-structure` — Markdown: file tree with module descriptions.
- `pywrdrb://project/repo-status` — Current git branch, recent commits, modified files for the Pywr-DRB source repo.

**Resource templates** (parameterized URIs — FastMCP supports `@mcp.resource("pywrdrb://parameter/{class_name}")`):
- `pywrdrb://parameter/{class_name}` — Returns detailed info for a specific parameter class. Complements the `get_parameter_class_info` tool by also being accessible as a resource the client can attach to context.
- `pywrdrb://reservoir/{reservoir_name}` — Returns reservoir details as a resource.

**Hand-written content resources** (Markdown files in `content/`):
- `pywrdrb://domain/ffmp-rules-summary` — Comprehensive FFMP rules: drought levels, storage zones, MRF targets, delivery constraints, flood releases, volume balancing logic. Distilled from `docs/NYC_Operations_Configuration.md`, `parameters/ffmp.py`, and `parameters/nyc_operations_config.py`.
- `pywrdrb://domain/starfit-rules-summary` — STARFIT release policy: harmonic terms, storage factors, inflow terms, physical constraints. From `parameters/starfit.py`.
- `pywrdrb://domain/flood-operations-summary` — Flood monitoring stages, rating curves, thresholds, flood-responsive operations. From `flood_thresholds.py`, `parameters/flood_stage.py`.
- `pywrdrb://project/getting-started` — Example workflow adapted from `simple_run.py`.

**Writing domain content**: The hand-written content files require careful reading of the source code and domain documentation to produce accurate, concise summaries. This is where the most domain expertise is needed. Read the relevant source files thoroughly before writing each content file.

### Phase 4: Prompts

Implement 6 prompt templates. Each prompt is registered with `@mcp.prompt()` and returns a list of messages that guide the LLM through a workflow.

1. **`add-new-parameter`** — Explains the pattern: inherit from `pywr.parameters.Parameter`, implement `value()`, `setup()`, `after()`, `reset()` methods, register with Pywr. References existing parameter classes as examples.

2. **`debug-simulation`** — Step-by-step diagnostic: check model build logs, verify inflow data, check parameter initialization, examine output recorder, common error patterns.

3. **`understand-node`** — Template that uses topology tools to pull all info for a node: upstream/downstream, parameters that reference it, data sources, operational constraints.

4. **`modify-ffmp-rules`** — Guide for using `NYCOperationsConfig` to change FFMP parameters without editing core code.

5. **`add-inflow-source`** — Walkthrough: create preprocessor subclass, add site_matches to `pywr_drb_node_data.py`, create flow data directory, process data.

6. **`review-model-output`** — Template for loading and interpreting simulation results using the `Data` class.

### Phase 5: Testing & Registration

1. **Unit tests** (`tests/`):
   - `test_ast_utils.py` — Verify dict/list/class extraction against known outputs from the actual pywrdrb source files.
   - `test_index.py` — Verify `PywrDRBIndex` builds successfully and contains expected data.
   - `test_tools.py` — Call each tool with known parameters, verify output structure.

2. **Run tests**: `uv run pytest tests/`

3. **Manual test**: `uv run python -m pywrdrb_mcp.server` — verify it starts without errors.

4. **Register with Claude Code**:
   ```bash
   claude mcp add --transport stdio pywrdrb-mcp -- uv run --directory "C:/Users/tjame/Desktop/Research/DRB/Pywr-DRB/pywrdrb-mcp" python -m pywrdrb_mcp.server
   ```

5. **End-to-end validation** — In a new Claude Code session, test queries:
   - "What nodes are upstream of delMontague?"
   - "Describe the STARFITReservoirRelease parameter class"
   - "What are the FFMP drought levels?"
   - "Search for where minimum release requirements are defined"
   - "Show me the Options dataclass fields"

---

## Key Technical Details

### AST Parsing Strategy

The most critical technical challenge is extracting structured data from Python source files without executing them. Here is the approach:

**For dictionary literals** (e.g., `upstream_nodes_dict` in `pywr_drb_node_data.py`):
```python
import ast

def extract_module_level_dict(filepath, variable_name):
    source = Path(filepath).read_text()
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    segment = ast.get_source_segment(source, node.value)
                    return ast.literal_eval(segment)
    return None
```

**Caveats**:
- `ast.literal_eval` only works on pure literals (strings, numbers, lists, dicts, tuples, booleans, None). It will fail on expressions like `reservoir_list[:3]` or f-strings.
- For derived variables, compute them in the indexer from the base data.
- Some dicts in `pywr_drb_node_data.py` (like `storage_curves`) use f-strings — skip these and provide alternative access via the `get_file_contents` tool.

**For class definitions**:
```python
def extract_class_info(filepath, class_name=None):
    source = Path(filepath).read_text()
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if class_name and node.name != class_name:
                continue
            info = {
                "name": node.name,
                "bases": [ast.dump(b) for b in node.bases],
                "docstring": ast.get_docstring(node),
                "methods": []
            }
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    info["methods"].append({
                        "name": item.name,
                        "args": [a.arg for a in item.args.args],
                        "docstring": ast.get_docstring(item)
                    })
            results.append(info)
    return results
```

### Staleness & Caching

- The index is built once at server startup. Pywrdrb source files change infrequently.
- For development workflows, restarting the MCP server refreshes the index.
- Optionally, add a `refresh_index` tool that rebuilds the cache without restarting.
- Store file modification times (`os.path.getmtime`) at index time; check on-demand tool calls to warn if a file has changed.

### Windows Compatibility

- Use `pathlib.Path` throughout for cross-platform path handling.
- The server runs via STDIO so no network ports are needed.
- `ast.get_source_segment()` requires the raw source text — always read with `Path.read_text(encoding='utf-8')`.

---

## Reference: Existing Source Files to Read

When implementing domain content files (`content/*.md`), read these source files for accurate information:

| Content File | Source Files to Read |
|---|---|
| `ffmp_rules.md` | `Pywr-DRB\docs\NYC_Operations_Configuration.md`, `parameters/ffmp.py`, `parameters/nyc_operations_config.py`, `parameters/banks.py` |
| `starfit_rules.md` | `parameters/starfit.py` (read the class docstring and `value()` method) |
| `flood_operations.md` | `flood_thresholds.py`, `parameters/flood_stage.py`, `FLOOD_OPERATIONS_RELEASE_NOTES.md` |
| `getting_started.md` | `Pywr-DRB\Pywr-DRB\simple_run.py`, `model_builder.py` docstring |

---

## Summary of Deliverables

1. A working MCP server at `Pywr-DRB\pywrdrb-mcp\`
2. 11 tools for dynamic codebase queries (including git status, data file discovery, and index refresh)
3. 16+ resources for pre-computed reference data (including parameterized URI templates and repo status)
4. 6 prompts for guided workflows
5. 4 hand-written domain knowledge content files
6. Unit tests for core functionality
7. Registration command for Claude Code integration

## Key Design Principles

- **No cloning or installing Pywr-DRB**: The MCP reads directly from the local source tree via `PYWRDRB_ROOT`. It never imports, installs, or executes pywrdrb code.
- **Branch-aware**: The `get_repo_status` tool and `pywrdrb://project/repo-status` resource report which git branch is checked out, so the LLM always knows what version of the code it's reading.
- **Refreshable**: The `refresh_index` tool allows mid-session cache rebuilds after branch switches or code changes, without restarting the server.
- **Data-driven discovery**: The `get_data_file_list` tool discovers what data files actually exist on disk, avoiding hard-coded assumptions about available inflow types or datasets.