"""
Hospice (CMS-1984-14) Facility Registry.

Cost center definitions per PRM 15-2 Chapter 43. Hospice cost reports
track expenses and revenue by Level of Care:
  - RHC: Routine Home Care
  - CHC: Continuous Home Care
  - IRC: Inpatient Respite Care
  - GIP: General Inpatient Care

Reference: CMS Pub. 15-2 Ch. 43, CMS-1984-14 form instructions
"""

from __future__ import annotations

from src.core.models import AllocationMethod, CostCenterCategory, CostCenterDefinition, FacilityType
from src.facilities.base import BaseFacilityRegistry


class HospiceRegistry(BaseFacilityRegistry):
    """Hospice — CMS-1984-14 cost center definitions."""

    facility_type = FacilityType.HOSPICE
    form_number = "CMS-1984-14"
    form_title = "Medicare Hospice Cost Report"
    cms_chapter = "PRM 15-2 Chapter 43"
    description = "Hospice provider (free-standing and hospital-based)"

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
            description="Administration, accounting, HR, billing, data processing, office",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "04": CostCenterDefinition(
            code="04",
            name="Maintenance & Housekeeping",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=4,
            description="Building/equipment maintenance, janitorial, laundry, linen",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "05": CostCenterDefinition(
            code="05",
            name="Dietary",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=5,
            description="Food costs and dietary services (primarily GIP/inpatient)",
            allocation_method=AllocationMethod.MEALS_SERVED,
        ),
        "06": CostCenterDefinition(
            code="06",
            name="Operation of Plant",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=6,
            description="Utilities, HVAC, plant operations",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "07": CostCenterDefinition(
            code="07",
            name="Other General Service",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=7,
            description="Other general service costs not classified above",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
    }

    _revenue_centers: dict[str, CostCenterDefinition] = {
        # ── Direct Patient Care by Level of Care ──
        "10": CostCenterDefinition(
            code="10",
            name="Routine Home Care (RHC)",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=10,
            description="Routine home care — nursing, aides, social work, counseling, volunteers",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "11": CostCenterDefinition(
            code="11",
            name="Continuous Home Care (CHC)",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=11,
            description="Continuous home care during crisis periods (8+ hours/day)",
            ccr_range_min=0.90,
            ccr_range_max=1.20,
        ),
        "12": CostCenterDefinition(
            code="12",
            name="Inpatient Respite Care (IRC)",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=12,
            description="Short-term respite care (up to 5 days) in an inpatient setting",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "13": CostCenterDefinition(
            code="13",
            name="General Inpatient Care (GIP)",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=13,
            description="General inpatient care for symptom management",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        # ── Service Disciplines (cross-cutting) ──
        "20": CostCenterDefinition(
            code="20",
            name="Nursing Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=20,
            description="Registered nurse, licensed practical nurse services",
            ccr_range_min=0.85,
            ccr_range_max=1.10,
        ),
        "21": CostCenterDefinition(
            code="21",
            name="Medical Social Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=21,
            description="Social work, counseling, bereavement",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "22": CostCenterDefinition(
            code="22",
            name="Physician Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=22,
            description="Hospice physician and medical director services",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "23": CostCenterDefinition(
            code="23",
            name="Counseling Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=23,
            description="Dietary, spiritual, bereavement, and other counseling",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        # ── Drugs & Supplies ──
        "30": CostCenterDefinition(
            code="30",
            name="Drugs & Biologics",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=30,
            description="Symptom management drugs, biologics, IV medications",
            ccr_range_min=0.60,
            ccr_range_max=0.95,
        ),
        "31": CostCenterDefinition(
            code="31",
            name="Medical Supplies & Equipment",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=31,
            description="Durable medical equipment, supplies, prosthetics",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        # ── Other ──
        "40": CostCenterDefinition(
            code="40",
            name="Other Hospice Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=40,
            description="Other hospice services not classified above",
            ccr_range_min=None,
            ccr_range_max=None,
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
        """Hospice step-down sequence per CMS guidelines."""
        return [
            "01",  # Capital-Related
            "02",  # Employee Benefits
            "04",  # Maintenance & Housekeeping
            "05",  # Dietary
            "06",  # Operation of Plant
            "03",  # Administrative & General
            "07",  # Other General Service
        ]

    @property
    def revenue_center_codes(self) -> list[str]:
        return list(self._revenue_centers.keys())

    @property
    def general_service_codes(self) -> list[str]:
        return list(self._general_services.keys())
