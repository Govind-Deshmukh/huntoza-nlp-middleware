"""
app.py - Job Data Extraction Service with Ollama Integration

This Flask application provides a focused API endpoint for job data extraction
from job descriptions using Ollama LLM with fallback to rule-based extraction.
"""
import os
import time
import logging
import json
import re
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', 240))
def check_ollama_availability():
    """Check if Ollama is available and running"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def extract_with_ollama(job_description):
    """
    Extract job data using Ollama model
    
    Args:
        job_description (str): Job description text
        
    Returns:
        dict: Extracted job data or None if processing failed
    """
    if not check_ollama_availability():
        logger.warning("Ollama is not available. Using fallback methods.")
        return None
        
    # Build extraction prompt specifically for our job schema
    prompt = """You are an AI assistant that extracts structured job information from job descriptions.

Extract the following information from the job description and return it as valid JSON:

{
  "company": "string - company name",
  "position": "string - job title/position", 
  "jobLocation": "string - job location (city, state or 'remote')",
  "jobType": "string - one of: full-time, part-time, contract, internship, remote, other",
  "salary": {
    "min": number - minimum salary (0 if not specified),
    "max": number - maximum salary (0 if not specified), 
    "currency": "string - currency code (INR, USD, EUR, etc.)"
  },
  "jobDescription": "string - cleaned and summarized job description (max 500 words)",
  "priority": "string - one of: low, medium, high (based on job attractiveness)",
  "notes": "string - any additional important details for job seekers"
}

