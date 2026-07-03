import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET = os.getenv("S3_BUCKET", "claim-documents-poc-adhi")

    EXTRACTION_MODEL_ID = os.getenv("EXTRACTION_MODEL_ID", "")
    SUMMARY_MODEL_ID = os.getenv("SUMMARY_MODEL_ID", "")
    DOC_UNDERSTANDING_MODEL_ID = os.getenv("DOC_UNDERSTANDING_MODEL_ID", "")
    EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

    LOCAL_DOCS_DIR = "sample_documents"
    LOCAL_POLICY_DIR = "policy_knowledge"

    @classmethod
    def validate(cls):
        missing = [
            name
            for name in ["EXTRACTION_MODEL_ID", "SUMMARY_MODEL_ID"]
            if not getattr(cls, name)
        ]
        if missing:
            raise ValueError(
                f"Missing required config: {missing}. "
                f"Run `python discover_models.py` first, then set these in .env"
            )
