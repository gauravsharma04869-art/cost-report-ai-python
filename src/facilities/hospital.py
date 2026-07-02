"""
Hospital (CMS-2552-10) Facility Registry.

Complete cost center line definitions per the Provider Reimbursement Manual
(PRM 15-2) Chapter 40, including general service centers (01-16) and
revenue-producing centers (20+). Step-down sequence follows CMS §4004.1.

Reference: CMS Pub. 15-2 Ch. 40, Transmittal 25 (Feb 2026)
"""

from __future__ import annotations

from src.core.models import AllocationMethod, CostCenterCategory, CostCenterDefinition, FacilityType
from src.facilities.base import BaseFacilityRegistry


class HospitalRegistry(BaseFacilityRegistry):
    """Acute Care Hospital — CMS-2552-10 cost center definitions."""

    facility_type = FacilityType.HOSPITAL
    form_number = "CMS-2552-10"
    form_title = "Medicare Hospital Cost Report"
    cms_chapter = "PRM 15-2 Chapter 40"
    description = "Acute Care Hospital including teaching, rural, urban, and CAH"

    # ── General Service Cost Centers (01-16) ─────────────────────────
    _general_services: dict[str, CostCenterDefinition] = {
        "01": CostCenterDefinition(
            code="01",
            name="Capital Related - Buildings & Fixtures",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=1,
            description="Depreciation, leases, taxes, insurance, and interest on buildings and fixed equipment",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "02": CostCenterDefinition(
            code="02",
            name="Capital Related - Movable Equipment",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=2,
            description="Depreciation, leases, and interest on movable equipment",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "03": CostCenterDefinition(
            code="03",
            name="Employee Benefits",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=3,
            description="FICA, health insurance, retirement plans, workers' compensation",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SALARIES,
        ),
        "04": CostCenterDefinition(
            code="04",
            name="Administrative & General",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=4,
            description="Administrative salaries, office supplies, telephone, data processing, accounting, HR",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "05": CostCenterDefinition(
            code="05",
            name="Maintenance & Repairs",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=5,
            description="Building and equipment maintenance, repairs, janitorial, grounds upkeep",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "06": CostCenterDefinition(
            code="06",
            name="Laundry & Linen Service",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=6,
            description="Laundry processing, linen purchase and rental, uniform cleaning",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.POUNDS_LAUNDRY,
        ),
        "07": CostCenterDefinition(
            code="07",
            name="Housekeeping",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=7,
            description="Cleaning supplies, housekeeping salaries, waste disposal",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "08": CostCenterDefinition(
            code="08",
            name="Dietary & Cafeteria",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=8,
            description="Food costs, dietary salaries, nutrition services, cafeteria operations",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.MEALS_SERVED,
        ),
        "09": CostCenterDefinition(
            code="09",
            name="Operation of Plant",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=9,
            description="Utilities (electricity, water, gas, steam), HVAC, plant operations",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "10": CostCenterDefinition(
            code="10",
            name="Patient Transport",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=10,
            description="Transporting patients within the facility, stretcher services, escort services",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.PATIENT_DAYS,
        ),
        "11": CostCenterDefinition(
            code="11",
            name="Pharmacy",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=11,
            description="Inpatient pharmacy operations (dispensing, IV preparation, clinical pharmacy)",
            ccr_range_min=0.60,
            ccr_range_max=0.95,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "12": CostCenterDefinition(
            code="12",
            name="Medical Supplies & Equipment",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=12,
            description="Central supply, surgical supplies, medical instruments, implant management",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "13": CostCenterDefinition(
            code="13",
            name="Other General Service",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=13,
            description="Other general service costs not classified above",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "14": CostCenterDefinition(
            code="14",
            name="Physician Services - Part A",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=14,
            description="Intern/resident salaries, teaching physician costs, Part A physician services",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "15": CostCenterDefinition(
            code="15",
            name="Physician Services - Part B",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=15,
            description="Physician Part B services, non-teaching physician costs",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "16": CostCenterDefinition(
            code="16",
            name="Other Capital-Related Costs",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=16,
            description="Capital-related costs not in 01-02 (Transmittal 25 additions)",
            ccr_range_min=None,
            ccr_range_max=None,
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
    }

    # ── Revenue-Producing Cost Centers (20+) ────────────────────────
    _revenue_centers: dict[str, CostCenterDefinition] = {
        "20": CostCenterDefinition(
            code="20",
            name="Routine Care - Adult & Pediatric",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=20,
            description="Adult medical-surgical, pediatric, and mixed acuity inpatient days",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "21": CostCenterDefinition(
            code="21",
            name="Routine Care - ICU/CCU",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=21,
            description="Intensive care, coronary care, and other critical care units",
            ccr_range_min=0.90,
            ccr_range_max=1.20,
        ),
        "22": CostCenterDefinition(
            code="22",
            name="Routine Care - Psychiatric",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=22,
            description="Psychiatric inpatient units (distinct part)",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "23": CostCenterDefinition(
            code="23",
            name="Routine Care - Rehabilitation",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=23,
            description="Inpatient rehabilitation unit (distinct part)",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "24": CostCenterDefinition(
            code="24",
            name="Routine Care - Skilled Nursing",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=24,
            description="Hospital-based SNF unit",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "25": CostCenterDefinition(
            code="25",
            name="Routine Care - Nursery",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=25,
            description="Well-baby nursery and intermediate care nursery",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "26": CostCenterDefinition(
            code="26",
            name="Routine Care - Other",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=26,
            description="Other routine care not classified above",
            ccr_range_min=0.85,
            ccr_range_max=1.15,
        ),
        "30": CostCenterDefinition(
            code="30",
            name="Operating Room",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=30,
            description="Inpatient and outpatient operating rooms, recovery room",
            ccr_range_min=0.40,
            ccr_range_max=0.75,
        ),
        "31": CostCenterDefinition(
            code="31",
            name="Laboratory",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=31,
            description="Clinical lab, pathology, blood bank, microbiology, chemistry",
            ccr_range_min=0.25,
            ccr_range_max=0.50,
        ),
        "32": CostCenterDefinition(
            code="32",
            name="Radiology - Diagnostic",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=32,
            description="X-ray, CT, MRI, ultrasound, nuclear medicine, mammography",
            ccr_range_min=0.40,
            ccr_range_max=0.70,
        ),
        "33": CostCenterDefinition(
            code="33",
            name="Radiology - Therapeutic",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=33,
            description="Radiation oncology, radiation therapy",
            ccr_range_min=0.40,
            ccr_range_max=0.70,
        ),
        "34": CostCenterDefinition(
            code="34",
            name="Emergency Room",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=34,
            description="Emergency department, trauma center, observation",
            ccr_range_min=0.70,
            ccr_range_max=1.10,
        ),
        "35": CostCenterDefinition(
            code="35",
            name="Respiratory Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=35,
            description="Respiratory care, pulmonary function, oxygen therapy",
            ccr_range_min=0.55,
            ccr_range_max=0.85,
        ),
        "36": CostCenterDefinition(
            code="36",
            name="Physical Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=36,
            description="Inpatient and outpatient physical therapy",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "37": CostCenterDefinition(
            code="37",
            name="Occupational Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=37,
            description="Inpatient and outpatient occupational therapy",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "38": CostCenterDefinition(
            code="38",
            name="Speech Pathology",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=38,
            description="Speech-language pathology services",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "39": CostCenterDefinition(
            code="39",
            name="Pharmacy - Outpatient",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=39,
            description="Outpatient pharmacy, retail pharmacy, outpatient IV therapy",
            ccr_range_min=0.60,
            ccr_range_max=0.95,
        ),
        "40": CostCenterDefinition(
            code="40",
            name="Cardiology",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=40,
            description="Cardiac catheterization, EKG, stress testing, echocardiography",
            ccr_range_min=0.40,
            ccr_range_max=0.70,
        ),
        "41": CostCenterDefinition(
            code="41",
            name="Medical Records",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=41,
            description="Medical records, HIM, transcription, coding",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "42": CostCenterDefinition(
            code="42",
            name="Social Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=42,
            description="Discharge planning, case management, social work",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "43": CostCenterDefinition(
            code="43",
            name="Nursing Education",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=43,
            description="Nursing school programs, continuing education, orientation",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "44": CostCenterDefinition(
            code="44",
            name="Other Ancillary",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=44,
            description="Other ancillary services not classified above",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "50": CostCenterDefinition(
            code="50",
            name="Outpatient Clinics",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=50,
            description="Hospital-based outpatient clinics, physician offices",
            ccr_range_min=0.70,
            ccr_range_max=1.00,
        ),
        "51": CostCenterDefinition(
            code="51",
            name="Ambulatory Surgery",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=51,
            description="Ambulatory surgery center, same-day surgery",
            ccr_range_min=0.40,
            ccr_range_max=0.75,
        ),
        "52": CostCenterDefinition(
            code="52",
            name="Home Health Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=52,
            description="Hospital-based home health agency",
            ccr_range_min=0.85,
            ccr_range_max=1.10,
        ),
        "53": CostCenterDefinition(
            code="53",
            name="Hospice Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=53,
            description="Hospital-based hospice program",
            ccr_range_min=0.85,
            ccr_range_max=1.10,
        ),
        "60": CostCenterDefinition(
            code="60",
            name="Dialysis - Outpatient",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=60,
            description="Hemodialysis, peritoneal dialysis, outpatient renal services",
            ccr_range_min=0.85,
            ccr_range_max=1.10,
        ),
        "70": CostCenterDefinition(
            code="70",
            name="Ambulance Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=70,
            description="Emergency and non-emergency ambulance transport",
            ccr_range_min=0.70,
            ccr_range_max=1.00,
        ),
        "80": CostCenterDefinition(
            code="80",
            name="Other Revenue Centers",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=80,
            description="Other revenue-producing centers not classified above",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "81": CostCenterDefinition(
            code="81",
            name="Medicare Advantage - Negotiated Charges",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=81,
            description="MAO negotiated charge arrangement costs (Transmittal 25, Worksheet S-12)",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
    }

    # ── Non-allowable / Adjustment Cost Centers ─────────────────────
    _adjustment_centers: dict[str, CostCenterDefinition] = {
        "90": CostCenterDefinition(
            code="90",
            name="Non-Allowable - Marketing",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=90,
            description="Advertising, marketing, public relations, promotions",
            allowable=False,
        ),
        "91": CostCenterDefinition(
            code="91",
            name="Non-Allowable - Lobbying",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=91,
            description="Lobbying activities, political contributions",
            allowable=False,
        ),
        "92": CostCenterDefinition(
            code="92",
            name="Non-Allowable - Entertainment",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=92,
            description="Entertainment, gifts, recreation",
            allowable=False,
        ),
        "93": CostCenterDefinition(
            code="93",
            name="Non-Allowable - Charity",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=93,
            description="Charity care, free services, bad debt write-offs",
            allowable=False,
        ),
        "94": CostCenterDefinition(
            code="94",
            name="Non-Allowable - Other",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=94,
            description="Other non-allowable costs per Medicare guidelines",
            allowable=False,
        ),
    }

    @property
    def cost_centers(self) -> dict[str, CostCenterDefinition]:
        """All cost centers combined."""
        return {
            **self._general_services,
            **self._revenue_centers,
            **self._adjustment_centers,
        }

    @property
    def step_down_sequence(self) -> list[str]:
        """
        CMS-mandated step-down allocation order per PRM §4004.1.

        General service centers are allocated in this exact sequence.
        Once allocated, a center is closed (no costs allocated back to earlier centers).
        """
        return [
            "01",  # Capital - Buildings & Fixtures
            "02",  # Capital - Movable Equipment
            "16",  # Other Capital-Related
            "03",  # Employee Benefits
            "05",  # Maintenance & Repairs
            "06",  # Laundry & Linen
            "07",  # Housekeeping
            "08",  # Dietary & Cafeteria
            "09",  # Operation of Plant
            "10",  # Patient Transport
            "04",  # Administrative & General
            "11",  # Pharmacy
            "12",  # Medical Supplies
            "13",  # Other General Service
            "14",  # Physician Services - Part A
            "15",  # Physician Services - Part B
        ]

    @property
    def revenue_center_codes(self) -> list[str]:
        return list(self._revenue_centers.keys())

    @property
    def general_service_codes(self) -> list[str]:
        return list(self._general_services.keys())

    @property
    def adjustment_codes(self) -> list[str]:
        return list(self._adjustment_centers.keys())
