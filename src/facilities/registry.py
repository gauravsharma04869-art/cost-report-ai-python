"""
Facility registry factory — selects the correct registry by facility type.

Provides a single point of access for all CMS cost center definitions
across all supported facility types.
"""

from __future__ import annotations

from typing import Optional

from src.core.models import FacilityType
from src.facilities.base import BaseFacilityRegistry
from src.facilities.hha import HHARegistry
from src.facilities.hospice import HospiceRegistry
from src.facilities.hospital import HospitalRegistry
from src.facilities.snf import SNFRegistry


def get_registry(facility_type: FacilityType) -> BaseFacilityRegistry:
    """Return the facility registry for the given facility type."""
    registries = {
        FacilityType.HOSPITAL: HospitalRegistry,
        FacilityType.SNF: SNFRegistry,
        FacilityType.HOSPICE: HospiceRegistry,
        FacilityType.HHA: HHARegistry,
    }
    cls = registries.get(facility_type)
    if cls is None:
        raise ValueError(f"Unsupported facility type: {facility_type}")
    return cls()


def get_registry_by_form_number(form_number: str) -> BaseFacilityRegistry:
    """Return the facility registry by CMS form number."""
    mapping = {
        "CMS-2552-10": FacilityType.HOSPITAL,
        "CMS-2540-10": FacilityType.SNF,
        "CMS-1984-14": FacilityType.HOSPICE,
        "CMS-1728-20": FacilityType.HHA,
    }
    ft = mapping.get(form_number.upper())
    if ft is None:
        raise ValueError(f"Unknown form number: {form_number}")
    return get_registry(ft)


def list_all_cost_centers(
    facility_type: Optional[FacilityType] = None,
) -> dict[str, dict[str, dict]]:
    """
    List cost centers for all (or a specific) facility type(s).

    Returns a nested dict: {facility_type: {code: {name, category, ...}}}
    Useful for API responses and documentation.
    """
    types = [facility_type] if facility_type else list(FacilityType)
    result: dict[str, dict[str, dict]] = {}
    for ft in types:
        reg = get_registry(ft)
        result[ft.value] = {}
        for code, cc in reg.cost_centers.items():
            result[ft.value][code] = {
                "name": cc.name,
                "category": cc.category.value,
                "worksheet": cc.worksheet,
                "line_number": cc.line_number,
                "allowable": cc.allowable,
                "ccr_range": (
                    {"min": cc.ccr_range_min, "max": cc.ccr_range_max}
                    if cc.ccr_range_min is not None and cc.ccr_range_max is not None
                    else None
                ),
            }
    return result
