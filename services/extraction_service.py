from functools import lru_cache
from utils.html_utils import extract_text_from_html, extract_job_url
from utils.regex_extractors import (
    extract_job_title, extract_company, extract_location, 
    extract_job_type, extract_salary, extract_description
)
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
        "favorite": False,
        "skills": []  # Additional field for extracted skills
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
    
    # Use NLP model for enhancement and to fill in missing fields
    nlp_results = enhance_extraction_with_nlp(clean_text)
    
    # Update fields that weren't successfully extracted with rule-based approach
    if not result["position"] and nlp_results["title"]:
        result["position"] = nlp_results["title"]
    if not result["company"] and nlp_results["company"]:
        result["company"] = nlp_results["company"]
    if not result["jobLocation"] and nlp_results["location"]:
        result["jobLocation"] = nlp_results["location"]
    if not result["jobType"] and nlp_results["job_type"]:
        result["jobType"] = nlp_results["job_type"]
    
    # Salary is a special case - merge results intelligently
    if result["salary"]["min"] == 0 and result["salary"]["max"] == 0:
        result["salary"] = nlp_results["salary"]
    
    # Add extracted skills to the result
    result["skills"] = nlp_results["skills"]
    
    # If rule-based extraction fails or returns empty values, 
    # generate a summary for job description using NLP
    if not result["jobDescription"] or len(result["jobDescription"]) < 50:
        result["jobDescription"] = clean_text[:1000]  # Use first 1000 chars as fallback
    
    return result