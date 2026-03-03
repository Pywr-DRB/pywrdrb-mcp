# pywrdrb-mcp

MCP server that gives LLMs efficient access to the [Pywr-DRB](https://github.com/Pywr-DRB/Pywr-DRB) water resource model codebase. Uses static analysis (Python `ast`) to extract structure and data from source files without importing pywrdrb or its heavy dependencies.

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- Pywr-DRB source code at `Pywr-DRB\Pywr-DRB\src\pywrdrb\` (sibling directory)

### Run the server

```bash
uv run python -m pywrdrb_mcp.server
```

### Register with Claude Code

**CLI:**
```bash
claude mcp add --transport stdio pywrdrb-mcp -- uv run --directory "C:/Users/tjame/Desktop/Research/DRB/Pywr-DRB/pywrdrb-mcp" python -m pywrdrb_mcp.server
```

**VS Code extension (manual):**

Add to your Claude Code MCP settings (`.claude/settings.json` or project-level):
```json
{
  "mcpServers": {
    "pywrdrb-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory", "C:/Users/tjame/Desktop/Research/DRB/Pywr-DRB/pywrdrb-mcp",
        "python", "-m", "pywrdrb_mcp.server"
      ]
    }
  }
}
```

### Run tests

```bash
uv run pytest tests/ -v
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `PYWRDRB_ROOT` | `C:\Users\tjame\...\Pywr-DRB\src\pywrdrb` | Path to the pywrdrb source package |

## What's Included

### Tools (19)

| Tool | Module | Purpose |
|---|---|---|
| `get_node_topology` | topology | River network connections, lags, and gage IDs for a node |
| `get_reservoir_details` | topology | Reservoir type, classification, and data source mappings |
| `get_file_contents` | code | Read any file in the pywrdrb source tree |
| `search_codebase` | code | Regex search across all source files |
| `get_module_overview` | code | Module docstring, classes, and functions summary |
| `get_parameter_class_info` | parameters | Full class details (methods, signatures, docstrings) |
| `get_model_builder_options` | model_builder | Options dataclass fields with types and defaults |
| `get_model_builder_method` | model_builder | Source code for any ModelBuilder method |
| `get_operational_constants` | data | Unit conversion constants |
| `get_repo_status` | data | Git branch, recent commits, modified files |
| `get_data_file_list` | data | Enumerate data files on disk |
| `refresh_index` | data | Rebuild the cached index without restarting |
| `get_node_list` | lists | All nodes by type (NYC, STARFIT, flood, etc.) |
| `get_reservoir_list` | lists | All 17 reservoirs with type classifications |
| `get_parameter_list` | lists | All parameter classes grouped by module |
| `get_results_set_list` | lists | Available results set options for loading output |
| `get_inflow_type_list` | lists | Available inflow data types with date ranges |
| `get_data_object_info` | data_object | Data class hierarchy, access patterns, loading methods |
| `get_ffmp_data` | ffmp_data | FFMP operational constants, profiles, and lower basin policy |

### Resources (15)

- **Topology:** network graph, reservoir list, node list
- **API:** parameter class index, ModelBuilder methods, Data loader methods
- **Data:** inflow types with date ranges, results set options, constants
- **Project:** package file tree, git repo status
- **Domain knowledge:** FFMP rules, STARFIT rules, flood operations, getting started guide
- **Templates:** `pywrdrb://parameter/{class_name}`, `pywrdrb://reservoir/{reservoir_name}`

### Prompts (6)

All prompts use the `how_to_*` naming convention to indicate they are instructional guides.

| Prompt | Workflow |
|---|---|
| `how_to_add_parameter` | Pattern for creating a custom Pywr Parameter |
| `how_to_debug_simulation` | Step-by-step simulation diagnostics |
| `how_to_understand_node` | Gather all info about a river network node |
| `how_to_modify_ffmp_rules` | Change FFMP rules via NYCOperationsConfig |
| `how_to_add_inflow_source` | Add a new hydrologic model inflow dataset |
| `how_to_review_output` | Load and interpret simulation results |

### Examples

See the `examples/` directory for usage guides:

- `01_exploring_the_network.md` — Node topology, reservoir details, network graph
- `02_working_with_parameters.md` — Listing, inspecting, and adding parameter classes
- `03_ffmp_operations.md` — FFMP data queries, rules, and scenario modification
- `04_simulation_results.md` — Data class, results sets, loading output
- `05_building_models.md` — ModelBuilder options, inflow sources, debugging

## Architecture

```
pywrdrb-mcp/
├── src/pywrdrb_mcp/
│   ├── server.py          # FastMCP entry point
│   ├── config.py          # PYWRDRB_ROOT path
│   ├── index/             # AST-based static analysis engine
│   ├── tools/             # 19 MCP tools (8 modules)
│   ├── resources/         # 15 MCP resources
│   ├── prompts/           # 6 MCP prompt templates (how_to_* convention)
│   └── content/           # Hand-written domain knowledge (markdown)
├── examples/              # Usage guides and workflow examples
└── tests/
```

The server reads from the Pywr-DRB source tree at startup via `ast.parse()` and `ast.literal_eval()` — it never imports or executes pywrdrb code.
