"""Pywr-DRB MCP Server entry point.

Run with:  uv run python -m pywrdrb_mcp.server
"""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from pywrdrb_mcp.index.builder import PywrDRBIndex

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

mcp = FastMCP(
    "pywrdrb-mcp",
    instructions=(
        "This server provides tools, resources, and prompts for working with "
        "the Pywr-DRB Delaware River Basin water resource simulation model. "
        "Use tools for dynamic queries (topology lookups, code search, class info). "
        "Use resources for pre-computed reference data (network graph, constant tables, "
        "operational rule summaries). Use prompts for guided multi-step workflows."
    ),
)

_index_instance: PywrDRBIndex | None = None


# Build the index once at startup
def _get_index() -> PywrDRBIndex:
    global _index_instance
    if _index_instance is None:
        _index_instance = PywrDRBIndex()
    return _index_instance


index = _get_index()

# When run as `python -m pywrdrb_mcp.server`, this module is loaded as
# __main__.  Sub-modules (tools, resources, prompts) import from
# `pywrdrb_mcp.server`, which would create a *second* module object with its
# own mcp/index.  Register __main__ under the canonical name so every import
# resolves to the same objects.
if __name__ == "__main__":
    sys.modules.setdefault("pywrdrb_mcp.server", sys.modules[__name__])

# Import and register tools, resources, prompts.
# Each sub-module registers its functions on the `mcp` instance.
from pywrdrb_mcp.tools import topology, code, parameters, model_builder, data, lists, data_object, ffmp_data  # noqa: E402, F401
from pywrdrb_mcp.resources import static  # noqa: E402, F401
from pywrdrb_mcp.prompts import templates  # noqa: E402, F401


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()