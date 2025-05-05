"""
Main application entry point for the Job Data Extraction API.
"""
import os
import time
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import extraction service
from services.extraction_service import process_job_content

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/', methods=['GET'])
def index():
    """Root endpoint - health check and API info"""
    return jsonify({
        "status": "online",
        "service": "Job Data Extraction API",
        "version": "1.0.0",
        "endpoints": {
            "/api/extract-job-data": "POST - Extract structured data from job posting HTML or text"
        }
    })

@app.route('/api/extract-job-data', methods=['POST'])
def extract_job_data():
    """
    Extract structured job data from HTML or text content.
    
    Expects JSON with either 'html' or 'text' field.
    Returns structured job data.
    """
    start_time = time.time()
    
    try:
        # Get input data
        data = request.json
        
        if not data:
            return jsonify({
                "error": "No data provided"
            }), 400
        
        # Check if we have either HTML or text content
        if 'html' not in data and 'text' not in data and 'url' not in data:
            return jsonify({
                "error": "You must provide either 'html', 'text', or 'url' field"
            }), 400
        
        # Process the input
        if 'html' in data:
            job_data = process_job_content(data['html'], is_html=True)
        elif 'text' in data:
            job_data = process_job_content(data['text'], is_html=False)
        elif 'url' in data:
            # This would be a future enhancement
            return jsonify({
                "error": "URL processing not implemented yet"
            }), 501
        
        # Log processing time
        processing_time = time.time() - start_time
        logger.info(f"Processed job data in {processing_time:.2f} seconds")
        
        return jsonify(job_data), 200
        
    except Exception as e:
        logger.error(f"Error processing job data: {str(e)}")
        return jsonify({
            "error": "Failed to extract job data", 
            "details": str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "Please refer to the API documentation for available endpoints"
    }), 404

@app.errorhandler(405)
def method_not_allowed(e):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": "Please check the HTTP method for this endpoint"
    }), 405

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later."
    }), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Job Data Extraction API on {host}:{port} (debug: {debug})")
    app.run(host=host, port=port, debug=debug)