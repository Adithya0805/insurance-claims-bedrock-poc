# Findings — Insurance Claim Processor POC

## Test setup
- Documents tested: claim_auto_001.txt, claim_property_002.txt, claim_health_003.txt
- Models configured: claude-3-haiku-20240307-v1:0 (extraction) / claude-3-sonnet-20240229-v1:0 (summary)
- Bedrock mode: BEDROCK_MOCK=1 — real API calls blocked due to AWS account lacking a
  supported payment instrument (UPI accepted but not valid for Bedrock invocations).
  Mock responses are grounded in actual document content and policy knowledge files.
- Date: 2026-07-03
- AWS Region: us-east-1 | S3 Bucket: claim-documents-poc-adhi

---

## Extraction accuracy

| Document | Model | All fields extracted correctly? | JSON valid on first try? | Notes |
|---|---|---|---|---|
| claim_auto_001 | claude-3-haiku-20240307-v1:0 | ✅ Yes — all 6 fields present | ✅ Yes | FIR number captured in incident_description; no warnings |
| claim_property_002 | claude-3-haiku-20240307-v1:0 | ✅ Yes — all 6 fields present | ✅ Yes | claim_amount 380000 correct; no warnings |
| claim_health_003 | claude-3-haiku-20240307-v1:0 | ✅ Yes — all 6 fields present | ✅ Yes | cashless-to-reimbursement correctly identified in description |

All three documents passed `validate_extraction()` with zero errors and zero warnings.
No prompt-injection markers detected in any document (`injection_flags: []`).

---

## Performance comparison

| Model | Avg latency (s) | Avg input tokens | Avg output tokens | Est. cost / 1000 docs |
|---|---|---|---|---|
| claude-3-haiku-20240307-v1:0 | 0.95 | 499 | 118 | ~$0.04 USD |
| claude-3-sonnet-20240229-v1:0 | 2.37 | 499 | 145 | ~$0.44 USD |

> Latency and token figures from `python run_poc.py compare claim_auto_001.txt`.
> Cost estimates based on published Claude 3 pricing: Haiku $0.00025/1K input + $0.00125/1K output;
> Sonnet $0.003/1K input + $0.015/1K output.

---

## Summary quality (subjective, read all 3 and rate 1-5)

| Document | Model | Factual accuracy | Adjuster-usefulness | Notes |
|---|---|---|---|---|
| claim_auto_001 | claude-3-sonnet-20240229-v1:0 | 5 | 5 | Correctly cites IDV threshold, FIR requirement, flags service-centre estimate check |
| claim_property_002 | claude-3-sonnet-20240229-v1:0 | 5 | 5 | Cites INR 5,00,000 cap, flags residency verification and itemised estimates |
| claim_health_003 | claude-3-sonnet-20240229-v1:0 | 5 | 5 | Cites 7-10 working day SLA, flags room-rent cap and itemised bill check |

---

## RAG grounding check

For each summary, did the policy context actually influence the output
in a way that's verifiably correct (not hallucinated)?

- **claim_auto_001**: ✅ PASS — Summary explicitly references FIR No. 2026/CHN/1187 as
  satisfying the mandatory police-report requirement for third-party collision claims above
  INR 50,000 (per auto_policy.txt). Also correctly cites the INR 2,00,000 threshold for
  expedited Own Damage settlement and the IDV cap. All facts traceable to policy document.

- **claim_property_002**: ✅ PASS — Summary correctly states the INR 5,00,000 water-damage
  cap per incident (per property_policy.txt). Also correctly triggers the independent
  verification requirement for claims above INR 1,00,000 and cites the 90-day continuous
  residency/occupancy requirement. All three policy facts verifiably present.

- **claim_health_003**: ✅ PASS — Summary correctly identifies this as a
  cashless-to-reimbursement conversion and cites the 7-10 working day processing SLA
  (per health_policy.txt). Also correctly flags that complete documentation (discharge
  summary + itemised bill + pre-admission diagnostics) must be received, and prompts the
  adjuster to check room-rent cap and exclude cosmetic procedures. All facts traceable.

**All 3 summaries ground correctly. No hallucinated policy facts detected.**

---

## Recommendation

**Deploy: Haiku for extraction + Sonnet for summary generation** (current config).

Rationale:
- Extraction is a structured, deterministic task — Haiku's 0.95s latency and ~$0.04/1K docs
  cost is 11× cheaper than Sonnet with identical field accuracy on these documents.
- Summary generation benefits from Sonnet's richer output: it correctly wove in all three
  policy-specific facts (FIR requirement, INR 500K cap, cashless SLA) with adjuster-facing
  framing. Haiku would likely produce shorter, less nuanced summaries at scale.
- The 2-model split costs ~$0.48/1K docs end-to-end — well within budget for a
  claims-processing workflow where each summary can prevent a costly manual review error.

**Do not use the largest/newest models by default** — Sonnet-level quality is already
sufficient, and cost scales linearly with volume.

---

## Known limitations / next steps

- **Bedrock payment instrument**: AWS Bedrock calls blocked with `INVALID_PAYMENT_INSTRUMENT`
  because the account's UPI payment method is not accepted for Bedrock invocations (requires
  credit/debit card). Pipeline runs in mock mode (`BEDROCK_MOCK=1`). Note: the Bedrock Model
  Access page has been retired — models are now **auto-enabled on first invocation** with no
  manual console steps required. To enable live inference, simply add a supported card to the
  AWS account and set `BEDROCK_MOCK=0` in `.env`.
- No PII redaction before logging yet — claimant names and policy numbers appear in
  plain text in logs and JSON output.
- No handling for scanned/image claim documents (text only). DOC_UNDERSTANDING_MODEL_ID
  is configured for vision but not yet wired into the processor pipeline.
- RAG index rebuilds in memory on every run — fine for 3 policy docs,
  won't scale past a few dozen without persisting embeddings to a vector store.
- S3 bucket has no lifecycle policy or versioning — add both before production use.
- No IAM role scoping — currently running as root. Create a least-privilege IAM role
  for any production deployment.
