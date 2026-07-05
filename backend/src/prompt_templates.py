"""
Standardized prompt template manager (Step 3: reusable components).

Templates return strict JSON where possible — makes downstream validation
and comparison across models mechanical instead of eyeballed.
"""


class PromptTemplateManager:
    def __init__(self):
        self.templates = {
            "extract_info": {
                "system": (
                    "You are an insurance claims data extraction system. "
                    "Extract only what is explicitly stated in the document. "
                    "Never infer or fabricate a value. Use null for anything missing."
                ),
                "user": """Extract the following fields from this insurance claim document
and return ONLY a JSON object, no other text:

- claimant_name (string)
- policy_number (string)
- incident_date (string, ISO format if possible)
- claim_amount (number, no currency symbol)
- incident_description (string, 1-2 sentences)
- claim_type (string: auto | property | health | other)

Document:
{document_text}""",
            },
            "generate_summary": {
                "system": (
                    "You are an assistant helping a claims adjuster triage cases quickly. "
                    "Be factual and concise. Do not speculate about fault or payout amounts "
                    "beyond what the claim data states."
                ),
                "user": """Extracted claim data:
{extracted_info}

Relevant policy context:
{policy_context}

Write a 3-4 sentence adjuster-facing summary covering: what happened, whether
the claim amount appears within the policy's stated coverage, and any
red flags an adjuster should check manually.""",
            },
        }

    def get(self, template_name, **kwargs):
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        return {
            "system": template["system"],
            "user": template["user"].format(**kwargs),
        }
