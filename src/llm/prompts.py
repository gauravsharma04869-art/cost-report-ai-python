"""
Prompt templates for the AI classification engine.

Each prompt is engineered for deterministic, auditable output.
System prompt establishes the CPA-expert persona.
"""

from __future__ import annotations

from typing import Any

from src.core.models import FacilityType

# ═══════════════════════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert Senior Medicare Cost Report CPA with 15+ years of experience.

Your task is to map general ledger (GL) account descriptions to the correct CMS
cost center codes for Medicare cost report preparation (Worksheet A).

RULES:
1. You MUST output valid JSON only — no markdown, no explanation outside JSON.
2. Every classification must include a confidence score (0.0-1.0) and reasoning.
3. If an account description is ambiguous, use context clues from the account number
   and description to make your best determination, but set confidence appropriately.
4. If the description clearly indicates a non-allowable cost (marketing, lobbying,
   entertainment, donations, fines), classify as unallowable (code 90+).
5. When in doubt, default to Administrative & General (code 04) with LOW confidence.

OUTPUT FORMAT:
{
  "cost_center_code": "04",
  "cost_center_name": "Administrative & General",
  "confidence_score": 0.95,
  "reasoning": "Brief explanation of why this classification was chosen",
  "worksheet": "A"
}"""


# ═══════════════════════════════════════════════════════════════════════════════
# Classification Prompt Builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_classification_prompt(
    account_description: str,
    account_number: str,
    facility_type: FacilityType,
    registry_data: dict[str, Any],
    few_shot_examples: list[dict[str, Any]] | None = None,
) -> str:
    """
    Build a prompt for classifying a single GL account.

    Includes:
    - The GL account to classify
    - The full CMS cost center registry for context
    - Few-shot examples if available
    """
    cost_centers_text = _format_cost_centers_for_prompt(registry_data["cost_centers"])
    examples_text = _format_few_shot_examples(few_shot_examples) if few_shot_examples else ""

    prompt = f"""FACILITY TYPE: {registry_data['facility_type'].upper()}
FORM: {registry_data['form_number']}

CMS COST CENTER REGISTRY:
{cost_centers_text}

{examples_text}

CLASSIFY THIS GL ACCOUNT:
Account Number: {account_number}
Account Description: {account_description}

Output ONLY valid JSON mapping this account to the correct CMS cost center code.
"""

    return prompt


def build_unallowable_check_prompt(
    account_description: str,
    account_number: str,
) -> str:
    """
    Prompt for checking if a GL account is non-allowable.

    Used when keyword-based detection is inconclusive.
    """
    return f"""Is the following GL account description likely a Medicare NON-ALLOWABLE cost?

Medicare non-allowable costs include:
- Marketing & advertising
- Lobbying & political activities
- Entertainment & recreation
- Charitable donations
- Fines & penalties
- Fundraising expenses

Account: {account_number} - {account_description}

