"""Configuration for the Pywr-DRB MCP server."""

import os
from pathlib import Path

# Path to the pywrdrb source package, configurable via environment variable.
PYWRDRB_ROOT = Path(
    os.environ.get(
        "PYWRDRB_ROOT",
        r"C:\Users\tjame\Desktop\Research\DRB\Pywr-DRB\Pywr-DRB\src\pywrdrb",
    )
)

# Path to the Pywr-DRB git repository root (parent of src/).
PYWRDRB_REPO_ROOT = PYWRDRB_ROOT.parent.parent
