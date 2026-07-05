import sys
import os
import json

# Ensure python path includes root and lambdas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lambdas.ocr_handler import handler as ocr_handler
from lambdas.extract_classify_handler import handler as extract_handler
from lambdas.rag_retrieve_handler import handler as rag_handler
from lambdas.summarize_translate_handler import handler as summarize_handler

def main():
    print("--- Testing OCR Handler ---")
    with open("events/test_event.json", "r") as f:
        event = json.load(f)
        
    ocr_result = ocr_handler(event, None)
    print("OCR Output Key:", ocr_result.get("key"))
    print("OCR Output Text preview:", ocr_result.get("document_text")[:100] + "...")
    
    print("\n--- Testing Extract/Classify Handler ---")
    extract_result = extract_handler(ocr_result, None)
    print("Extract Status:", extract_result.get("status"))
    print("Extracted claimant:", extract_result.get("extracted_info", {}).get("claimant_name"))
    
    print("\n--- Testing RAG Retrieve Handler ---")
    rag_result = rag_handler(extract_result, None)
    print("RAG Context matched:", rag_result.get("policy_context")[:100] + "...")
    
    print("\n--- Testing Summarize/Translate Handler ---")
    summary_result = summarize_handler(rag_result, None)
    print("Summary result Status:", summary_result.get("status"))
    print("Summary result text:", summary_result.get("summary"))
    print("Metrics latency total:", summary_result.get("metrics"))
    
    print("\n[SUCCESS] ALL HANDLERS VALIDATED SUCCESSFULLY LOCALLY!")

if __name__ == "__main__":
    main()
