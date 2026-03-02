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

### Tools (11)

| Tool | Purpose |
|---|---|
| `get_node_topology` | River network connections, lags, and gage IDs for a node |
| `get_reservoir_details` | Reservoir type, classification, and data source mappings |
| `get_file_contents` | Read any file in the pywrdrb source tree |
| `search_codebase` | Regex search across all source files |
| `get_module_overview` | Module docstring, classes, and functions summary |
| `get_parameter_class_info` | Full class details (methods, signatures, docstrings) |
| `get_model_builder_options` | Options dataclass fields with types and defaults |
| `get_model_builder_method` | Source code for any ModelBuilder method |
| `get_operational_constants` | Unit conversion constants |
| `get_repo_status` | Git branch, recent commits, modified files |
| `get_data_file_list` | Enumerate data files on disk |
| `refresh_index` | Rebuild the cached index without restarting |

### Resources (16+)

- **Topology:** network graph, reservoir list, node list
- **API:** parameter class index, ModelBuilder methods, Data loader methods
- **Data:** inflow types with date ranges, results set options, constants
- **Project:** package file tree, git repo status
- **Domain knowledge:** FFMP rules, STARFIT rules, flood operations, getting started guide
- **Templates:** `pywrdrb://parameter/{class_name}`, `pywrdrb://reservoir/{reservoir_name}`

### Prompts (6)

| Prompt | Workflow |
|---|---|
| `add-new-parameter` | Pattern for creating a custom Pywr Parameter |
| `debug-simulation` | Step-by-step simulation diagnostics |
| `understand-node` | Gather all info about a river network node |
| `modify-ffmp-rules` | Change FFMP rules via NYCOperationsConfig |
| `add-inflow-source` | Add a new hydrologic model inflow dataset |
| `review-model-output` | Load and interpret simulation results |

## Architecture

```
pywrdrb-mcp/
├── src/pywrdrb_mcp/
│   ├── server.py          # FastMCP entry point
│   ├── config.py          # PYWRDRB_ROOT path
│   ├── index/             # AST-based static analysis engine
│   ├── tools/             # 11 MCP tools
│   ├── resources/         # 16+ MCP resources
│   ├── prompts/           # 6 MCP prompt templates
│   └── content/           # Hand-written domain knowledge (markdown)
└── tests/                 # 68 tests
```

The server reads from the Pywr-DRB source tree at startup via `ast.parse()` and `ast.literal_eval()` — it never imports or executes pywrdrb code.
