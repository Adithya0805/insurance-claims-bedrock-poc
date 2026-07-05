import os
from src.s3_handler import S3Handler

def handler(event, context):
    # event can be direct Step Functions input or triggered via S3 event
    print("Received event:", event)
    
    # Handle both direct execution or S3 trigger format
    if "Records" in event:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
    else:
        bucket = event.get("bucket")
        key = event.get("key")
        
    if not key:
        raise ValueError("Missing document key in event")
        
    s3 = S3Handler(bucket=bucket)
    text = s3.get_document_text(key)
    
    return {
        "document_id": key,
        "bucket": bucket,
        "key": key,
        "document_text": text
    }
