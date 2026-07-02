"""
Base facility registry module.

Each facility type (hospital, SNF, hospice, HHA) extends BaseFacilityRegistry
to provide its own CMS cost center definitions, worksheet structures,
step-down sequence, and allocation method defaults.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.core.models import (
    AllocationMethod,
    CostCenterCategory,
    CostCenterDefinition,
    FacilityType,
)


class BaseFacilityRegistry(ABC):
    """Abstract base for all CMS facility type registries."""

    facility_type: FacilityType
    form_number: str
    form_title: str
    cms_chapter: str
    description: str

    @property
    @abstractmethod
    def cost_centers(self) -> dict[str, CostCenterDefinition]:
        """Return all cost centers keyed by CMS code (e.g., '01', '20')."""
        ...

    @property
    @abstractmethod
    def step_down_sequence(self) -> list[str]:
        """Return the CMS-mandated order of cost center codes for step-down allocation."""
        ...

    @property
    @abstractmethod
    def revenue_center_codes(self) -> list[str]:
        """Return cost center codes that are revenue-producing centers."""
        ...

    @property
    @abstractmethod
    def general_service_codes(self) -> list[str]:
        """Return cost center codes that are general service (overhead) centers."""
        ...

    def get_cost_center(self, code: str) -> Optional[CostCenterDefinition]:
        """Look up a cost center by its CMS code."""
        return self.cost_centers.get(code)

    def is_revenue_center(self, code: str) -> bool:
        """Check if a cost center code is a revenue-producing center."""
        return code in self.revenue_center_codes

    def is_general_service(self, code: str) -> bool:
        """Check if a cost center code is a general service center."""
        return code in self.general_service_codes

    def is_allowable(self, code: str) -> bool:
        """Check if a cost center is Medicare-allowable."""
        cc = self.get_cost_center(code)
        return cc.allowable if cc else True

    def get_allocation_method(self, code: str) -> Optional[AllocationMethod]:
        """Get the default allocation method for a cost center."""
        cc = self.get_cost_center(code)
        return cc.allocation_method if cc else None

    def get_ccr_range(self, code: str) -> tuple[Optional[float], Optional[float]]:
        """Get the expected CCR range for smell test validation."""
        cc = self.get_cost_center(code)
        if cc:
            return (cc.ccr_range_min, cc.ccr_range_max)
        return (None, None)

    def search_centers(self, query: str) -> list[CostCenterDefinition]:
        """Search cost centers by keyword in name or description."""
        query_lower = query.lower()
        return [
            cc
            for cc in self.cost_centers.values()
            if query_lower in cc.name.lower() or query_lower in cc.description.lower()
        ]
