"""
Usage:
    python run_poc.py process claim_auto_001.txt
    python run_poc.py process claim_auto_001.txt --all         # process every sample doc
    python run_poc.py compare claim_auto_001.txt                # compare models on one doc
"""
import argparse
import json
from src.processor import ClaimProcessor
from src.s3_handler import S3Handler
from src.model_comparator import compare_extraction_models, print_comparison
from src.config import Config


def run_process(doc_key, all_docs):
    processor = ClaimProcessor()
    s3 = S3Handler()

    keys = s3.list_documents() if all_docs else [doc_key]
    for key in keys:
        print(f"\n{'=' * 60}\nProcessing: {key}\n{'=' * 60}")
        result = processor.process(key)
        print(json.dumps(result, indent=2, default=str))


def run_compare(doc_key):
    s3 = S3Handler()
    document_text = s3.get_document_text(doc_key)

    candidate_models = [
        m for m in [Config.EXTRACTION_MODEL_ID, Config.SUMMARY_MODEL_ID] if m
    ]
    if len(candidate_models) < 2:
        print(
            "Set at least two different model IDs (EXTRACTION_MODEL_ID, "
            "SUMMARY_MODEL_ID) in .env to compare, or edit run_poc.py to "
            "pass a custom list."
        )
        return

    rows = compare_extraction_models(document_text, candidate_models)
    print_comparison(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process")
    p_process.add_argument("document_key")
    p_process.add_argument("--all", action="store_true", dest="all_docs")

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("document_key")

    args = parser.parse_args()

    if args.command == "process":
        run_process(args.document_key, args.all_docs)
    elif args.command == "compare":
        run_compare(args.document_key)
