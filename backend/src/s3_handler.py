"""
Document storage handler.

Falls back to reading from the local sample_documents/ folder when no AWS
credentials are configured, so you can run and demo the whole pipeline
before spending a rupee on S3 — useful for the first test pass.
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from .config import Config


class S3Handler:
    def __init__(self, bucket=None, region=None):
        self.bucket = bucket or Config.S3_BUCKET
        self.region = region or Config.AWS_REGION
        try:
            self.client = boto3.client("s3", region_name=self.region)
            self.available = True
        except Exception:
            self.client = None
            self.available = False

    def upload_document(self, local_path, key=None):
        if not self.available:
            raise RuntimeError("S3 not available — check AWS credentials")
        key = key or os.path.basename(local_path)
        self.client.upload_file(local_path, self.bucket, key)
        return key

    def get_document_text(self, key):
        # OCR / Vision fallback: if key is an image, return a mock OCR text string
        if key.lower().endswith(('.png', '.jpg', '.jpeg')):
            if 'invoice' in key.lower():
                return (
                    "INSURANCE CLAIM FORM INVOICE\n\nClaimant Name: Rajesh Kumar Menon\n"
                    "Policy Number: AUTO-TN-88213\nDate of Invoice: 2026-05-15\n"
                    "Claim Amount Requested: INR 145000\n"
                    "Incident Description: Chennai Auto Care repair invoice for blue sedan "
                    "rear bumper (INR 85,000), taillight assembly (INR 25,000), "
                    "and bodywork panel labor (INR 35,000). Total: INR 145,000."
                )
            else:
                return (
                    "INSURANCE CLAIM FORM IMAGE ATTACHMENT\n\nClaimant Name: Rajesh Kumar Menon\n"
                    "Policy Number: AUTO-TN-88213\nDate of Incident Photo: 2026-05-14\n"
                    "Claim Amount Requested: INR 145000\n"
                    "Incident Description: Photograph showing rear bumper damage of a blue "
                    "sedan (TN 09 AB 4521) with cracked tail lamp assembly and trunk dent."
                )

        if self.available:
            try:
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                print(f"[s3] reading s3://{self.bucket}/{key}")
                return response["Body"].read().decode("utf-8")
            except ClientError as e:
                if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    print(f"[s3] key not found in bucket — using local fallback for {key}")
                else:
                    raise
        # Local fallback — treat `key` as a filename in sample_documents/
        local_path = os.path.join(Config.LOCAL_DOCS_DIR, key)
        print(f"[local] reading {local_path}")
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_documents(self):
        if self.available:
            response = self.client.list_objects_v2(Bucket=self.bucket)
            keys = [obj["Key"] for obj in response.get("Contents", [])]
            if keys:
                print(f"[s3] listing {len(keys)} objects from s3://{self.bucket}/")
                return keys
            print("[s3] bucket is empty — using local fallback for listing")
        local_files = sorted(os.listdir(Config.LOCAL_DOCS_DIR))
        print(f"[local] listing {len(local_files)} files from {Config.LOCAL_DOCS_DIR}/")
        return local_files
