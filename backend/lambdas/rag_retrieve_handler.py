import os
from src.config import Config
from src.bedrock_client import BedrockClient
from src.rag_engine import PolicyRAG

def handler(event, context):
    print("Received event:", event)
    extracted_info = event["extracted_info"]
    claim_type = extracted_info.get("claim_type", "other")
    
    if os.getenv("BEDROCK_MOCK", "0") == "1":
        from src.mock_bedrock_client import MockBedrockClient
        bedrock = MockBedrockClient()
    else:
        bedrock = BedrockClient()
        
    # Use policy knowledge folder in workspace root (packaged in lambda CodeUri)
    policy_dir = os.path.join(os.path.dirname(__file__), "../policy_knowledge")
    if not os.path.exists(policy_dir):
        # Fallback for sam bundle where policy_knowledge is placed in code root
        policy_dir = "policy_knowledge"
        
    rag = PolicyRAG(bedrock, policy_dir)
    # Index policies
    n_chunks = rag.build_index()
    print(f"[rag] indexed {n_chunks} policy chunks")
    
    policy_context = rag.retrieve_as_context(f"{claim_type} claim coverage limits and exclusions")
    
    # Forward previous variables + RAG context
    event["policy_context"] = policy_context
    return event
