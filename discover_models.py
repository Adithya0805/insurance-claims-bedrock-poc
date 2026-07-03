"""
Run this FIRST, before anything else.

Bedrock model IDs change faster than any tutorial can track, and they vary
by AWS account (depends on what model access you've been granted) and by
region. Never hardcode a model ID you found in a blog post — pull it live.

Usage:
    python discover_models.py
"""
import boto3

REGION = "us-east-1"  # change if you enabled Bedrock in a different region


def main():
    client = boto3.client("bedrock", region_name=REGION)

    print(f"\nAnthropic (Claude) models available in {REGION}:\n")
    resp = client.list_foundation_models(byProvider="anthropic")
    for m in resp["modelSummaries"]:
        modalities_in = m.get("inputModalities", [])
        modalities_out = m.get("outputModalities", [])
        print(f"  {m['modelId']:<55} in={modalities_in} out={modalities_out}")

    print(f"\nAmazon (Titan) embedding models available in {REGION}:\n")
    resp = client.list_foundation_models(byProvider="amazon")
    for m in resp["modelSummaries"]:
        if "embed" in m["modelId"].lower():
            print(f"  {m['modelId']}")

    print(
        "\nCopy the model IDs you want into your .env file:\n"
        "  EXTRACTION_MODEL_ID=<a fast/cheap Claude model, e.g. Haiku>\n"
        "  SUMMARY_MODEL_ID=<a stronger Claude model, e.g. Sonnet>\n"
        "  DOC_UNDERSTANDING_MODEL_ID=<a vision-capable Claude model>\n"
        "  EMBEDDING_MODEL_ID=<a Titan embedding model>\n"
    )
    print(
        "If this returns an AccessDeniedException, go to:\n"
        "  AWS Console -> Bedrock -> Model access -> Request access\n"
        "and enable the Anthropic and Amazon Titan models you plan to use.\n"
    )


if __name__ == "__main__":
    main()