Answer YES or NO followed by a brief reason.
Format: {{"is_unallowable": true/false, "category": "marketing|lobbying|entertainment|donations|fines|other", "reasoning": "..."}}"""


def build_few_shot_examples(facility_type: FacilityType) -> list[dict]:
    """Return few-shot examples for a given facility type."""
    hospital_examples = [
        {
            "account_number": "6010",
            "account_description": "RN Salaries - Medical Surgical Unit",
            "cost_center_code": "20",
            "cost_center_name": "Routine Care - Adult & Pediatric",
            "confidence_score": 0.95,
            "reasoning": "RN salaries on a med-surg unit map directly to routine inpatient care (Code 20).",
            "worksheet": "A",
        },
        {
            "account_number": "7100",
            "account_description": "Lab Supplies - Chemistry",
            "cost_center_code": "31",
            "cost_center_name": "Laboratory",
            "confidence_score": 0.95,
            "reasoning": "Chemistry lab supplies map directly to Laboratory cost center (Code 31).",
            "worksheet": "A",
        },
        {
            "account_number": "8100",
            "account_description": "Pharmacy - IV Solutions",
            "cost_center_code": "39",
            "cost_center_name": "Pharmacy - Outpatient",
            "confidence_score": 0.90,
            "reasoning": "Pharmacy IV solutions map to Pharmacy cost center. Without inpatient/outpatient distinction, defaults to outpatient (Code 39).",
            "worksheet": "A",
        },
        {
            "account_number": "5005",
            "account_description": "Advertising - Chamber of Commerce Sponsorship",
            "cost_center_code": "90",
            "cost_center_name": "Non-Allowable Costs",
            "confidence_score": 0.98,
            "reasoning": "Advertising and sponsorship are Medicare non-allowable costs.",
            "worksheet": "A-8",
        },
        {
            "account_number": "9100",
            "account_description": "Medical Director - Administrative Duties",
            "cost_center_code": "04",
            "cost_center_name": "Administrative & General",
            "confidence_score": 0.85,
            "reasoning": "Medical director administrative time maps to A&G (Code 04), not direct patient care.",
            "worksheet": "A",
        },
    ]

    snf_examples = [
        {
            "account_number": "7000",
            "account_description": "CNA Wages - Skilled Nursing Floor",
            "cost_center_code": "10",
            "cost_center_name": "Routine Services - Nursing",
            "confidence_score": 0.95,
            "reasoning": "CNA wages on skilled nursing floor map directly to Routine Services - Nursing (Code 10).",
            "worksheet": "A",
        },
        {
            "account_number": "7500",
            "account_description": "PT Services - Contract Labor",
            "cost_center_code": "23",
            "cost_center_name": "Physical Therapy",
            "confidence_score": 0.95,
            "reasoning": "Physical therapy contract labor maps to PT cost center (Code 23).",
            "worksheet": "A",
        },
    ]

    hospice_examples = [
        {
            "account_number": "6000",
            "account_description": "RN Visits - Routine Home Care",
            "cost_center_code": "10",
            "cost_center_name": "Routine Home Care (RHC)",
            "confidence_score": 0.95,
            "reasoning": "RN visits for routine home care map to RHC (Code 10).",
            "worksheet": "A",
        },
        {
            "account_number": "6500",
            "account_description": "Bereavement Counseling Services",
            "cost_center_code": "23",
            "cost_center_name": "Counseling Services",
            "confidence_score": 0.90,
            "reasoning": "Bereavement counseling maps to Counseling Services (Code 23).",
            "worksheet": "A",
        },
    ]

    hha_examples = [
        {
            "account_number": "5500",
            "account_description": "RN Visit - Home Health Patient",
            "cost_center_code": "10",
            "cost_center_name": "Skilled Nursing",
            "confidence_score": 0.95,
            "reasoning": "RN home health visits map directly to Skilled Nursing (Code 10).",
            "worksheet": "A",
        },
        {
            "account_number": "5600",
            "account_description": "PT Visit - Home Health",
            "cost_center_code": "11",
            "cost_center_name": "Physical Therapy",
            "confidence_score": 0.95,
            "reasoning": "Physical therapy home health visits map to PT (Code 11).",
            "worksheet": "A",
        },
    ]

    examples_map = {
        FacilityType.HOSPITAL: hospital_examples,
        FacilityType.SNF: snf_examples,
        FacilityType.HOSPICE: hospice_examples,
        FacilityType.HHA: hha_examples,
    }

    return examples_map.get(facility_type, hospital_examples)


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _format_cost_centers_for_prompt(cost_centers: dict[str, Any]) -> str:
    """Format cost center registry into a readable text block for the prompt."""
    lines = []
    for code, cc in sorted(cost_centers.items()):
        allowable = "(allowable)" if cc.get("allowable", True) else "(NON-ALLOWABLE)"
        lines.append(f"  {code}: {cc['name']} [{cc['category']}] {allowable}")
        if cc.get("description"):
            lines.append(f"      {cc['description']}")
    return "\n".join(lines)


def _format_few_shot_examples(examples: list[dict[str, Any]]) -> str:
    """Format few-shot examples for the prompt."""
    lines = ["FEW-SHOT EXAMPLES:"]
    for ex in examples:
        lines.append(
            f"  Account {ex['account_number']}: '{ex['account_description']}' → "
            f"Code {ex['cost_center_code']} ({ex['cost_center_name']}) "
            f"[confidence: {ex['confidence_score']}]"
        )
    return "\n".join(lines)
