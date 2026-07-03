"""
Thin wrapper around Bedrock.

Uses the Converse API instead of the older InvokeModel + provider-specific
body format. Converse gives you the same request/response shape across every
model family on Bedrock (Anthropic, Amazon, Meta, etc.), so switching models
for the comparison step in Step 4 is a one-line change, not a rewrite.
"""
import json
import time
import boto3
from .config import Config


class BedrockClient:
    def __init__(self, region=None):
        self.region = region or Config.AWS_REGION
        self.runtime = boto3.client("bedrock-runtime", region_name=self.region)

    def invoke(self, model_id, prompt, system=None, max_tokens=1000, temperature=0.0):
        """
        Calls a Claude model via Converse. Returns text output plus basic
        usage/latency metrics — useful later for the model comparison step.
        """
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        kwargs = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = [{"text": system}]

        start = time.time()
        response = self.runtime.converse(**kwargs)
        elapsed = time.time() - start

        output_text = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})

        return {
            "text": output_text,
            "input_tokens": usage.get("inputTokens"),
            "output_tokens": usage.get("outputTokens"),
            "latency_seconds": round(elapsed, 2),
            "model_id": model_id,
        }

    def embed(self, text, model_id=None):
        """
        Titan embeddings still use InvokeModel (Converse doesn't cover
        embedding models) — this returns a plain float vector.
        """
        model_id = model_id or Config.EMBEDDING_MODEL_ID
        body = json.dumps({"inputText": text[:8000]})  # Titan input cap
        response = self.runtime.invoke_model(modelId=model_id, body=body)
        payload = json.loads(response["body"].read())
        return payload["embedding"]