Rules:
- Extract only factual information from the text
- If salary is not mentioned, set min and max to 0  
- If location suggests remote work, use 'remote' as jobLocation
- Summarize the job description to focus on key responsibilities and requirements
- Be concise and factual
- Return ONLY valid JSON, no other text"""

    # Truncate job description if too long
    max_desc_length = 2000
    if len(job_description) > max_desc_length:
        job_description = job_description[:max_desc_length]
        
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{prompt}\n\nJOB DESCRIPTION:\n'''\n{job_description}\n'''",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1024,
                }
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Error from Ollama API: {response.text}")
            return None
            
        result = response.json()
        generated_text = result.get('response', '')
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{\s*"[\w]+"\s*:[\s\S]*}', generated_text)
            if json_match:
                json_str = json_match.group(1) or json_match.group(0)
                return json.loads(json_str)
            else:
                # Try to parse entire response as JSON
                return json.loads(generated_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Ollama response")
            return None
                
    except requests.RequestException as e:
        logger.error(f"Error communicating with Ollama: {e}")
        return None

def fallback_extraction(job_description):
    """
    Fallback extraction using rule-based methods when Ollama is unavailable
    
    Args:
        job_description (str): Job description text
        
    Returns:
        dict: Extracted job data using simple pattern matching
    """
    text_lower = job_description.lower()
    
    # Company extraction patterns
    company = ""
    company_patterns = [
        r'(?:company|organization|employer)[\s:]+([A-Za-z0-9\s\-\&\.]+)',
        r'(?:at|with|for|by)\s+([A-Za-z0-9\s\-\&\.]+?)(?:\s+is|\s+are|\s+has|\s+have)',
        r'about\s+([A-Za-z0-9\s\-\&\.]+?)(?:\n|\.|,|:)'
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text_lower)
        if match:
            company = match.group(1).strip()
            if 3 < len(company) < 50:
                break
    
    # Position extraction
    position = ""
    position_patterns = [
        r'(?:job title|position|role|job)[\s:]+([A-Za-z0-9\s\-\&\/\(\)\,\.]+)',
        r'hiring(?:[\s:]+)(?:a|an)?(?:[\s:]+)([A-Za-z0-9\s\-\&\/\(\)]+)',
    ]
    
    for pattern in position_patterns:
        match = re.search(pattern, text_lower)
        if match:
            position = match.group(1).strip()
            if 3 < len(position) < 100:
                break
    
    # Location extraction
    location = "remote"
    if any(term in text_lower for term in ['remote', 'work from home', 'wfh']):
        location = "remote"
    else:
        location_patterns = [
            r'(?:location|based\s+in|located\s+in)[\s:]+([A-Za-z0-9\s\-\,\.]+)',
            r'(?:in|at)\s+([A-Za-z]+(?:\s*,\s*[A-Za-z]+)?)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text_lower)
            if match:
                location = match.group(1).strip()
                if 2 < len(location) < 50:
                    break
    
    # Job type extraction
    job_type = "full-time"
    if 'part-time' in text_lower or 'part time' in text_lower:
        job_type = "part-time"
    elif 'contract' in text_lower:
        job_type = "contract"
    elif 'intern' in text_lower:
        job_type = "internship"
    elif 'remote' in text_lower:
        job_type = "remote"
    
    # Salary extraction
    salary = {"min": 0, "max": 0, "currency": "INR"}
    
    # Determine currency
    currency = "INR"
    if "$" in job_description or "usd" in text_lower:
        currency = "USD"
    elif "€" in job_description or "eur" in text_lower:
        currency = "EUR"
    elif "£" in job_description or "gbp" in text_lower:
        currency = "GBP"
    
    # Look for salary patterns
    salary_patterns = [
        r'(\d+(?:,\d+)?)\s*(?:k|K|thousand)?\s*(?:-|to|–)\s*(\d+(?:,\d+)?)\s*(?:k|K|thousand)?',
        r'(?:salary|compensation|pay).*?(\d+(?:,\d+)?)'
    ]
    
    for pattern in salary_patterns:
        match = re.search(pattern, job_description)
        if match:
            if len(match.groups()) == 2:
                min_sal = int(match.group(1).replace(',', ''))
                max_sal = int(match.group(2).replace(',', ''))
                
                # Check for 'k' multiplier
                if 'k' in match.group(0).lower():
                    min_sal *= 1000
                    max_sal *= 1000
                    
                salary = {"min": min_sal, "max": max_sal, "currency": currency}
            break
    
    # Summary (take first 500 words)
    words = job_description.split()
    summary = ' '.join(words[:100]) if len(words) > 100 else job_description
    
    return {
        "company": company,
        "position": position,
        "jobLocation": location,
        "jobType": job_type,
        "salary": salary,
        "jobDescription": summary,
        "priority": "medium",
        "notes": ""
    }

@app.route('/', methods=['GET'])
def index():
    """Health check and API information"""
    return jsonify({
        "status": "online",
        "service": "Job Data Extraction Service",
        "version": "1.0.0",
        "endpoints": {
            "/api/extract-job-data": "POST - Extract structured data from job description"
        },
        "ollama_available": check_ollama_availability()
    })

@app.route('/api/extract-job-data', methods=['POST'])
def extract_job_data():
    """
    Extract structured job data from job description text
    
    Accepts:
        {
            "jobDescription": "string - the job description text",
            "useLLM": "boolean - whether to use Ollama LLM (optional, default: true)"
        }
        
    Returns:
        {
            "success": true,
            "data": {
                "company": "string",
                "position": "string",
                "jobLocation": "string", 
                "jobType": "string",
                "salary": {"min": number, "max": number, "currency": "string"},
                "jobDescription": "string",
                "priority": "string",
                "notes": "string"
            },
            "processed_by": "ollama|fallback",
            "processing_time_ms": number
        }
    """
    start_time = time.time()
    
    try:
        request_data = request.json
        
        if not request_data:
            return jsonify({
                "success": false,
                "error": "No data provided"
            }), 400
        
        job_description = request_data.get('jobDescription', '')
        use_llm = request_data.get('useLLM', True)
        
        if not job_description or len(job_description.strip()) < 50:
            return jsonify({
                "success": false,
                "error": "Job description is required and must be at least 50 characters"
            }), 400
        
        # Try Ollama extraction first if requested
        extracted_data = None
        processed_by = "fallback"
        
        if use_llm:
            extracted_data = extract_with_ollama(job_description)
            if extracted_data:
                processed_by = "ollama"
        
        # Fallback to rule-based extraction if Ollama failed
        if not extracted_data:
            extracted_data = fallback_extraction(job_description)
            processed_by = "fallback"
        
        # Add processing metadata
        processing_time = time.time() - start_time
        
        return jsonify({
            "success": True,
            "data": extracted_data,
            "processed_by": processed_by,
            "processing_time_ms": round(processing_time * 1000),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing job data: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to process job data",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Log Ollama status on startup
    ollama_available = check_ollama_availability()
    if ollama_available:
        logger.info(f"Ollama is available at {OLLAMA_URL} using model {OLLAMA_MODEL}")
    else:
        logger.warning(f"Ollama is not available at {OLLAMA_URL}. Using fallback extraction only.")
    
    logger.info(f"Starting Job Data Extraction Service on {host}:{port}")
    app.run(host=host, port=port, debug=debug)