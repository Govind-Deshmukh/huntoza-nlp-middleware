"""
app.py - Main Flask application with Ollama integration

This Flask application provides API endpoints for job data processing,
using a hybrid approach with rule-based extractors and Ollama for more complex tasks.
"""
import os
import time
import logging
import json
import re
from functools import wraps
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Import extractors
from services.extractors.skills_extractor import extract_skills  
from services.extractors.summary_extractor import summarize_job_description
from services.extractors.highlights_extractor import extract_highlights
from services.cache_manager import CacheManager

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize cache
cache = CacheManager(max_size=1000, ttl=3600)  # Cache for 1 hour

# Ollama configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')  # Can be changed to other models
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', 30))  # Timeout in seconds

# Resource throttling
MAX_CONCURRENT_OLLAMA_REQUESTS = int(os.environ.get('MAX_CONCURRENT_OLLAMA', 2))
CURRENT_OLLAMA_REQUESTS = 0

# Request throttling decorator
def throttle_requests(max_requests=10, window_seconds=60):
    """
    Rate limiting decorator that restricts endpoints to a maximum number of requests
    in a given time window.
    """
    # Create the request_history list in the decorator's scope
    request_history = []
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Use nonlocal to indicate we're using the decorator's request_history
            nonlocal request_history
            
            # Clean up old requests
            current_time = time.time()
            request_history = [t for t in request_history if current_time - t < window_seconds]
            
            # Check if we're over the limit
            if len(request_history) >= max_requests:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {max_requests} requests allowed per {window_seconds} seconds"
                }), 429
                
            # Add this request to history
            request_history.append(current_time)
            
            # Process the request
            return f(*args, **kwargs)
        return wrapped
    return decorator

