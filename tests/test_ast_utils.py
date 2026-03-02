"""Tests for AST parsing utilities against actual pywrdrb source files."""

import pytest
from pathlib import Path

from pywrdrb_mcp.config import PYWRDRB_ROOT
from pywrdrb_mcp.index.ast_utils import (
    extract_module_level_dict,
    extract_module_level_list,
    extract_module_level_value,
    extract_class_info,
    extract_function_info,
    extract_method_source,
    extract_dataclass_fields,
    extract_module_docstring,
    _MISSING,
)


# ── Dict extraction ──────────────────────────────────────────────────

class TestExtractDict:
    def test_upstream_nodes_dict(self):
        filepath = PYWRDRB_ROOT / "pywr_drb_node_data.py"
        result = extract_module_level_dict(filepath, "upstream_nodes_dict")
        assert result is not None
        assert isinstance(result, dict)
        assert "delMontague" in result
        assert isinstance(result["delMontague"], list)

    def test_downstream_node_lags(self):
        filepath = PYWRDRB_ROOT / "pywr_drb_node_data.py"
        result = extract_module_level_dict(filepath, "downstream_node_lags")
        assert result is not None
        assert isinstance(result, dict)
        # Lags should be integers
        for v in result.values():
            assert isinstance(v, int)

    def test_flood_stage_thresholds(self):
        filepath = PYWRDRB_ROOT / "flood_thresholds.py"
        result = extract_module_level_dict(filepath, "flood_stage_thresholds")
        assert result is not None
        assert "01426500" in result
        assert "action" in result["01426500"]

    def test_storage_curves_returns_none(self):
        """storage_curves uses f-strings — should return None."""
        filepath = PYWRDRB_ROOT / "pywr_drb_node_data.py"
        result = extract_module_level_dict(filepath, "storage_curves")
        assert result is None

    def test_results_set_descriptions(self):
        filepath = PYWRDRB_ROOT / "utils" / "results_sets.py"
        result = extract_module_level_dict(filepath, "pywrdrb_results_set_descriptions")
        assert result is not None
        assert "major_flow" in result

    def test_nonexistent_variable(self):
        filepath = PYWRDRB_ROOT / "pywr_drb_node_data.py"
        result = extract_module_level_dict(filepath, "nonexistent_var_xyz")
        assert result is None


# ── List extraction ──────────────────────────────────────────────────

class TestExtractList:
    def test_reservoir_list(self):
        filepath = PYWRDRB_ROOT / "utils" / "lists.py"
        result = extract_module_level_list(filepath, "reservoir_list")
        assert result is not None
        assert len(result) == 17
        assert result[0] == "cannonsville"
        assert result[1] == "pepacton"
        assert result[2] == "neversink"

    def test_flood_monitoring_nodes(self):
        filepath = PYWRDRB_ROOT / "utils" / "lists.py"
        result = extract_module_level_list(filepath, "flood_monitoring_nodes")
        assert result is not None
        assert len(result) == 3
        assert "01426500" in result

    def test_derived_list_returns_none(self):
        """reservoir_list_nyc is a slice — should return None."""
        filepath = PYWRDRB_ROOT / "utils" / "lists.py"
        result = extract_module_level_list(filepath, "reservoir_list_nyc")
        assert result is None


# ── Value extraction ─────────────────────────────────────────────────

class TestExtractValue:
    def test_literal_constant(self):
        filepath = PYWRDRB_ROOT / "utils" / "constants.py"
        result = extract_module_level_value(filepath, "cfs_to_mgd")
        assert result is not _MISSING
        assert abs(result - 0.645932368556) < 1e-10

    def test_arithmetic_returns_missing(self):
        filepath = PYWRDRB_ROOT / "utils" / "constants.py"
        result = extract_module_level_value(filepath, "cm_to_mg")
        assert result is _MISSING


# ── Class extraction ─────────────────────────────────────────────────

class TestExtractClassInfo:
    def test_options_dataclass(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        result = extract_class_info(filepath, class_name="Options")
        assert len(result) == 1
        cls = result[0]
        assert cls["name"] == "Options"
        assert cls["docstring"] is not None

    def test_model_builder_class(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        result = extract_class_info(filepath, class_name="ModelBuilder")
        assert len(result) == 1
        cls = result[0]
        assert cls["name"] == "ModelBuilder"
        assert len(cls["methods"]) > 20

    def test_starfit_class(self):
        filepath = PYWRDRB_ROOT / "parameters" / "starfit.py"
        result = extract_class_info(filepath, class_name="STARFITReservoirRelease")
        assert len(result) == 1
        cls = result[0]
        assert "Parameter" in cls["bases"][0] or "parameter" in cls["bases"][0].lower()
        assert cls["docstring"] is not None

    def test_fallback_docstring_from_init(self):
        """water_temperature.py classes have docstrings in __init__, not class body."""
        filepath = PYWRDRB_ROOT / "parameters" / "water_temperature.py"
        result = extract_class_info(filepath)
        # At least one class should have a docstring from __init__ fallback
        has_docstring = any(c["docstring"] is not None for c in result)
        assert has_docstring, "Expected at least one class with docstring via __init__ fallback"

    def test_all_classes_in_file(self):
        filepath = PYWRDRB_ROOT / "parameters" / "ffmp.py"
        result = extract_class_info(filepath)
        assert len(result) >= 8
        names = {c["name"] for c in result}
        assert "FfmpNycRunningAvgParameter" in names
        assert "NYCCombinedReleaseFactor" in names


# ── Method source extraction ─────────────────────────────────────────

class TestExtractMethodSource:
    def test_make_model(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        source = extract_method_source(filepath, "ModelBuilder", "make_model")
        assert source is not None
        assert "def make_model" in source

    def test_nonexistent_method(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        source = extract_method_source(filepath, "ModelBuilder", "nonexistent_xyz")
        assert source is None


# ── Dataclass field extraction ───────────────────────────────────────

class TestExtractDataclassFields:
    def test_options_fields(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        fields = extract_dataclass_fields(filepath, "Options")
        assert fields is not None
        assert len(fields) >= 10
        names = {f["name"] for f in fields}
        assert "NSCENARIOS" in names
        assert "inflow_ensemble_indices" in names
        assert "flow_prediction_mode" in names

    def test_non_dataclass_returns_none(self):
        filepath = PYWRDRB_ROOT / "model_builder.py"
        result = extract_dataclass_fields(filepath, "ModelBuilder")
        assert result is None


# ── Module docstring ─────────────────────────────────────────────────

class TestExtractModuleDocstring:
    def test_lists_module(self):
        filepath = PYWRDRB_ROOT / "utils" / "lists.py"
        result = extract_module_docstring(filepath)
        assert result is not None
        assert "lists" in result.lower()
