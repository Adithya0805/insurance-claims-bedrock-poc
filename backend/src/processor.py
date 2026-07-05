"""
End-to-end claim processor:
S3/local doc -> Bedrock extraction -> validation -> RAG policy lookup ->
Bedrock summary generation -> structured result.
"""
from .config import Config
from .bedrock_client import BedrockClient
from .mock_bedrock_client import MockBedrockClient
from .s3_handler import S3Handler
from .prompt_templates import PromptTemplateManager
from .rag_engine import PolicyRAG
from .content_validator import validate_extraction, check_prompt_injection
import os


class ClaimProcessor:
    def __init__(self):
        Config.validate()
        if os.getenv("BEDROCK_MOCK", "0") == "1":
            print("[mock] BEDROCK_MOCK=1 — using MockBedrockClient (no real AWS Bedrock calls)")
            self.bedrock = MockBedrockClient()
        else:
            self.bedrock = BedrockClient()
        self.s3 = S3Handler()
        self.templates = PromptTemplateManager()
        self.rag = PolicyRAG(self.bedrock, Config.LOCAL_POLICY_DIR)
        self._rag_ready = False

    def _ensure_rag_index(self):
        if not self._rag_ready:
            n_chunks = self.rag.build_index()
            print(f"[rag] indexed {n_chunks} policy chunks")
            self._rag_ready = True

    def process(self, document_key, extraction_model=None, summary_model=None):
        extraction_model = extraction_model or Config.EXTRACTION_MODEL_ID
        summary_model = summary_model or Config.SUMMARY_MODEL_ID

        document_text = self.s3.get_document_text(document_key)

        injection_flags = check_prompt_injection(document_text)
        if injection_flags:
            print(f"[validator] WARNING: possible injection markers: {injection_flags}")

        extract_prompt = self.templates.get("extract_info", document_text=document_text)
        extraction = self.bedrock.invoke(
            extraction_model,
            extract_prompt["user"],
            system=extract_prompt["system"],
            max_tokens=500,
            temperature=0.0,
        )

        validation = validate_extraction(extraction["text"])
        if not validation.is_valid:
            return {
                "document_key": document_key,
                "status": "extraction_failed",
                "errors": validation.errors,
                "raw_output": extraction["text"],
            }

        self._ensure_rag_index()
        claim_type = validation.parsed.get("claim_type", "")
        policy_context = self.rag.retrieve_as_context(
            f"{claim_type} claim coverage limits and exclusions"
        )

        summary_prompt = self.templates.get(
            "generate_summary",
            extracted_info=validation.parsed,
            policy_context=policy_context,
        )
        summary = self.bedrock.invoke(
            summary_model,
            summary_prompt["user"],
            system=summary_prompt["system"],
            max_tokens=300,
            temperature=0.4,
        )

        return {
            "document_key": document_key,
            "status": "success",
            "extracted_info": validation.parsed,
            "validation_warnings": validation.warnings,
            "injection_flags": injection_flags,
            "summary": summary["text"],
            "metrics": {
                "extraction_latency_s": extraction["latency_seconds"],
                "summary_latency_s": summary["latency_seconds"],
                "extraction_model": extraction_model,
                "summary_model": summary_model,
            },
        }
