"""
Tests for all CMS facility registries.
"""

import pytest

from src.core.models import CostCenterCategory, FacilityType
from src.facilities.hha import HHARegistry
from src.facilities.hospice import HospiceRegistry
from src.facilities.hospital import HospitalRegistry
from src.facilities.registry import get_registry, list_all_cost_centers
from src.facilities.snf import SNFRegistry


class TestHospitalRegistry:
    def setup_method(self):
        self.reg = HospitalRegistry()

    def test_cost_centers_count(self):
        """Hospital should have all general + revenue + adjustment centers."""
        assert len(self.reg.cost_centers) >= 40

    def test_step_down_sequence(self):
        """Step-down should be in correct CMS order (starts with 01, ends with 15)."""
        seq = self.reg.step_down_sequence
        assert seq[0] == "01"  # Capital - Buildings
        assert seq[-1] == "15"  # Physician Services Part B
        assert len(seq) == 16

    def test_general_services_are_general(self):
        for code in self.reg.general_service_codes:
            cc = self.reg.get_cost_center(code)
            assert cc.category == CostCenterCategory.GENERAL_SERVICE

    def test_revenue_centers_are_revenue(self):
        for code in self.reg.revenue_center_codes:
            cc = self.reg.get_cost_center(code)
            assert cc.category == CostCenterCategory.REVENUE_PRODUCING

    def test_non_allowable_not_allowable(self):
        for code in self.reg.adjustment_codes:
            cc = self.reg.get_cost_center(code)
            assert cc.allowable is False

    def test_get_cost_center(self):
        cc = self.reg.get_cost_center("04")
        assert cc is not None
        assert cc.name == "Administrative & General"
        assert cc.allocation_method is not None

    def test_search_centers(self):
        results = self.reg.search_centers("pharmacy")
        assert len(results) >= 2  # Code 11 (Pharmacy) and Code 39 (Pharmacy - Outpatient)
        assert all("pharmacy" in r.name.lower() for r in results)

    def test_ccr_ranges(self):
        """Revenue centers should have CCR ranges defined."""
        cc = self.reg.get_cost_center("20")  # Routine Care
        assert cc.ccr_range_min == 0.85
        assert cc.ccr_range_max == 1.15

        cc = self.reg.get_cost_center("31")  # Lab
        assert cc.ccr_range_min == 0.25

    def test_is_revenue_center(self):
        assert self.reg.is_revenue_center("20") is True
        assert self.reg.is_revenue_center("04") is False

    def test_is_general_service(self):
        assert self.reg.is_general_service("01") is True
        assert self.reg.is_general_service("30") is False


class TestSNFRegistry:
    def setup_method(self):
        self.reg = SNFRegistry()

    def test_cost_centers(self):
        assert len(self.reg.cost_centers) >= 15

    def test_step_down_sequence(self):
        seq = self.reg.step_down_sequence
        assert seq[0] == "01"
        assert len(seq) == 9


class TestHospiceRegistry:
    def setup_method(self):
        self.reg = HospiceRegistry()

    def test_cost_centers(self):
        assert len(self.reg.cost_centers) >= 15

    def test_level_of_care_codes(self):
        """Hospice should have RHC, CHC, IRC, GIP codes."""
        names = [cc.name for cc in self.reg.cost_centers.values()]
        assert any("Routine Home Care" in n for n in names)
        assert any("Continuous Home Care" in n for n in names)
        assert any("Inpatient Respite" in n for n in names)
        assert any("General Inpatient" in n for n in names)


class TestHHARegistry:
    def setup_method(self):
        self.reg = HHARegistry()

    def test_cost_centers(self):
        assert len(self.reg.cost_centers) >= 12

    def test_disciplines(self):
        """HHA should have nursing, PT, OT, SLP, aide, social work."""
        names = [cc.name for cc in self.reg.cost_centers.values()]
        assert any("Nursing" in n for n in names)
        assert any("Physical Therapy" in n for n in names)
        assert any("Occupational Therapy" in n for n in names)
        assert any("Speech" in n for n in names)


class TestRegistryFactory:
    def test_get_registry(self):
        for ft in FacilityType:
            reg = get_registry(ft)
            assert reg.facility_type == ft
            assert len(reg.cost_centers) > 0
            assert len(reg.step_down_sequence) > 0

    def test_list_all(self):
        all_centers = list_all_cost_centers()
        assert len(all_centers) == 4  # All 4 facility types
        assert "hospital" in all_centers
        assert "snf" in all_centers
