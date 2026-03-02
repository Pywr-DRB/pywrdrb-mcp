"""File system utilities for the Pywr-DRB MCP server.

Provides safe file reading, path validation, regex search, and directory
traversal — all scoped to the PYWRDRB_ROOT source tree.
"""

from __future__ import annotations

import re
from pathlib import Path

from pywrdrb_mcp.config import PYWRDRB_ROOT


def validate_path(relative_path: str) -> Path:
    """Resolve a relative path within PYWRDRB_ROOT and validate it.

    Raises ValueError if the resolved path escapes the source tree.
    Raises FileNotFoundError if the file doesn't exist.
    """
    resolved = (PYWRDRB_ROOT / relative_path).resolve()
    root_resolved = PYWRDRB_ROOT.resolve()

    if not str(resolved).startswith(str(root_resolved)):
        raise ValueError(
            f"Path traversal denied: '{relative_path}' resolves outside the pywrdrb source tree."
        )

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    return resolved


def read_file(relative_path: str, start_line: int = 1, end_line: int = 0) -> str:
    """Read a file within the pywrdrb source tree with optional line bounds.

    Args:
        relative_path: Path relative to PYWRDRB_ROOT.
        start_line: First line to include (1-indexed, default 1).
        end_line: Last line to include (0 = read to end).

    Returns:
        File contents with line numbers prefixed.
    """
    filepath = validate_path(relative_path)
    lines = filepath.read_text(encoding="utf-8").splitlines()

    start_idx = max(0, start_line - 1)
    end_idx = end_line if end_line > 0 else len(lines)
    selected = lines[start_idx:end_idx]

    numbered = []
    for i, line in enumerate(selected, start=start_idx + 1):
        numbered.append(f"{i:>5} | {line}")

    return "\n".join(numbered)


def search_files(
    query: str,
    file_pattern: str = "*.py",
    max_results: int = 20,
    root: Path | None = None,
) -> list[dict]:
    """Regex search across files in the pywrdrb source tree.

    Args:
        query: Regular expression pattern.
        file_pattern: Glob pattern for file filtering (default: *.py).
        max_results: Maximum number of matches to return.
        root: Search root directory (default: PYWRDRB_ROOT).

    Returns:
        List of dicts with keys: file, line, content, match.
    """
    search_root = root or PYWRDRB_ROOT
    pattern = re.compile(query, re.IGNORECASE)
    results = []

    for filepath in sorted(search_root.rglob(file_pattern)):
        if not filepath.is_file():
            continue
        # Skip __pycache__ and hidden directories
        if any(part.startswith(("__pycache__", ".")) for part in filepath.parts):
            continue

        try:
            text = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                rel = filepath.relative_to(PYWRDRB_ROOT)
                results.append({
                    "file": str(rel).replace("\\", "/"),
                    "line": lineno,
                    "content": line.strip(),
                    "match": m.group(),
                })
                if len(results) >= max_results:
                    return results

    return results


def get_package_structure(root: Path | None = None) -> dict[str, str | None]:
    """Walk the pywrdrb package and build a map of {relative_path: module_docstring}.

    Returns a dict where keys are relative file paths (forward-slash separated)
    and values are the module docstring (or None).
    """
    from pywrdrb_mcp.index.ast_utils import extract_module_docstring

    search_root = root or PYWRDRB_ROOT
    structure: dict[str, str | None] = {}

    for filepath in sorted(search_root.rglob("*.py")):
        if any(part.startswith(("__pycache__", ".")) for part in filepath.parts):
            continue
        rel = str(filepath.relative_to(PYWRDRB_ROOT)).replace("\\", "/")
        try:
            docstring = extract_module_docstring(filepath)
        except Exception:
            docstring = None
        structure[rel] = docstring

    return structure


def get_data_directory_listing(subdir: str = "") -> list[dict]:
    """List data files under pywrdrb/data/ (or a subdirectory).

    Returns list of dicts with keys: path, size_bytes, modified.
    """
    import os
    from datetime import datetime, timezone

    data_root = PYWRDRB_ROOT / "data"
    if subdir:
        data_root = data_root / subdir

    if not data_root.exists():
        return []

    results = []
    for filepath in sorted(data_root.rglob("*")):
        if not filepath.is_file():
            continue
        if any(part.startswith(("__pycache__", ".")) for part in filepath.parts):
            continue

        stat = filepath.stat()
        rel = str(filepath.relative_to(PYWRDRB_ROOT / "data")).replace("\\", "/")
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        results.append({
            "path": rel,
            "size_bytes": stat.st_size,
            "modified": mtime,
        })

    return results
