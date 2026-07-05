# Insurance Claim Document Processor — Bedrock POC

Automates extraction and summarization of insurance claim documents using Amazon Bedrock, with a lightweight RAG layer grounding summaries in actual policy coverage terms instead of letting the model guess.

## Architecture

This project is deployed as serverless AWS infrastructure using **AWS SAM** and **AWS Step Functions**:

```
S3 (claim-documents-poc-adhi)
  -> S3 Event (Object Created)
    -> EventBridge Rule (S3TriggerClaimProcessing)
      -> Step Functions State Machine (ClaimProcessingStateMachine)
         1. OCRState (OcrHandlerFunction Lambda)
         2. ClassifyExtractState (ExtractClassifyFunction Lambda)
         3. CheckExtractionStatusState (Choice Branch: fails -> DynamoDB)
         4. RAGRetrieveState (RagRetrieveFunction Lambda)
         5. SummarizeTranslateState (SummarizeTranslateFunction Lambda)
         6. WriteToDynamoDBState (Writes final report to DynamoDB: ClaimResults)
```

## Setup & Local Verification

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Discover model IDs
python discover_models.py

# 3. Verify the handlers run correctly locally
python scratch/verify_handlers.py
```

## Serverless Deployment

We use the AWS Serverless Application Model (SAM) to build and deploy:

```bash
# 1. Build the serverless package
sam build

# 2. Deploy to AWS Cloud
sam deploy --stack-name insurance-claims-bedrock-poc-stack --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-htih1xarifd5 --capabilities CAPABILITY_IAM --region us-east-1 --no-confirm-changeset
```

## Running the Serverless Pipeline (End-to-End)

Once deployed, the pipeline is fully event-driven and triggers automatically when you copy files to S3:

```bash
# 1. Upload a claim document to S3
aws s3 cp sample_documents/claim_property_002.txt s3://claim-documents-poc-adhi/

# 2. List the active Step Functions executions
aws stepfunctions list-executions --state-machine-arn <state-machine-arn>

# 3. Scan the DynamoDB table to retrieve the generated claim report
aws dynamodb scan --table-name ClaimResults
```

## Running the Web Dashboard (Local Adjuster Portal)

To run the Flask Adjuster dashboard:

```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser to view visual scan uploads, check real-time claimant fraud shield gauges, edit facts, and approve ledger payouts!

## Project structure

```
backend/
  lambdas/               # Serverless AWS Lambda handler modules
  src/                   # Core shared backend code package
  policy_knowledge/      # Policy coverage documents used in RAG
  requirements.txt       # Clean Python backend dependencies
app.py                   # Flask Local Adjuster dashboard server
static/                  # Web dashboard UI files (HTML, CSS, JS)
template.yaml            # AWS SAM Serverless template mapping resources
.samignore               # SAM zipping exclusion rules
EXECUTION_LOG.md         # Sequential execution logs
SERVERLESS_MIGRATION.md  # Serverless migration notes and costs
```

## Cost management

- The serverless stack operates **100% inside the AWS Free Tier** for testing scale:
  - AWS Lambda: 1 Million requests/month free.
  - AWS DynamoDB: 25 RCUs / WCUs free (permanent).
  - AWS Step Functions: 4,000 state transitions/month free.
  - Bedrock: Configured to run `BEDROCK_MOCK=1` in our global stack template to avoid payment/instrument blocker fees.
- Clean up resources when done:
  - CloudFormation stack: `sam delete`
  - S3 bucket: `aws s3 rb s3://claim-documents-poc-adhi --force`
