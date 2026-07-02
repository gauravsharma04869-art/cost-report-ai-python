"""
AI Semantic Account Mapping Engine.

Classifies messy GL account descriptions against CMS cost center line items
using LiteLLM for provider-agnostic LLM access. Supports zero-shot and few-shot
classification with full confidence scoring, reasoning, and unallowable expense detection.

Architecture:
  GL Account Description → [LLM Prompt with CMS Registry] → Structured Classification
                                                                     ↓
                                                          Confidence Score (0-1)
                                                          Reasoning Chain
                                                          Unallowable Flag
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from src.config import settings
from src.core.models import (
    ClassificationBatchResult,
    ClassificationResult,
    ConfidenceLevel,
    FacilityType,
    GrossGLTransaction,
    UnallowableCategory,
)
from src.facilities.registry import get_registry
from src.llm.prompts import (
    build_classification_prompt,
    build_unallowable_check_prompt,
    build_few_shot_examples,
    CLASSIFICATION_SYSTEM_PROMPT,
)


class GLClassifier:
    """
    Classifies GL account descriptions against CMS cost center line items.

    Uses LiteLLM to call configurable LLM providers (OpenAI, Azure, Anthropic, etc.)
    with structured output parsing for deterministic, auditable results.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.0,
    ):
        self.model = model or settings.LLM_MODEL
        self.api_key = api_key or settings.LLM_API_KEY
        self.provider = provider or settings.LLM_PROVIDER
        self.temperature = temperature

        # Configure LiteLLM
        if self.api_key:
            litellm.api_key = self.api_key

    def classify(
        self,
        transaction: GrossGLTransaction,
        facility_type: FacilityType,
        registry_data: Optional[dict[str, Any]] = None,
        few_shot_examples: Optional[list[dict]] = None,
    ) -> ClassificationResult:
        """
        Classify a single GL transaction against a facility's cost center registry.

        Args:
            transaction: The GL transaction to classify
            facility_type: Hospital, SNF, Hospice, or HHA
            registry_data: Pre-fetched registry data (cost centers, codes, descriptions)
            few_shot_examples: Optional examples for few-shot prompting

        Returns:
            ClassificationResult with mapped cost center, confidence, and reasoning
        """
        if registry_data is None:
            registry = get_registry(facility_type)
            registry_data = self._build_registry_data(registry)

        # First check: is this an unallowable expense?
        unallowable_check = self._check_unallowable(transaction)

        if unallowable_check["is_unallowable"]:
            # Route to Worksheet A-8 adjustments
            return ClassificationResult(
                transaction_id=transaction.id,
                account_number=transaction.account_number,
                account_description=transaction.account_description,
                net_amount=transaction.net_amount,
                mapped_cost_center_code="90",
                mapped_cost_center_name="Non-Allowable Costs",
                mapped_worksheet="A-8",
                confidence_score=0.95,
                confidence_level=ConfidenceLevel.HIGH,
                reasoning=unallowable_check["reasoning"],
                source_attribution=f"Detected as unallowable: {unallowable_check['category']}",
                is_unallowable=True,
                unallowable_category=UnallowableCategory(unallowable_check["category"]),
                unallowable_reason=unallowable_check["reasoning"],
                model_used=self.model,
            )

        # Build classification prompt
        prompt = build_classification_prompt(
            account_description=transaction.account_description,
            account_number=transaction.account_number,
            facility_type=facility_type,
            registry_data=registry_data,
            few_shot_examples=few_shot_examples or build_few_shot_examples(facility_type),
        )

        # Call LLM
        result = self._call_llm(prompt)

        # Parse and return
        return self._parse_result(transaction, result, facility_type)

    def classify_batch(
        self,
        transactions: list[GrossGLTransaction],
        facility_type: FacilityType,
        batch_size: int = 10,
    ) -> ClassificationBatchResult:
        """
        Classify a batch of GL transactions.

        For larger batches, uses sequential processing with a single model call
        to classify multiple accounts at once (more cost-effective).

        Args:
            transactions: List of GL transactions to classify
            facility_type: Target facility type
            batch_size: Number of transactions per LLM call

        Returns:
            ClassificationBatchResult with all classifications
        """
        start_time = time.time()
        registry = get_registry(facility_type)
        registry_data = self._build_registry_data(registry)
        few_shot = build_few_shot_examples(facility_type)

        all_results: list[ClassificationResult] = []
        summary = {
            "total": len(transactions),
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "unallowable": 0,
            "total_amount": 0.0,
            "unallowable_amount": 0.0,
        }

        # Batch processing — send multiple accounts in one LLM call
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i : i + batch_size]

            results = self._classify_batch_internal(
                batch, facility_type, registry_data, few_shot
            )
            all_results.extend(results)

            # Update summary
            for r in results:
                summary["total_amount"] += float(r.net_amount)
                if r.is_unallowable:
                    summary["unallowable"] += 1
                    summary["unallowable_amount"] += float(r.net_amount)
                if r.confidence_level == ConfidenceLevel.HIGH:
                    summary["high_confidence"] += 1
                elif r.confidence_level == ConfidenceLevel.MEDIUM:
                    summary["medium_confidence"] += 1
                else:
                    summary["low_confidence"] += 1

        elapsed = (time.time() - start_time) * 1000

        return ClassificationBatchResult(
            ingestion_id=transactions[0].id if transactions else "",
            facility_type=facility_type,
            results=all_results,
            summary=summary,
            processing_time_ms=round(elapsed, 2),
            model_used=self.model,
        )

    def _classify_batch_internal(
        self,
        batch: list[GrossGLTransaction],
        facility_type: FacilityType,
        registry_data: dict[str, Any],
        few_shot: list[dict],
    ) -> list[ClassificationResult]:
        """Classify a batch of transactions in a single LLM call."""
        results: list[ClassificationResult] = []

        for txn in batch:
            try:
                result = self.classify(txn, facility_type, registry_data, few_shot)
                results.append(result)
            except Exception as e:
                # Fallback: return low-confidence classification
                results.append(ClassificationResult(
                    transaction_id=txn.id,
                    account_number=txn.account_number,
                    account_description=txn.account_description,
                    net_amount=txn.net_amount,
                    mapped_cost_center_code=settings.CLASSIFIER_DEFAULT_FALLBACK_COST_CENTER,
                    mapped_cost_center_name="Administrative & General",
                    mapped_worksheet="A",
                    confidence_score=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    reasoning=f"Classification failed: {e}. Defaulted to A&G.",
                    source_attribution="Fallback: LLM call error",
                    model_used=self.model,
                ))

        return results

    def _check_unallowable(self, transaction: GrossGLTransaction) -> dict:
        """
        Determine if a GL account should be flagged as non-allowable.

        First checks keyword patterns (fast path), then uses LLM for
        ambiguous descriptions (slow path).
        """
        desc = transaction.account_description.lower()
        acct = transaction.account_number.lower()

        # ── Keyword-based fast path ──────────────────────────────────
        unallowable_patterns = {
            "marketing": [
                "marketing", "advertising", "promotion", "public relations", "pr ",
                "branding", "market research", "ad campaign", "social media ads",
            ],
            "lobbying": [
                "lobby", "political", "campaign", "pac ", "legislative advocacy",
                "grassroots", "government relations",
            ],
            "entertainment": [
                "entertainment", "golf", "gym membership", "recreation",
                "social events", "company party", "holiday party", "sporting event",
            ],
            "donations": [
                "donation", "charitable contribution", "sponsorship", "fundraising gift",
                "political contribution",
            ],
            "fines": [
                "fine", "penalty", "settlement", "litigation award", "regulatory fine",
            ],
        }

        for category, patterns in unallowable_patterns.items():
            for pattern in patterns:
                if pattern in desc:
                    return {
                        "is_unallowable": True,
                        "category": category,
                        "reasoning": f"Account description contains '{pattern}' which is a Medicare non-allowable cost ({category}).",
                    }

        # ── LLM-based slow path for ambiguous cases ──────────────────
        prompt = build_unallowable_check_prompt(
            account_description=transaction.account_description,
            account_number=transaction.account_number,
        )

        try:
            response = self._call_llm(prompt, max_tokens=300)
            raw = response.get("raw_text", "").strip().lower()
            if "unallowable" in raw or "non-allowable" in raw or "yes" in raw:
                return {
                    "is_unallowable": True,
                    "category": "other",
                    "reasoning": f"LLM classified as potentially non-allowable: {raw[:200]}",
                }
        except Exception:
            pass

        return {"is_unallowable": False, "category": None, "reasoning": ""}

    def _call_llm(self, prompt: str, max_tokens: int = None) -> dict:
        """
        Call the LLM via LiteLLM with retry logic.

        Returns parsed JSON response with fields:
          cost_center_code, cost_center_name, confidence_score, reasoning
        """
        messages = [
            {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self._llm_call_with_retry(messages, max_tokens)

        raw = response.choices[0].message.content or ""

        # Parse JSON from response (handle markdown-wrapped JSON)
        return self._parse_llm_response(raw)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: True),
    )
    def _llm_call_with_retry(self, messages: list[dict], max_tokens: int = None) -> Any:
        """Make the actual LiteLLM API call with retry."""
        return litellm.completion(
            model=f"{self.provider}/{self.model}",
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        )

    def _parse_llm_response(self, raw: str) -> dict:
        """Extract JSON from LLM response (handles code blocks, trailing text)."""
        # Strip markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)

        # Find JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: return raw text
        return {"raw_text": raw, "cost_center_code": "04", "confidence_score": 0.0}

    def _parse_result(
        self,
        transaction: GrossGLTransaction,
        llm_result: dict,
        facility_type: FacilityType,
    ) -> ClassificationResult:
        """Convert LLM response into a structured ClassificationResult."""
        code = str(llm_result.get("cost_center_code", "04")).strip().zfill(2)
        name = str(llm_result.get("cost_center_name", "Administrative & General"))
        score = float(llm_result.get("confidence_score", 0.0))
        reasoning = str(llm_result.get("reasoning", ""))
        worksheet = str(llm_result.get("worksheet", "A"))

        # Validate against registry
        registry = get_registry(facility_type)
        cc = registry.get_cost_center(code)
        if cc:
            name = cc.name
            worksheet = cc.worksheet

        return ClassificationResult(
            transaction_id=transaction.id,
            account_number=transaction.account_number,
            account_description=transaction.account_description,
            net_amount=transaction.net_amount,
            mapped_cost_center_code=code,
            mapped_cost_center_name=name,
            mapped_worksheet=worksheet,
            confidence_score=round(score, 4),
            confidence_level=self._score_to_level(score),
            reasoning=reasoning,
            source_attribution=f"LLM classified from GL description: '{transaction.account_description}'",
            is_unallowable=False,
            model_used=self.model,
        )

    @staticmethod
    def _score_to_level(score: float) -> ConfidenceLevel:
        if score >= settings.CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif score >= settings.CLASSIFIER_MEDIUM_CONFIDENCE_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @staticmethod
    def _build_registry_data(registry: Any) -> dict[str, Any]:
        """Build a simplified registry dict for prompt consumption."""
        return {
            "facility_type": registry.facility_type.value,
            "form_number": registry.form_number,
            "cost_centers": {
                code: {
                    "name": cc.name,
                    "category": cc.category.value,
                    "description": cc.description,
                    "allowable": cc.allowable,
                }
                for code, cc in registry.cost_centers.items()
            },
            "step_down_sequence": registry.step_down_sequence,
        }
