"""
Basic content validator (Step 3 requirement).

Checks the extraction output is structurally sound and flags anything a
human should double-check before the summary is trusted. This is not a
security boundary — it's a sanity layer.
"""
import json
import re

REQUIRED_FIELDS = [
    "claimant_name",
    "policy_number",
    "incident_date",
    "claim_amount",
    "incident_description",
    "claim_type",
]

INJECTION_MARKERS = [
    "ignore previous instructions",
    "ignore all prior",
    "system prompt",
    "you are now",
]


class ValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.parsed = None

    def add_error(self, msg):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_extraction(raw_model_output: str) -> ValidationResult:
    result = ValidationResult()

    cleaned = raw_model_output.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?|```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        result.add_error(f"Model did not return valid JSON: {e}")
        return result

    result.parsed = parsed

    for field in REQUIRED_FIELDS:
        if field not in parsed:
            result.add_error(f"Missing required field: {field}")
        elif parsed[field] in (None, "", "null"):
            result.add_warning(f"Field '{field}' is empty/null — document may lack this info")

    amount = parsed.get("claim_amount")
    if amount is not None:
        try:
            amount_val = float(amount)
            if amount_val < 0:
                result.add_error("claim_amount is negative")
            if amount_val > 10_000_000:
                result.add_warning("claim_amount is unusually large — verify manually")
        except (TypeError, ValueError):
            result.add_error(f"claim_amount is not numeric: {amount!r}")

    return result


def check_prompt_injection(document_text: str) -> list:
    """
    Flags documents that appear to contain instruction-injection attempts —
    e.g. a 'claim document' that actually contains text trying to steer the
    model ('ignore previous instructions...'). Doesn't block, just flags for
    manual review, since false positives on legitimate documents are common.
    """
    lowered = document_text.lower()
    return [marker for marker in INJECTION_MARKERS if marker in lowered]
