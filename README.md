# Insurance Claim Document Processor — Bedrock POC

Automates extraction and summarization of insurance claim documents using
Amazon Bedrock, with a lightweight RAG layer grounding summaries in actual
policy coverage terms instead of letting the model guess.

## Architecture

```
S3 (claim documents)
    -> Lambda trigger (S3 event)
        -> Bedrock: extraction (Claude Haiku 4.5)      -> structured JSON
        -> Policy RAG (Titan embeddings + policy KB)   -> coverage context
            -> Bedrock: summary generation (Claude Sonnet 5)
                -> Output store (S3 JSON + DynamoDB)
```

Two Bedrock calls per document, not one: a cheap/fast model for structured
extraction, a stronger model for the prose an adjuster actually reads. This
also gives you a natural A/B point for Step 4 (compare model performance).

**Model choices and why:**

| Stage | Model | Reasoning |
|---|---|---|
| Extraction | Claude Haiku 4.5 | Structured JSON extraction is cheap/mechanical — don't pay Sonnet prices |
| Summary generation | Claude Sonnet 5 | Prose quality and reasoning about policy fit matter here |
| Document understanding (scanned forms) | Claude Sonnet 5 (vision) | Only needed if you extend to image/PDF input — see extensions |
| Embeddings | Titan Text Embeddings v2 | Native to Bedrock, no extra vendor dependency |

Model IDs change frequently and depend on what your AWS account has been
granted. Don't trust any ID in a tutorial (including this one) — run
`discover_models.py` first.

## Setup

```bash
# 1. Create the S3 bucket
aws s3 mb s3://claim-documents-poc-<your-initials>

# 2. Install dependencies
pip install -r requirements.txt

# 3. Enable model access
# AWS Console -> Bedrock -> Model access -> request Anthropic + Amazon Titan models

# 4. Discover exact model IDs available to your account
python discover_models.py

# 5. Copy and fill in your config
cp .env.example .env
# paste model IDs from step 4, set your bucket name
```

## Running it

The pipeline works against local files in `sample_documents/` with zero AWS
setup beyond Bedrock model access — useful for your first test pass before
you touch S3 billing at all.

```bash
# Process one document
python run_poc.py process claim_auto_001.txt

# Process all sample documents
python run_poc.py process claim_auto_001.txt --all

# Compare extraction/summary models on the same document
python run_poc.py compare claim_auto_001.txt
```

To run against real S3 instead of local files: upload the sample docs
(`aws s3 cp sample_documents/ s3://your-bucket/ --recursive`), and
`S3Handler` will detect valid AWS credentials automatically and switch
from local fallback to S3.

## Project structure

```
src/
  config.py             # env-driven config, fails loudly if model IDs unset
  bedrock_client.py      # Converse API wrapper + Titan embeddings
  s3_handler.py           # S3 I/O with local-file fallback for cheap testing
  prompt_templates.py     # Step 3: reusable prompt template manager
  rag_engine.py            # Step 2: simple in-memory RAG over policy docs
  content_validator.py     # Step 3: JSON structure + injection-marker checks
  processor.py              # orchestrates the full pipeline
  model_comparator.py        # Step 4: side-by-side model comparison
sample_documents/            # 3 synthetic claims (auto/property/health)
policy_knowledge/             # synthetic policy excerpts, grounds the RAG step
discover_models.py             # run first — lists real model IDs for your account
run_poc.py                      # CLI entry point
FINDINGS_TEMPLATE.md             # fill this in for the Step 4 deliverable
```

## Cost management

- Set a billing alert before you run this against real Bedrock calls:
  AWS Console -> Billing -> Budgets -> create a $5 budget with an alert.
- Haiku-class models cost a fraction of Sonnet-class per token — the
  extraction step alone processing 3 sample docs will cost well under $0.01.
- `aws s3 rb s3://your-bucket --force` and delete the Bedrock model access
  grants when you're done, per the assignment's cleanup instructions.

## Extending this (bonus challenges from the assignment)

- **Flask web interface**: wrap `ClaimProcessor.process()` in a single
  `/process` POST route — the processor is already decoupled from any
  particular entry point.
- **Content filtering for PII**: extend `content_validator.py` — you
  already have `claimant_name`/contact info isolated post-extraction,
  so redaction before logging is a small addition.
- **Feedback mechanism**: log `(document_key, model_id, adjuster_correction)`
  tuples to a DynamoDB table; that becomes eval data for prompt tuning later.
- **Scanned/image claims**: swap the extraction call to pass the document
  as an image content block instead of text, using a vision-capable model —
  the `BedrockClient.invoke()` signature would need a `document_bytes` param.