def check_ollama_availability():
    """Check if Ollama is available and running"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def extract_with_ollama(text, prompt, use_json=True):
    """
    Extract information using Ollama model
    
    Args:
        text (str): Text to analyze
        prompt (str): Instruction prompt
        use_json (bool): Whether to request JSON output
        
    Returns:
        dict: Extracted information
    """
    global CURRENT_OLLAMA_REQUESTS
    
    # Check if Ollama is available
    if not check_ollama_availability():
        logger.warning("Ollama is not available. Using fallback methods.")
        return None
        
    # Check if we've reached the maximum concurrent requests
    if CURRENT_OLLAMA_REQUESTS >= MAX_CONCURRENT_OLLAMA_REQUESTS:
        logger.warning("Maximum concurrent Ollama requests reached. Using fallback methods.")
        return None
        
    try:
        CURRENT_OLLAMA_REQUESTS += 1
        
        # Prepare the prompt
        full_prompt = prompt
        if use_json:
            full_prompt += "\n\nProvide the output in valid JSON format only."
            
        # Send request to Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{full_prompt}\n\nText to analyze:\n'''\n{text}\n'''",
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more factual responses
                    "num_predict": 1024,  # Limit token generation
                }
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Error from Ollama API: {response.text}")
            return None
            
        result = response.json()
        generated_text = result.get('response', '')
        
        # Parse JSON response if required
        if use_json:
            try:
                # Find JSON block in the response
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{\s*"[\w]+"\s*:[\s\S]*}', generated_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(0)
                    return json.loads(json_str)
                else:
                    # Try to parse the entire response as JSON
                    return json.loads(generated_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Ollama response: {e}")
                logger.debug(f"Response was: {generated_text}")
                return None
        
        return {"text": generated_text}
        
    except requests.RequestException as e:
        logger.error(f"Error communicating with Ollama: {e}")
        return None
    finally:
        CURRENT_OLLAMA_REQUESTS -= 1

@app.route('/', methods=['GET'])
def index():
    """Health check and API information"""
    return jsonify({
        "status": "online",
        "service": "Job Data Processing Middleware",
        "version": "1.0.0",
        "endpoints": {
            "/api/extract-job-data": "POST - Extract structured data from job posting HTML or text"
        }
    })

@app.route('/api/extract-job-data', methods=['POST'])
@throttle_requests(max_requests=20, window_seconds=60)
def extract_job_data():
    """
    Process job posting content and extract structured data.
    
    Accepts:
        - HTML content: {"html": "..."}
        - Plain text: {"text": "..."}
        - URL (future): {"url": "..."}
        
    Optional parameters:
        - use_llm: bool - Whether to use LLM for enhanced extraction
        - format: "basic" or "detailed" - Level of detail in response
        
    Returns:
        Structured job data including skills, summary, etc.
    """
    start_time = time.time()
    request_data = request.json
    
    if not request_data:
        return jsonify({"error": "No data provided"}), 400
        
    # Check if we have required fields
    if not any(field in request_data for field in ['html', 'text']):
        return jsonify({
            "error": "Missing data",
            "message": "You must provide either 'html' or 'text' field"
        }), 400
    
    # Extract configuration options
    use_llm = request_data.get('use_llm', False)
    format_type = request_data.get('format', 'basic')
    
    # Get the content to process
    content = None
    is_html = False
    
    if 'html' in request_data:
        from services.extraction_service import process_job_content
        # Process HTML content using existing service
        try:
            preprocessed = process_job_content(request_data['html'], is_html=True)
            content = preprocessed.get('jobDescription', '')
            is_html = True
        except Exception as e:
            logger.error(f"Error processing HTML content: {str(e)}")
            return jsonify({"error": "Failed to process HTML content"}), 500
    elif 'text' in request_data:
        content = request_data['text']
    
    if not content:
        return jsonify({"error": "No content to process"}), 400
    
    # Check cache
    cache_key = f"job_data:{hash(content)}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info("Returning cached result")
        # Add timing information
        cached_result['_meta'] = {
            'cached': True,
            'processing_time_ms': 0,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(cached_result), 200
    
    # Initialize result object
    result = {
        'skills': [],
        'summary': '',
        'highlights': [],
    }
    
    # Extract data using rule-based methods
    try:
        # Extract skills
        result['skills'] = extract_skills(content)
        
        # Generate summary
        result['summary'] = summarize_job_description(content)
        
        # Extract highlights
        result['highlights'] = extract_highlights(content)
    except Exception as e:
        logger.error(f"Error in rule-based extraction: {str(e)}")
        # Continue with partial results
    
    # If LLM processing is requested and more complex analysis is needed
    if use_llm and len(content) > 100:
        try:
            # Extract with Ollama for enhanced results
            ollama_prompt = (
                "You are a job analysis assistant. Extract the following information from the job description:\n"
                "1. A list of required skills and qualifications\n"
                "2. A concise summary of the job (2-3 sentences)\n"
                "3. 3-5 key highlights about the position (benefits, growth opportunities, etc.)\n"
                "4. Any special notes that would be useful for job seekers"
            )
            
            ollama_result = extract_with_ollama(content, ollama_prompt)
            
            if ollama_result:
                # Update or merge with rule-based results
                if 'skills' in ollama_result and ollama_result['skills']:
                    # Combine skills, removing duplicates
                    all_skills = set(result['skills'])
                    all_skills.update(ollama_result['skills'])
                    result['skills'] = list(all_skills)
                
                if 'summary' in ollama_result and ollama_result['summary']:
                    result['summary'] = ollama_result['summary']
                
                if 'highlights' in ollama_result and ollama_result['highlights']:
                    result['highlights'] = ollama_result['highlights']
                
                if 'notes' in ollama_result and ollama_result['notes']:
                    result['notes'] = ollama_result['notes']
        except Exception as e:
            logger.error(f"Error in LLM-based extraction: {str(e)}")
            # Continue with rule-based results
    
    # Format response according to requested detail level
    formatted_result = result
    if format_type == 'detailed':
        # For detailed format, include additional information and metadata
        formatted_result = {
            **result,
            'analysis': {
                'detected_job_type': detect_job_type(content),
                'education_requirements': extract_education_requirements(content),
                'experience_level': extract_experience_level(content),
                'remote_status': is_remote_job(content),
            }
        }
    
    # Add metadata
    processing_time = time.time() - start_time
    formatted_result['_meta'] = {
        'cached': False,
        'processing_time_ms': round(processing_time * 1000),
        'timestamp': datetime.now().isoformat(),
        'llm_enhanced': use_llm
    }
    
    # Cache the result
    cache.set(cache_key, formatted_result)
    
    return jsonify(formatted_result), 200

# Simple extraction functions for detailed format
def detect_job_type(text):
    """Detect job type from text"""
    job_types = {
        'full-time': ['full time', 'full-time', 'permanent'],
        'part-time': ['part time', 'part-time'],
        'contract': ['contract', 'contractor', 'temporary'],
        'internship': ['intern', 'internship', 'trainee'],
        'freelance': ['freelance', 'freelancer'],
    }
    
    for job_type, keywords in job_types.items():
        if any(keyword in text.lower() for keyword in keywords):
            return job_type
    
    # Default to full-time if not specified
    return 'full-time'

def extract_education_requirements(text):
    """Extract education requirements from text"""
    education_levels = [
        'bachelor', 'master', 'phd', 'doctorate', 'high school', 'associate',
        'degree', 'diploma', 'mba', 'b.tech', 'b.e.', 'm.tech', 'm.e.'
    ]
    
    text_lower = text.lower()
    for level in education_levels:
        if level in text_lower:
            # Find the context around this education level
            index = text_lower.find(level)
            start = max(0, index - 30)
            end = min(len(text), index + 50)
            context = text[start:end]
            return context.strip()
    
    return "Not specified"

def extract_experience_level(text):
    """Extract experience level from text"""
    text_lower = text.lower()
    
    # Look for X+ years, X years of experience, etc.
    experience_patterns = [
        r'(\d+)\+?\s*(?:years|yrs)',
        r'(\d+)-(\d+)\s*(?:years|yrs)',
        r'(?:minimum|min)\.?\s*(?:of)?\s*(\d+)\s*(?:years|yrs)',
        r'(?:at least|atleast)\s*(\d+)\s*(?:years|yrs)',
        r'(\d+)\s*(?:years|yrs).*?experience'
    ]
    
    for pattern in experience_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 1:
                return f"{match.group(1)}+ years"
            elif len(match.groups()) == 2:
                return f"{match.group(1)}-{match.group(2)} years"
    
    # Check for entry level indicators
    if any(term in text_lower for term in ['entry level', 'junior', 'no experience', 'fresh', 'graduate']):
        return "Entry level"
    
    # Check for senior level indicators
    if any(term in text_lower for term in ['senior', 'sr.', 'experienced', 'lead']):
        return "Senior level"
    
    return "Not specified"

def is_remote_job(text):
    """Determine if job is remote"""
    text_lower = text.lower()
    remote_indicators = ['remote', 'work from home', 'wfh', 'virtual', 'telecommute']
    hybrid_indicators = ['hybrid', 'flexible location', 'partially remote']
    
    if any(indicator in text_lower for indicator in remote_indicators):
        if any(indicator in text_lower for indicator in hybrid_indicators):
            return "hybrid"
        return "remote"
    
    return "onsite"

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
        logger.warning(f"Ollama is not available at {OLLAMA_URL}. LLM-enhanced features will use fallback methods.")
    
    logger.info(f"Starting Job Data Processing Middleware on {host}:{port} (debug: {debug})")
    app.run(host=host, port=port, debug=debug)