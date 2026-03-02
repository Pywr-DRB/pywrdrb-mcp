"""Tools for querying operational constants, data files, repo status, and refreshing the index."""

from __future__ import annotations

import json
import subprocess

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.config import PYWRDRB_ROOT, PYWRDRB_REPO_ROOT
from pywrdrb_mcp.index.file_utils import get_data_directory_listing


@mcp.tool()
def get_operational_constants() -> str:
    """Get unit conversion constants and key operational values used by Pywr-DRB.

    Returns all constants from utils/constants.py (e.g., cfs_to_mgd, cms_to_mgd).
    """
    return json.dumps(index.constants, indent=2)


@mcp.tool()
def get_repo_status() -> str:
    """Get the current git status of the Pywr-DRB source repository.

    Returns the current branch, recent commit history, and modified files.
    This tells you which version of the code you're reading.
    """
    repo = str(PYWRDRB_REPO_ROOT)
    result: dict = {}

    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=repo, timeout=10,
        )
        result["branch"] = branch.stdout.strip()
    except Exception as e:
        result["branch_error"] = str(e)

    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True, cwd=repo, timeout=10,
        )
        result["recent_commits"] = log.stdout.strip().splitlines()
    except Exception as e:
        result["log_error"] = str(e)

    try:
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=repo, timeout=10,
        )
        result["modified_files"] = status.stdout.strip().splitlines() or ["(clean)"]
    except Exception as e:
        result["status_error"] = str(e)

    return json.dumps(result, indent=2)


@mcp.tool()
def get_data_file_list(data_subdir: str = "") -> str:
    """List data files available in the pywrdrb/data/ directory.

    Discovers which inflow types, observation files, rating curves, and
    operational constants are actually present on disk.

    Args:
        data_subdir: Subdirectory to list (e.g., 'flows', 'observations', 'rating_curves').
                     Empty string lists top-level data files and subdirectory summaries.
    """
    files = get_data_directory_listing(data_subdir)
    if not files:
        path_desc = f"data/{data_subdir}" if data_subdir else "data/"
        return f"No files found in {path_desc}."

    # Summarize by subdirectory if listing top level
    if not data_subdir:
        subdirs: dict[str, int] = {}
        for f in files:
            parts = f["path"].split("/")
            top = parts[0] if len(parts) > 1 else "(root)"
            subdirs[top] = subdirs.get(top, 0) + 1

        lines = [f"Data directory summary ({len(files)} total files):\n"]
        for sd, count in sorted(subdirs.items()):
            lines.append(f"  {sd}/  ({count} files)")
        lines.append("\nUse data_subdir parameter to explore subdirectories.")
        return "\n".join(lines)

    # Detailed listing for subdirectory
    lines = [f"Files in data/{data_subdir}/ ({len(files)} files):\n"]
    for f in files:
        size_kb = f["size_bytes"] / 1024
        if size_kb > 1024:
            size_str = f"{size_kb/1024:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"
        lines.append(f"  {f['path']}  ({size_str})")

    return "\n".join(lines)


@mcp.tool()
def refresh_index() -> str:
    """Rebuild the PywrDRBIndex cache without restarting the server.

    Useful after switching branches, pulling changes, or modifying data files.
    Returns a summary of what changed.
    """
    summary = index.rebuild()
    lines = ["Index refreshed successfully.\n"]

    if summary["added_parameters"]:
        lines.append(f"New parameter classes: {', '.join(summary['added_parameters'])}")
    if summary["removed_parameters"]:
        lines.append(f"Removed parameter classes: {', '.join(summary['removed_parameters'])}")

    lines.append(f"Source files: {summary['file_count_before']} → {summary['file_count_after']}")

    if not summary["added_parameters"] and not summary["removed_parameters"]:
        lines.append("No changes detected in parameter classes.")

    return "\n".join(lines)
