import os
from src.config import Config
from src.bedrock_client import BedrockClient
from src.content_validator import validate_extraction, check_prompt_injection
from src.prompt_templates import PromptTemplateManager

def handler(event, context):
    print("Received event:", event)
    document_text = event["document_text"]
    key = event["key"]
    
    # Initialize components
    # If BEDROCK_MOCK=1 is active, we use the Mock client
    if os.getenv("BEDROCK_MOCK", "0") == "1":
        from src.mock_bedrock_client import MockBedrockClient
        bedrock = MockBedrockClient()
    else:
        bedrock = BedrockClient()
        
    templates = PromptTemplateManager()
    
    injection_flags = check_prompt_injection(document_text)
    if injection_flags:
        print(f"[validator] WARNING: possible injection markers: {injection_flags}")
        
    extract_prompt = templates.get("extract_info", document_text=document_text)
    extraction = bedrock.invoke(
        Config.EXTRACTION_MODEL_ID or "anthropic.claude-3-haiku-20240307-v1:0",
        extract_prompt["user"],
        system=extract_prompt["system"],
        max_tokens=500,
        temperature=0.0,
    )
    
    validation = validate_extraction(extraction["text"])
    if not validation.is_valid:
        return {
            "document_id": key,
            "key": key,
            "status": "extraction_failed",
            "errors": validation.errors,
            "raw_output": extraction["text"]
        }
        
    return {
        "document_id": key,
        "key": key,
        "status": "success",
        "extracted_info": validation.parsed,
        "validation_warnings": validation.warnings,
        "injection_flags": injection_flags,
        "extraction_metrics": {
            "latency_s": extraction["latency_seconds"],
            "model": extraction["model_id"]
        }
    }
