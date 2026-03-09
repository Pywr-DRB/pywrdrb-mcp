"""AST-based static extraction utilities for parsing Pywr-DRB source files.

These functions use Python's ast module to extract structured information from
source files WITHOUT importing or executing them. This is critical because
pywrdrb has heavy dependencies (pywr, torch, mpi4py) that we don't want to
require in the MCP server.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Any


def extract_module_level_dict(filepath: Path, variable_name: str) -> dict | None:
    """Extract a module-level dictionary literal by variable name.

    Only works for pure literal dicts (no f-strings, function calls, or
    variable references). Returns None if the variable isn't found or
    isn't a literal.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    segment = ast.get_source_segment(source, node.value)
                    if segment is None:
                        return None
                    try:
                        return ast.literal_eval(segment)
                    except (ValueError, SyntaxError):
                        return None
    return None


def extract_module_level_list(filepath: Path, variable_name: str) -> list | None:
    """Extract a module-level list literal by variable name.

    Only works for pure literal lists. Returns None if not found or not a literal.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    segment = ast.get_source_segment(source, node.value)
                    if segment is None:
                        return None
                    try:
                        return ast.literal_eval(segment)
                    except (ValueError, SyntaxError):
                        return None
    return None


def extract_module_level_value(filepath: Path, variable_name: str) -> Any:
    """Extract any module-level literal value (int, float, str, etc.).

    Returns a sentinel _MISSING if not found or not a literal.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    segment = ast.get_source_segment(source, node.value)
                    if segment is None:
                        return _MISSING
                    try:
                        return ast.literal_eval(segment)
                    except (ValueError, SyntaxError):
                        return _MISSING
    return _MISSING


class _MissingSentinel:
    """Sentinel for missing values (distinct from None)."""
    def __bool__(self):
        return False
    def __repr__(self):
        return "<MISSING>"

_MISSING = _MissingSentinel()


def extract_class_info(filepath: Path, class_name: str | None = None) -> list[dict]:
    """Extract class definitions from a Python source file via AST.

    Returns a list of dicts, each with keys:
        name, bases, docstring, methods, module_path

    If class_name is given, only that class is returned.
    Falls back to checking __init__ for docstrings when the class-level
    docstring is missing (handles water_temperature.py / salt_front_location.py pattern).
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if class_name and node.name != class_name:
            continue

        # Extract base class names as readable strings
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(ast.unparse(b))
            else:
                bases.append(ast.unparse(b))

        docstring = ast.get_docstring(node)

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_doc = ast.get_docstring(item)
                # Fallback: if class docstring is missing and this is __init__,
                # use __init__'s docstring as the class docstring
                if docstring is None and item.name == "__init__" and method_doc:
                    docstring = method_doc

                args = []
                for a in item.args.args:
                    arg_info = {"name": a.arg}
                    if a.annotation:
                        arg_info["annotation"] = ast.unparse(a.annotation)
                    args.append(arg_info)

                methods.append({
                    "name": item.name,
                    "args": args,
                    "docstring": method_doc,
                    "lineno": item.lineno,
                })

        info = {
            "name": node.name,
            "bases": bases,
            "docstring": docstring,
            "methods": methods,
            "lineno": node.lineno,
        }
        results.append(info)

    return results


def extract_function_info(filepath: Path) -> list[dict]:
    """Extract top-level function definitions (not methods) from a source file.

    Returns list of dicts with keys: name, args, docstring, lineno.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    results = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = []
            for a in node.args.args:
                arg_info = {"name": a.arg}
                if a.annotation:
                    arg_info["annotation"] = ast.unparse(a.annotation)
                args.append(arg_info)

            results.append({
                "name": node.name,
                "args": args,
                "docstring": ast.get_docstring(node),
                "lineno": node.lineno,
            })

    return results


def extract_method_source(filepath: Path, class_name: str, method_name: str) -> str | None:
    """Extract the raw source code for a specific method within a class.

    Returns the source text with original indentation, or None if not found.
    """
    source = filepath.read_text(encoding="utf-8")
    source_lines = source.splitlines(keepends=True)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        start = item.lineno - 1  # 0-indexed
                        end = item.end_lineno  # end_lineno is 1-indexed inclusive
                        if end is None:
                            # Fallback: scan for next def or end of class
                            end = len(source_lines)
                        return "".join(source_lines[start:end])

    return None


