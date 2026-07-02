"""
Skilled Nursing Facility (CMS-2540-10) Registry.

Cost center definitions per PRM 15-2 Chapter 35. SNFs have a simpler
cost center structure than hospitals but still require full step-down
allocation with cost centers for routine services, ancillary, and
general service overhead.

Reference: CMS Pub. 15-2 Ch. 35, CMS-2540-10 form instructions
"""

from __future__ import annotations

from src.core.models import AllocationMethod, CostCenterCategory, CostCenterDefinition, FacilityType
from src.facilities.base import BaseFacilityRegistry


class SNFRegistry(BaseFacilityRegistry):
    """Skilled Nursing Facility — CMS-2540-10 cost center definitions."""

    facility_type = FacilityType.SNF
    form_number = "CMS-2540-10"
    form_title = "Medicare Skilled Nursing Facility Cost Report"
    cms_chapter = "PRM 15-2 Chapter 35"
    description = "Skilled Nursing Facility (free-standing and hospital-based)"

    _general_services: dict[str, CostCenterDefinition] = {
        "01": CostCenterDefinition(
            code="01",
            name="Capital-Related Costs",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=1,
            description="Depreciation, rent, leases, taxes, insurance on buildings and equipment",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "02": CostCenterDefinition(
            code="02",
            name="Employee Benefits",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=2,
            description="FICA, health insurance, retirement, worker's compensation",
            allocation_method=AllocationMethod.SALARIES,
        ),
        "03": CostCenterDefinition(
            code="03",
            name="Administrative & General",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=3,
            description="Administration, accounting, HR, data processing, telephone, office supplies",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "04": CostCenterDefinition(
            code="04",
            name="Maintenance & Repairs",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=4,
            description="Building/equipment maintenance, janitorial, grounds",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "05": CostCenterDefinition(
            code="05",
            name="Laundry & Linen",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=5,
            description="Laundry processing, linen purchase and rental",
            allocation_method=AllocationMethod.POUNDS_LAUNDRY,
        ),
        "06": CostCenterDefinition(
            code="06",
            name="Housekeeping",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=6,
            description="Cleaning supplies and housekeeping salaries",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "07": CostCenterDefinition(
            code="07",
            name="Dietary",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=7,
            description="Food costs, dietary salaries, nutrition services",
            allocation_method=AllocationMethod.MEALS_SERVED,
        ),
        "08": CostCenterDefinition(
            code="08",
            name="Operation of Plant",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=8,
            description="Utilities (electricity, water, gas), HVAC, plant operations",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "09": CostCenterDefinition(
            code="09",
            name="Other General Service",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=9,
            description="Other general service costs not classified above",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
    }

    _revenue_centers: dict[str, CostCenterDefinition] = {
        "10": CostCenterDefinition(
            code="10",
            name="Routine Services - Nursing",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=10,
            description="Direct nursing care, nurse aides, LPNs, RNs on patient floors",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "11": CostCenterDefinition(
            code="11",
            name="Routine Services - Other",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=11,
            description="Other routine care costs (room, board, social services, activities)",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "20": CostCenterDefinition(
            code="20",
            name="Pharmacy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=20,
            description="Medication dispensing, IV therapy, pharmaceutical supplies",
            ccr_range_min=0.60,
            ccr_range_max=0.95,
        ),
        "21": CostCenterDefinition(
            code="21",
            name="Laboratory",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=21,
            description="Clinical laboratory services (often contracted)",
            ccr_range_min=0.25,
            ccr_range_max=0.50,
        ),
        "22": CostCenterDefinition(
            code="22",
            name="Radiology",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=22,
            description="X-ray and other diagnostic imaging",
            ccr_range_min=0.40,
            ccr_range_max=0.70,
        ),
        "23": CostCenterDefinition(
            code="23",
            name="Physical Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=23,
            description="Physical therapy services",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "24": CostCenterDefinition(
            code="24",
            name="Occupational Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=24,
            description="Occupational therapy services",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "25": CostCenterDefinition(
            code="25",
            name="Speech Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=25,
            description="Speech-language pathology services",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "26": CostCenterDefinition(
            code="26",
            name="Other Ancillary",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=26,
            description="Other ancillary services not classified above",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "30": CostCenterDefinition(
            code="30",
            name="IV Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=30,
            description="Intravenous therapy services",
            ccr_range_min=0.60,
            ccr_range_max=0.95,
        ),
    }

    _non_allowable: dict[str, CostCenterDefinition] = {
        "90": CostCenterDefinition(
            code="90",
            name="Non-Allowable Costs",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=90,
            description="Marketing, lobbying, entertainment, and other non-allowable costs",
            allowable=False,
        ),
    }

    @property
    def cost_centers(self) -> dict[str, CostCenterDefinition]:
        return {**self._general_services, **self._revenue_centers, **self._non_allowable}

    @property
    def step_down_sequence(self) -> list[str]:
        """SNF step-down sequence per CMS guidelines."""
        return [
            "01",  # Capital-Related
            "02",  # Employee Benefits
            "04",  # Maintenance & Repairs
            "05",  # Laundry & Linen
            "06",  # Housekeeping
            "07",  # Dietary
            "08",  # Operation of Plant
            "03",  # Administrative & General
            "09",  # Other General Service
        ]

    @property
    def revenue_center_codes(self) -> list[str]:
        return list(self._revenue_centers.keys())

    @property
    def general_service_codes(self) -> list[str]:
        return list(self._general_services.keys())
