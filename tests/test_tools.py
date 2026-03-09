"""Tests for MCP tool functions."""

import json
import pytest

from pywrdrb_mcp.index.builder import PywrDRBIndex

# We need the index to exist before importing tools
import pywrdrb_mcp.server  # triggers index build

from pywrdrb_mcp.tools.topology import get_node_topology, get_reservoir_details
from pywrdrb_mcp.tools.code import get_file_contents, search_codebase, get_module_overview
from pywrdrb_mcp.tools.parameters import get_parameter_class_info
from pywrdrb_mcp.tools.model_builder import get_model_builder_options, get_model_builder_method
from pywrdrb_mcp.tools.data import (
    get_repo_status,
    get_data_file_list,
    refresh_index,
)


class TestTopologyTools:
    def test_get_node_topology_known_node(self):
        result = json.loads(get_node_topology("delMontague"))
        assert result["node"] == "delMontague"
        assert "upstream_nodes" in result
        assert isinstance(result["upstream_nodes"], list)

    def test_get_node_topology_case_insensitive(self):
        result = json.loads(get_node_topology("delmontague"))
        assert result["node"] == "delMontague"

    def test_get_node_topology_unknown_node(self):
        result = json.loads(get_node_topology("nonexistent_node"))
        assert "error" in result
        assert "available_nodes" in result

    def test_get_node_topology_with_flood(self):
        result = json.loads(get_node_topology("01426500", include_flood_topology=True))
        assert result["is_flood_monitoring_node"] is True

    def test_get_reservoir_details_nyc(self):
        result = json.loads(get_reservoir_details("cannonsville"))
        assert result["type"] == "NYC"
        assert "nyc" in result["classifications"]

    def test_get_reservoir_details_starfit(self):
        result = json.loads(get_reservoir_details("blueMarsh"))
        assert "starfit" in result["classifications"]
        assert "drbc_lower_basin" in result["classifications"]

    def test_get_reservoir_details_unknown(self):
        result = json.loads(get_reservoir_details("nonexistent"))
        assert "error" in result

    def test_get_reservoir_details_has_capacity(self):
        result = json.loads(get_reservoir_details("cannonsville"))
        assert "capacity_mg" in result
        assert result["capacity_mg"] is not None
        assert result["capacity_mg"] > 0

    def test_get_reservoir_details_starfit_params(self):
        result = json.loads(get_reservoir_details("cannonsville"))
        assert "starfit_params" in result
        assert "Release_c" in result["starfit_params"]


class TestCodeTools:
    def test_get_file_contents(self):
        result = get_file_contents("utils/lists.py", start_line=1, end_line=5)
        assert "lists" in result.lower() or "|" in result

    def test_get_file_contents_invalid_path(self):
        result = get_file_contents("../../etc/passwd")
        assert "Error" in result

    def test_search_codebase(self):
        result = search_codebase("class ModelBuilder")
        assert "ModelBuilder" in result
        assert "model_builder.py" in result

    def test_search_codebase_no_results(self):
        result = search_codebase("zzz_impossible_pattern_xyz_123")
        assert "No matches" in result

    def test_get_module_overview(self):
        result = get_module_overview("parameters/starfit.py")
        assert "STARFITReservoirRelease" in result
        assert "Module:" in result


class TestParameterTools:
    def test_get_parameter_class_info_known(self):
        result = json.loads(get_parameter_class_info("STARFITReservoirRelease"))
        assert result["name"] == "STARFITReservoirRelease"
        assert "methods" in result
        assert len(result["methods"]) > 5

    def test_get_parameter_class_info_unknown(self):
        result = json.loads(get_parameter_class_info("NonexistentClass"))
        assert "error" in result
        assert "available_classes" in result


class TestModelBuilderTools:
    def test_get_model_builder_options(self):
        result = get_model_builder_options()
        assert "NSCENARIOS" in result
        assert "flow_prediction_mode" in result

    def test_get_model_builder_method_known(self):
        result = get_model_builder_method("make_model")
        assert "def make_model" in result

    def test_get_model_builder_method_unknown(self):
        result = get_model_builder_method("nonexistent_method")
        assert "error" in result.lower() or "not found" in result.lower()


class TestDataTools:
    def test_get_repo_status(self):
        result = json.loads(get_repo_status())
        assert "branch" in result or "branch_error" in result

    def test_get_data_file_list_summary(self):
        result = get_data_file_list()
        assert "files" in result.lower() or "summary" in result.lower()

    def test_get_data_file_list_subdir(self):
        result = get_data_file_list("observations")
        assert "files" in result.lower()

    def test_refresh_index(self):
        result = refresh_index()
        assert "refreshed" in result.lower() or "Index" in result
