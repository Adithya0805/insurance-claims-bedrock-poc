import os
import time
from src.config import Config
from src.bedrock_client import BedrockClient
from src.prompt_templates import PromptTemplateManager

def handler(event, context):
    print("Received event:", event)
    extracted_info = event["extracted_info"]
    policy_context = event["policy_context"]
    key = event["key"]
    
    if os.getenv("BEDROCK_MOCK", "0") == "1":
        from src.mock_bedrock_client import MockBedrockClient
        bedrock = MockBedrockClient()
    else:
        bedrock = BedrockClient()
        
    templates = PromptTemplateManager()
    
    summary_prompt = templates.get(
        "generate_summary",
        extracted_info=extracted_info,
        policy_context=policy_context,
    )
    
    summary = bedrock.invoke(
        Config.SUMMARY_MODEL_ID or "anthropic.claude-3-sonnet-20240229-v1:0",
        summary_prompt["user"],
        system=summary_prompt["system"],
        max_tokens=300,
        temperature=0.4,
    )
    
    # Structure result ready for DynamoDB storage
    return {
        "document_id": key,
        "status": "processed",
        "extracted_info": extracted_info,
        "validation_warnings": event.get("validation_warnings", []),
        "injection_flags": event.get("injection_flags", []),
        "summary": summary["text"],
        "processed_timestamp": int(time.time()),
        "metrics": {
            "extraction_latency_s": event["extraction_metrics"]["latency_s"],
            "extraction_model": event["extraction_metrics"]["model"],
            "summary_latency_s": summary["latency_seconds"],
            "summary_model": summary["model_id"]
        }
    }
