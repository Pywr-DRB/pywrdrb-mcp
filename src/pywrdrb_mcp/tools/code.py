"""Tools for searching and reading the Pywr-DRB source code."""

from __future__ import annotations

import json

from pywrdrb_mcp.server import mcp, index
from pywrdrb_mcp.index.ast_utils import (
    extract_class_info,
    extract_function_info,
    extract_module_docstring,
)
from pywrdrb_mcp.index.file_utils import read_file, search_files, validate_path
from pywrdrb_mcp.config import PYWRDRB_ROOT


@mcp.tool()
def get_file_contents(
    relative_path: str,
    start_line: int = 1,
    end_line: int = 0,
) -> str:
    """Read a file from the Pywr-DRB source tree with optional line range.

    Path must be relative to the pywrdrb package root (e.g., 'model_builder.py',
    'parameters/ffmp.py', 'utils/lists.py').

    Args:
        relative_path: Path relative to pywrdrb source root.
        start_line: First line to return (1-indexed, default 1).
        end_line: Last line to return (0 = read to end).
    """
    try:
        return read_file(relative_path, start_line, end_line)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"


@mcp.tool()
def search_codebase(
    query: str,
    file_pattern: str = "*.py",
    max_results: int = 20,
) -> str:
    """Regex search across the Pywr-DRB source code.

    Returns matching lines with file paths and line numbers.

    Args:
        query: Regular expression pattern to search for.
        file_pattern: Glob pattern for file filtering (default: '*.py').
        max_results: Maximum matches to return (default: 20).
    """
    results = search_files(query, file_pattern, max_results)
    if not results:
        return f"No matches found for pattern '{query}' in {file_pattern} files."

    output_lines = [f"Found {len(results)} match(es) for '{query}':\n"]
    for r in results:
        output_lines.append(f"  {r['file']}:{r['line']}  {r['content']}")

    if len(results) == max_results:
        output_lines.append(f"\n(Showing first {max_results} results — increase max_results for more)")

    return "\n".join(output_lines)


@mcp.tool()
def get_module_overview(module_path: str) -> str:
    """Get an overview of a pywrdrb module: docstring, classes, and functions.

    Args:
        module_path: Relative path to the .py file (e.g., 'parameters/ffmp.py', 'model_builder.py').
    """
    try:
        filepath = validate_path(module_path)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"

    docstring = extract_module_docstring(filepath) or "(No module docstring)"
    classes = extract_class_info(filepath)
    functions = extract_function_info(filepath)

    lines = [
        f"## Module: {module_path}\n",
        f"**Docstring:** {docstring}\n",
    ]

    if classes:
        lines.append(f"### Classes ({len(classes)}):\n")
        for cls in classes:
            bases_str = ", ".join(cls["bases"]) if cls["bases"] else ""
            doc_summary = _first_line(cls["docstring"])
            lines.append(f"- **{cls['name']}**({bases_str}) — {doc_summary}")
            for m in cls["methods"]:
                if m["name"].startswith("_") and m["name"] != "__init__":
                    continue
                m_doc = _first_line(m.get("docstring"))
                lines.append(f"    - `{m['name']}()` — {m_doc}")
        lines.append("")

    if functions:
        lines.append(f"### Functions ({len(functions)}):\n")
        for fn in functions:
            doc_summary = _first_line(fn["docstring"])
            lines.append(f"- **{fn['name']}()** — {doc_summary}")

    return "\n".join(lines)


def _first_line(text: str | None) -> str:
    """Extract the first sentence/line from a docstring."""
    if not text:
        return "(no description)"
    first = text.strip().split("\n")[0].strip()
    return first[:200] if len(first) > 200 else first
