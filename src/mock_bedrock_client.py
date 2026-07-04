"""
Mock Bedrock client for demonstration when real Bedrock access is unavailable
(e.g. AWS account without a supported payment instrument).

Activated by setting  BEDROCK_MOCK=1  in the environment or .env file.

All responses are grounded in the actual sample documents and policy knowledge
files — they represent what a correctly-prompted Claude model would return.
Each response includes realistic latency simulation and token counts consistent
with Claude 3 Haiku (fast) and Claude 3 Sonnet (strong) throughput benchmarks.
"""
import json
import time
import random

# ---------------------------------------------------------------------------
# Pre-crafted extraction responses (what Claude would return for each doc)
# ---------------------------------------------------------------------------

_EXTRACTIONS = {
    "claim_auto_001.txt": {
        "claimant_name": "Rajesh Kumar Menon",
        "policy_number": "AUTO-TN-88213",
        "incident_date": "2026-05-14",
        "claim_amount": 145000,
        "incident_description": (
            "Claimant's vehicle (TN 09 AB 4521) was rear-ended at a signal on "
            "Anna Salai, Chennai; rear bumper, tail lamp assembly, and trunk panel "
            "were damaged. FIR No. 2026/CHN/1187 filed at T. Nagar police station."
        ),
        "claim_type": "auto",
    },
    "claim_property_002.txt": {
        "claimant_name": "Priya Subramaniam",
        "policy_number": "PROP-TN-55097",
        "incident_date": "2026-06-02",
        "claim_amount": 380000,
        "incident_description": (
            "Heavy rainfall and water ingress on June 2, 2026 damaged the ground "
            "floor of the claimant's property in Coimbatore — flooring, electrical "
            "wiring in two rooms, and household furniture affected."
        ),
        "claim_type": "property",
    },
    "claim_health_003.txt": {
        "claimant_name": "Suresh Babu Iyer",
        "policy_number": "HLTH-TN-31042",
        "incident_date": "2026-04-28",
        "claim_amount": 92500,
        "incident_description": (
            "Claimant hospitalized for 3 days (April 28-30, 2026) at Ambur General "
            "Hospital for acute appendicitis and laparoscopic appendectomy; "
            "cashless-to-reimbursement conversion after partial cashless delay."
        ),
        "claim_type": "health",
    },
    "repair_invoice_004.png": {
        "claimant_name": "Rajesh Kumar Menon",
        "policy_number": "AUTO-TN-88213",
        "incident_date": "2026-05-15",
        "claim_amount": 145000,
        "incident_description": (
            "Scanned auto repair invoice from Chennai Auto Care. Bumper assembly, "
            "taillight unit, and bodywork labor listed for a total of INR 145,000."
        ),
        "claim_type": "auto",
    },
    "car_damage_005.png": {
        "claimant_name": "Rajesh Kumar Menon",
        "policy_number": "AUTO-TN-88213",
        "incident_date": "2026-05-14",
        "claim_amount": 145000,
        "incident_description": (
            "Visual inspection photograph of blue sedan rear bumper damage, cracked "
            "taillight, and trunk dent. Match for accident claim description."
        ),
        "claim_type": "auto",
    },
}


# ---------------------------------------------------------------------------
# Pre-crafted summary responses — grounded in policy knowledge files
# ---------------------------------------------------------------------------

_SUMMARIES = {
    "auto": (
        "Rajesh Kumar Menon is claiming INR 1,45,000 for rear-end collision damage "
        "to vehicle TN 09 AB 4521 on Anna Salai, Chennai on 2026-05-14. "
        "The claim amount falls below the INR 2,00,000 threshold for expedited "
        "Own Damage settlement per the Tamil Nadu Standard Motor Plan, and an FIR "
        "(No. 2026/CHN/1187) is on file satisfying the mandatory police-report "
        "requirement for third-party collision claims above INR 50,000. "
        "Adjuster should verify the repair estimate from the authorised service "
        "centre against the vehicle's current IDV and confirm no commercial-use "
        "exclusion applies."
    ),
    "property": (
        "Priya Subramaniam is claiming INR 3,80,000 for rainfall-induced water "
        "damage to her Coimbatore property on 2026-06-02. "
        "The Tamil Nadu Homeowner Plan caps water-damage cover at INR 5,00,000 "
        "per incident, so the claim amount is within the policy limit; however, "
        "claims above INR 1,00,000 require independent verification of the "
        "flooding event (municipal record attached) and photographic evidence "
        "(Annexure B referenced). "
        "Adjuster should confirm continuous residency for at least 90 days prior "
        "to incident and obtain itemised replacement estimates for furniture and "
        "electrical fixtures before processing."
    ),
    "health": (
        "Suresh Babu Iyer is submitting a reimbursement claim of INR 92,500 "
        "for a 3-day hospitalisation (April 28-30, 2026) for laparoscopic "
        "appendectomy at Ambur General Hospital. "
        "This is a cashless-to-reimbursement conversion; per the Tamil Nadu "
        "Family Health Plan, such conversions should be prioritised and typically "
        "process within 7-10 working days once discharge summary, itemised bill, "
        "and pre-admission diagnostics are received — all three are stated as "
        "attached. "
        "Adjuster should verify the room-rent component against the plan-tier cap "
        "and confirm no cosmetic or non-prescribed procedure appears on the "
        "itemised bill."
    ),
}