def extract_dataclass_fields(filepath: Path, class_name: str) -> list[dict] | None:
    """Extract fields from a @dataclass class definition.

    Returns list of dicts with keys: name, type, default, description.
    The description is parsed from the class docstring if it follows
    the 'Attributes:' section convention.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue

        # Check for @dataclass decorator
        is_dataclass = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id == "dataclass":
                is_dataclass = True
            elif isinstance(dec, ast.Attribute) and dec.attr == "dataclass":
                is_dataclass = True
        if not is_dataclass:
            return None

        # Parse docstring for field descriptions
        docstring = ast.get_docstring(node) or ""
        field_descriptions = _parse_attributes_section(docstring)

        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = ast.unparse(item.annotation) if item.annotation else "Any"

                # Extract default value
                default = None
                if item.value is not None:
                    segment = ast.get_source_segment(source, item.value)
                    if segment:
                        default = segment

                fields.append({
                    "name": field_name,
                    "type": field_type,
                    "default": default,
                    "description": field_descriptions.get(field_name, ""),
                })

        return fields

    return None


def extract_module_docstring(filepath: Path) -> str | None:
    """Extract the module-level docstring from a Python file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    return ast.get_docstring(tree)


def _parse_attributes_section(docstring: str) -> dict[str, str]:
    """Parse an 'Attributes:' section from a docstring.

    Returns a dict mapping attribute names to their descriptions.
    Handles both Google-style and numpy-style attribute docs.
    """
    descriptions: dict[str, str] = {}
    if not docstring:
        return descriptions

    lines = textwrap.dedent(docstring).splitlines()
    in_attributes = False
    current_name = None
    current_desc_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Detect the start of an Attributes section
        if stripped.lower() in ("attributes:", "args:", "fields:"):
            in_attributes = True
            continue

        # End of section: another section header or empty after content
        if in_attributes and stripped and not stripped.startswith(" ") and ":" not in stripped:
            # Could be a new section header
            if stripped.endswith(":") or stripped[0].isupper():
                # Save current field
                if current_name:
                    descriptions[current_name] = " ".join(current_desc_lines).strip()
                in_attributes = False
                continue

        if not in_attributes:
            continue

        if not stripped:
            continue

        # Try to match "field_name (type): description" or "field_name: description"
        if ":" in stripped and not stripped.startswith(" "):
            # Save previous field
            if current_name:
                descriptions[current_name] = " ".join(current_desc_lines).strip()

            parts = stripped.split(":", 1)
            name_part = parts[0].strip()
            # Remove type annotation in parentheses
            if "(" in name_part:
                name_part = name_part.split("(")[0].strip()
            current_name = name_part
            current_desc_lines = [parts[1].strip()] if len(parts) > 1 else []
        elif current_name:
            current_desc_lines.append(stripped)

    # Save last field
    if current_name:
        descriptions[current_name] = " ".join(current_desc_lines).strip()

    return descriptions


def extract_dict_from_simple_script(filepath: Path, variable_name: str) -> dict | None:
    """Extract a dict built procedurally from a simple script (e.g., for-loops + assignments).

    Unlike extract_module_level_dict, this handles scripts where a dict is built
    incrementally (e.g., ``d = {}; d["key"] = val``). It first verifies via AST
    that the file contains no imports or dangerous constructs, then executes the
    pure-literal code in a restricted namespace.

    Returns None if the file contains imports or the variable is not a dict.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Safety check: reject files with imports, function calls to external modules,
    # or any construct beyond assignments, for-loops, and literals
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return None
        # Allow: Assign, AugAssign, For, Expr (docstrings), Module, Constant,
        #        Dict, List, Tuple, Name, Subscript, Index, BinOp, UnaryOp,
        #        Compare, JoinedStr, FormattedValue, Call (only to builtins)
        if isinstance(node, ast.Call):
            # Only allow calls to known safe builtins
            if isinstance(node.func, ast.Name) and node.func.id in (
                "range", "len", "str", "int", "float", "list", "dict", "tuple", "set",
            ):
                continue
            return None

    namespace: dict[str, Any] = {}
    try:
        exec(compile(tree, str(filepath), "exec"), {"__builtins__": {}}, namespace)  # noqa: S102
    except Exception:
        return None

    result = namespace.get(variable_name)
    if isinstance(result, dict):
        return result
    return None
