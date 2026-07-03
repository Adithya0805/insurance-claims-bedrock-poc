"""
Compares multiple models on the same document/task — Step 4 requirement.
Produces a table you can drop straight into FINDINGS_TEMPLATE.md.
"""
from tabulate import tabulate
from .bedrock_client import BedrockClient
from .mock_bedrock_client import MockBedrockClient
from .prompt_templates import PromptTemplateManager
from .content_validator import validate_extraction
import os


def compare_extraction_models(document_text, model_ids):
    if os.getenv("BEDROCK_MOCK", "0") == "1":
        bedrock = MockBedrockClient()
    else:
        bedrock = BedrockClient()
    templates = PromptTemplateManager()
    prompt = templates.get("extract_info", document_text=document_text)

    rows = []
    for model_id in model_ids:
        result = bedrock.invoke(
            model_id,
            prompt["user"],
            system=prompt["system"],
            max_tokens=500,
            temperature=0.0,
        )
        validation = validate_extraction(result["text"])
        rows.append(
            {
                "model": model_id,
                "latency_s": result["latency_seconds"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "valid_json": validation.is_valid,
                "warnings": len(validation.warnings),
            }
        )
    return rows


def print_comparison(rows):
    print(tabulate(rows, headers="keys", tablefmt="github"))
