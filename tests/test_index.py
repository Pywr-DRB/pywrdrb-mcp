"""Tests for the PywrDRBIndex builder."""

import pytest

from pywrdrb_mcp.index.builder import PywrDRBIndex


@pytest.fixture(scope="module")
def idx():
    """Build the index once for all tests in this module."""
    return PywrDRBIndex()


class TestTopology:
    def test_upstream_nodes_populated(self, idx):
        assert len(idx.upstream_nodes) > 0
        assert "delMontague" in idx.upstream_nodes

    def test_downstream_populated(self, idx):
        assert len(idx.immediate_downstream) > 0

    def test_lags_populated(self, idx):
        assert len(idx.downstream_lags) > 0

    def test_site_matches_populated(self, idx):
        assert len(idx.obs_site_matches) > 0
        assert len(idx.nhm_site_matches) > 0
        assert len(idx.nwm_site_matches) > 0

    def test_all_node_names(self, idx):
        assert len(idx.all_node_names) > 20


class TestLists:
    def test_reservoir_list(self, idx):
        assert len(idx.reservoir_list) == 17
        assert idx.reservoir_list[0] == "cannonsville"

    def test_reservoir_list_nyc(self, idx):
        assert len(idx.reservoir_list_nyc) == 3
        assert "cannonsville" in idx.reservoir_list_nyc

    def test_starfit_reservoir_list(self, idx):
        assert len(idx.starfit_reservoir_list) == 14

    def test_independent_starfit(self, idx):
        assert len(idx.independent_starfit_reservoirs) > 0
        # Should not contain lower basin reservoirs
        for r in idx.drbc_lower_basin_reservoirs:
            assert r not in idx.independent_starfit_reservoirs

    def test_required_model_reservoirs(self, idx):
        assert len(idx.required_model_reservoirs) == 6  # 3 NYC + 3 lower basin

    def test_seasons_dict(self, idx):
        assert len(idx.seasons_dict) == 12
        assert idx.seasons_dict[1] == "DJF"
        assert idx.seasons_dict[6] == "JJA"

    def test_flood_monitoring_nodes(self, idx):
        assert len(idx.flood_monitoring_nodes) == 3


class TestConstants:
    def test_constants_populated(self, idx):
        assert len(idx.constants) >= 8
        assert "cfs_to_mgd" in idx.constants
        assert abs(idx.constants["cfs_to_mgd"] - 0.645932368556) < 1e-10

    def test_computed_constants(self, idx):
        assert "cm_to_mg" in idx.constants
        assert abs(idx.constants["cm_to_mg"] - 264.17 / 1e6) < 1e-15
        assert "GAL_TO_MG" in idx.constants


class TestFloodThresholds:
    def test_thresholds_populated(self, idx):
        assert len(idx.flood_stage_thresholds) >= 3
        assert "01426500" in idx.flood_stage_thresholds

    def test_threshold_structure(self, idx):
        t = idx.flood_stage_thresholds["01426500"]
        assert "action" in t
        assert "minor" in t
        assert "moderate" in t
        assert "major" in t


class TestParameterIndex:
    def test_parameter_index_populated(self, idx):
        assert len(idx.parameter_index) > 20

    def test_known_classes(self, idx):
        assert "STARFITReservoirRelease" in idx.parameter_index
        assert "FfmpNycRunningAvgParameter" in idx.parameter_index
        assert "FlowEnsemble" in idx.parameter_index

    def test_parameter_entry_structure(self, idx):
        entry = idx.parameter_index["STARFITReservoirRelease"]
        assert "module" in entry
        assert "name" in entry
        assert "bases" in entry
        assert entry["module"] == "parameters/starfit.py"

    def test_parameter_files_mapping(self, idx):
        assert "STARFITReservoirRelease" in idx.parameter_files
        assert idx.parameter_files["STARFITReservoirRelease"].name == "starfit.py"


class TestResultsSets:
    def test_results_set_descriptions(self, idx):
        assert len(idx.results_set_descriptions) > 10
        assert "major_flow" in idx.results_set_descriptions


class TestDateRanges:
    def test_date_ranges(self, idx):
        assert len(idx.model_date_ranges) >= 7
        assert "nhmv10" in idx.model_date_ranges
        start, end = idx.model_date_ranges["nhmv10"]
        assert start == "1983-10-01"


class TestPackageStructure:
    def test_package_structure_populated(self, idx):
        assert len(idx.package_structure) > 20

    def test_known_files(self, idx):
        assert "model_builder.py" in idx.package_structure
        assert "parameters/ffmp.py" in idx.package_structure


class TestRebuild:
    def test_rebuild_returns_summary(self, idx):
        summary = idx.rebuild()
        assert "added_parameters" in summary
        assert "removed_parameters" in summary
        assert "file_count_before" in summary
        assert "file_count_after" in summary
