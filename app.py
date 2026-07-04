import os
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

# Import backend POC functions
from src.processor import ClaimProcessor
from src.s3_handler import S3Handler
from src.model_comparator import compare_extraction_models
from src.config import Config

app = Flask(__name__, static_folder='static', static_url_path='')

# Ensure we validate config first
Config.validate()

# Initialize handlers
s3 = S3Handler()
processor = ClaimProcessor()

# Serve Frontend SPA
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# API: List all claims in S3 (or fallback local files)
@app.route('/api/claims', methods=['GET'])
def list_claims():
    try:
        keys = s3.list_documents()
        return jsonify({"status": "success", "claims": keys})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Get raw text of a specific claim
@app.route('/api/claims/<path:key>', methods=['GET'])
def get_claim_text(key):
    try:
        text = s3.get_document_text(key)
        return jsonify({"status": "success", "text": text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Upload a new claim file to S3
@app.route('/api/claims/upload', methods=['POST'])
def upload_claim():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Empty filename"}), 400
    
    filename = secure_filename(file.filename)
    
    # Save file locally first, then upload
    temp_dir = os.path.join(os.path.dirname(__file__), 'scratch')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        file.save(temp_path)
        # Upload to S3 (uses local fallback if AWS not ready)
        s3.upload_document(temp_path, key=filename)
        # Remove temp file
        os.remove(temp_path)
        return jsonify({"status": "success", "filename": filename})
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Process claim with Bedrock & RAG
@app.route('/api/claims/process/<path:key>', methods=['POST'])
def process_claim(key):
    try:
        # Check optional models overrides
        data = request.get_json(silent=True) or {}
        extraction_model = data.get('extraction_model', Config.EXTRACTION_MODEL_ID)
        summary_model = data.get('summary_model', Config.SUMMARY_MODEL_ID)
        
        result = processor.process(
            key, 
            extraction_model=extraction_model, 
            summary_model=summary_model
        )
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Compare models (Haiku vs Sonnet)
@app.route('/api/claims/compare/<path:key>', methods=['GET'])
def compare_models(key):
    try:
        document_text = s3.get_document_text(key)
        candidate_models = [
            m for m in [Config.EXTRACTION_MODEL_ID, Config.SUMMARY_MODEL_ID] if m
        ]
        if len(candidate_models) < 2:
            return jsonify({
                "status": "error", 
                "message": "Set at least two different model IDs in .env to compare."
            }), 400
            
        rows = compare_extraction_models(document_text, candidate_models)
        return jsonify({"status": "success", "comparison": rows})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# API: Serve raw image content for S3 or local fallback
@app.route('/api/claims/image/<path:key>', methods=['GET'])
def get_claim_image(key):
    try:
        if s3.available:
            # Fetch directly from S3
            response = s3.client.get_object(Bucket=s3.bucket, Key=key)
            return response['Body'].read(), 200, {'Content-Type': 'image/png'}
        
        # Local fallback
        local_path = os.path.join(Config.LOCAL_DOCS_DIR, key)
        return send_from_directory(Config.LOCAL_DOCS_DIR, key, mimetype='image/png')
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 404

# API: Fraud Shield Checker
@app.route('/api/claims/fraud-check/<path:key>', methods=['POST'])
def check_fraud(key):
    try:
        data = request.get_json(silent=True) or {}
        claimant = data.get('claimant_name', '')
        policy = data.get('policy_number', '')
        amount = float(data.get('claim_amount', 0))

        risk_score = 0
        reasons = []

        # List all other claims in S3 (excluding current key)
        all_keys = s3.list_documents()
        for other_key in all_keys:
            if other_key == key:
                continue
            
            # Simple check: does the other claim text contain matching identifiers?
            text = s3.get_document_text(other_key).lower()
            
            if claimant.lower() and claimant.lower() in text:
                risk_score += 45
                reasons.append(f"Matching claimant '{claimant}' found in file '{other_key}'")
            if policy.lower() and policy.lower() in text:
                risk_score += 50
                reasons.append(f"Matching policy number '{policy}' found in file '{other_key}'")
            
        # Limit score to 100 max
        risk_score = min(risk_score, 100)
        
        return jsonify({
            "status": "success",
            "risk_score": risk_score,
            "reasons": reasons
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # Run locally on port 5000
    app.run(debug=True, host='127.0.0.1', port=5000)
