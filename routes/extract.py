from flask import Blueprint, request, jsonify
import time
import logging
from services.extraction_service import process_job_content
# from services.auth_service import verify_user

extract_blueprint = Blueprint('extract', __name__)

@app.route('/api/extract-job-data', methods=['POST'])
def extract_job_data():
    start_time = time.time()
    try:
        # Disable authentication for testing
        # auth_header = request.headers.get('Authorization')
        # token = None
        # if auth_header and auth_header.startswith('Bearer '):
        #     token = auth_header.split(' ')[1]
        
        # user = None
        # error_message = None
        # if token:
        #     user, error_message = verify_user(token)
        #     if error_message and token:
        #         return jsonify({"error": error_message}), 401

        user = None  # Explicitly set user to None to skip usage logging

        # Get input data
        data = request.json
        
        if not data or ('html' not in data and 'text' not in data):
            return jsonify({"error": "You must provide either HTML or text content"}), 400
        
        # Process the input
        content = data.get('html', '') or data.get('text', '')
        job_data = process_job_content(content, data.get('html') is not None)
        
        # Log processing time
        processing_time = time.time() - start_time
        logging.info(f"Processed job data in {processing_time:.2f} seconds")
        
        # Skip usage update since auth is disabled
        # if user:
        #     users_collection.update_one(
        #         {"_id": user["_id"]},
        #         {"$inc": {"extractionCount": 1}}
        #     )
        
        return jsonify(job_data), 200
    except Exception as e:
        logging.error(f"Error processing job data: {str(e)}")
        return jsonify({"error": "Failed to extract job data", "details": str(e)}), 500

