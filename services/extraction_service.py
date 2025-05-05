from functools import lru_cache
from utils.html_utils import extract_text_from_html, extract_job_url
from utils.regex_extractors import *
from utils.nlp_helpers import enhance_extraction_with_nlp


@lru_cache(maxsize=100)  # Cache results for performance
def process_job_content(content, is_html=True):
    """Process job posting content and extract structured data"""
    # Initial empty result structure matching your Job schema
    result = {
        "company": "",
        "position": "",
        "status": "applied",  # Default value
        "jobType": "full-time",  # Will be updated based on extraction
        "jobLocation": "remote",  # Will be updated based on extraction
        "jobDescription": "",
        "jobUrl": "",
        "salary": {
            "min": 0,
            "max": 0,
            "currency": "INR"
        },
        "applicationDate": "",  # Will use current date in frontend
        "contactPerson": None,  # This would be linked to contacts in frontend
        "notes": "",
        "priority": "medium",
        "favorite": False
    }
    
    # Extract clean text from HTML if needed
    clean_text = extract_text_from_html(content) if is_html else content
    
    # Use rule-based extraction first
    result["position"] = extract_job_title(clean_text)
    result["company"] = extract_company(clean_text)
    result["jobLocation"] = extract_location(clean_text)
    result["jobType"] = extract_job_type(clean_text)
    result["salary"] = extract_salary(clean_text)
    result["jobDescription"] = extract_description(clean_text)
    result["jobUrl"] = extract_job_url(content, is_html)
    
    # Use NLP model for any fields that weren't successfully extracted
    if not result["position"] or not result["company"]:
        nlp_results = enhance_extraction_with_nlp(clean_text)
        
        # Only update fields that weren't successfully extracted with rule-based approach
        if not result["position"] and nlp_results["title"]:
            result["position"] = nlp_results["title"]
        if not result["company"] and nlp_results["company"]:
            result["company"] = nlp_results["company"]
        if not result["jobLocation"] and nlp_results["location"]:
            result["jobLocation"] = nlp_results["location"]
    
    return result