# ---------------------------------------------------------------------------
# Token/latency profiles per model (realistic approximations)
# ---------------------------------------------------------------------------

_PROFILES = {
    # Claude 3 Haiku: ~250 input tokens for extraction prompt + doc, ~120 output
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "input_tokens_base": 248,
        "output_tokens_base": 118,
        "latency_base": 0.9,   # seconds
        "latency_jitter": 0.3,
    },
    # Claude 3 Sonnet: same prompt, richer output, slower
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "input_tokens_base": 248,
        "output_tokens_base": 145,
        "latency_base": 2.1,
        "latency_jitter": 0.6,
    },
}

_DEFAULT_PROFILE = {
    "input_tokens_base": 250,
    "output_tokens_base": 130,
    "latency_base": 1.5,
    "latency_jitter": 0.4,
}


def _profile(model_id):
    return _PROFILES.get(model_id, _DEFAULT_PROFILE)


def _simulate_latency(model_id):
    p = _profile(model_id)
    t = p["latency_base"] + random.uniform(0, p["latency_jitter"])
    time.sleep(t)
    return round(t, 2)


def _token_counts(model_id, extra_input=0, extra_output=0):
    p = _profile(model_id)
    return (
        p["input_tokens_base"] + extra_input,
        p["output_tokens_base"] + extra_output,
    )


# ---------------------------------------------------------------------------
# Public API — drop-in replacement for BedrockClient
# ---------------------------------------------------------------------------

class MockBedrockClient:
    """
    Mimics the interface of BedrockClient (invoke + embed).
    Detects which document / claim type is being processed from the prompt
    text and returns the appropriate pre-crafted response.
    """

    def invoke(self, model_id, prompt, system=None, max_tokens=1000, temperature=0.0):
        latency = _simulate_latency(model_id)

        # --- summary call FIRST: look for adjuster-summary prompt signature ---
        # The generate_summary template always contains "adjuster" in its user text.
        if "adjuster" in prompt.lower() or "policy context" in prompt.lower():
            summary_hints = {
                "auto":     ["Rajesh Kumar Menon", "AUTO-TN-88213"],
                "property": ["Priya Subramaniam",  "PROP-TN-55097"],
                "health":   ["Suresh Babu Iyer",   "HLTH-TN-31042"],
            }
            for claim_type, hints in summary_hints.items():
                if any(hint in prompt for hint in hints):
                    summary_text = _SUMMARIES[claim_type]
                    inp, out = _token_counts(model_id,
                                            extra_input=len(prompt) // 4,
                                            extra_output=len(summary_text) // 4)
                    return {
                        "text": summary_text,
                        "input_tokens": inp,
                        "output_tokens": out,
                        "latency_seconds": latency,
                        "model_id": model_id,
                        "mock": True,
                    }

        # --- extraction call: prompt contains the raw document text ---
        for filename, extraction in _EXTRACTIONS.items():
            if extraction["policy_number"] in prompt:
                inp, out = _token_counts(model_id, extra_input=len(prompt) // 4)
                return {
                    "text": json.dumps(extraction, indent=2),
                    "input_tokens": inp,
                    "output_tokens": out,
                    "latency_seconds": latency,
                    "model_id": model_id,
                    "mock": True,
                }



        # Fallback — should not normally be reached
        return {
            "text": '{"error": "mock could not match document"}',
            "input_tokens": 100,
            "output_tokens": 10,
            "latency_seconds": latency,
            "model_id": model_id,
            "mock": True,
        }

    def embed(self, text, model_id=None):
        """
        Returns a deterministic 1536-dim unit vector derived from the text hash.
        Ensures RAG cosine similarity still works (different texts → different vectors).
        """
        import hashlib
        import numpy as np

        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(1536).astype("float32")
        vec /= np.linalg.norm(vec)          # unit vector → cosine sim is meaningful
        return vec.tolist()
