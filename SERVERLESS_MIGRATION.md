# Serverless Migration Report — AWS SAM & Step Functions

## Overview

This report documents the migration of the Insurance Claim Document processing pipeline from a local Python runner to a fully event-driven, serverless infrastructure on AWS.

## Architecture Diagram

```
[Claim Uploaded] -> S3 Bucket (claim-documents-poc-adhi)
                           |
                     (Object Created)
                           v
               Amazon EventBridge Rule
                           |
                    (Trigger State Machine)
                           v
              AWS Step Functions Orchestrator
                (ClaimProcessingStateMachine)
                           |
        +------------------+------------------+
        |                  |                  |
   [OCR Lambda]    [Extract Lambda]    [RAG Lambda]
        |                  |                  |
        +------------------+------------------+
                           |
                [Summarize/Translate Lambda]
                           |
                           v
              AWS DynamoDB (ClaimResults)
```

## Key Changes & Design Choices

1. **Modular AWS Lambdas:** 
   We decoupled the pipeline into 4 single-responsibility Lambda functions:
   * **`OcrHandlerFunction`:** Fetches document content from S3 and performs initial parsing.
   * **`ExtractClassifyFunction`:** Uses Claude to parse structured facts (claimant, amount, dates).
   * **`RagRetrieveFunction`:** Uses PolicyRAG to index policies and fetch relevant coverage rules.
   * **`SummarizeTranslateFunction`:** Generates the final adjuster summary and report.

2. **Step Functions State Machine Orchestration:**
   * Replaced the local procedural script orchestration with a robust Cloud orchestrator.
   * Included **Choice branching** to automatically separate valid extractions from validation failures, routing failures to failure tables instead of breaking execution.
   * Configured **Catch/Try blocks** on all states to log unexpected infrastructure failures directly to DynamoDB for audit logging.

3. **Event-Driven EventBridge S3 Trigger:**
   * Configured S3 to publish EventBridge notifications.
   * Created an EventBridge Rule that automatically starts Step Functions executions on new file uploads.
   * Handled S3 input mapping using **EventBridge Input Transformers** (mapping bucket names and keys straight into the OCR state input parameters).

4. **DynamoDB Write Integration:**
   * Integrated Step Functions directly with DynamoDB (`arn:aws:states:::dynamodb:putItem`), writing success states, general failures, and extraction validations natively without executing any custom database script.

## Packaging Optimization

* **Challenge:** The initial workspace contained global Python installation binaries (1.25 GB), which bloated SAM's zipping process.
* **Solution:** Decoupled the code into a clean `backend/` directory containing only handler code and shared modules.
* **Optimization:** Replaced the heavy `numpy` dependency in the RAG similarity engine with 100% pure Python calculations, and removed `boto3` (pre-installed in AWS Lambda).
* **Result:** Reduced the deployment package size from **1.25 GB** to **10 MB** (99.2% reduction), ensuring instant uploads and fast cold starts.

## AWS Cost Breakdown

All resources used are **100% covered by the AWS Free Tier**. Total cost incurred: **$0.00**.

| Resource | Free Tier Limit | Actual Usage | Cost |
|---|---|---|---|
| **AWS Lambda** | 1,000,000 requests/month | ~10 executions | $0.00 |
| **AWS Step Functions** | 4,000 state transitions/month | ~40 transitions | $0.00 |
| **AWS DynamoDB** | 25 GB Storage / 25 RCU/WCU | ~5 Read/Writes | $0.00 |
| **Amazon EventBridge** | 1,000,000 free events/month | ~10 events | $0.00 |
| **Amazon S3** | 5 GB standard storage (12 months) | < 5 MB storage | $0.00 |
| **Amazon Bedrock** | Account-wide requests | Mock Mode Active (`BEDROCK_MOCK=1`) | $0.00 |
| **Total Incurred** | | | **$0.00** |
