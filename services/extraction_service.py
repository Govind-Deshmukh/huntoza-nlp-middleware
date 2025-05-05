"""
Job data extraction service - core business logic for extracting structured job data.
"""
from functools import lru_cache
import logging
from utils.html_utils import extract_text_from_html, extract_job_url, extract_metadata_fields
from utils.regex_extractors import (
    extract_job_title, extract_company, extract_location, 
    extract_job_type, extract_salary, extract_description
)

logger = logging.getLogger(__name__)

@lru_cache(maxsize=100)  # Cache results for performance
def process_job_content(content, is_html=True):
    """
    Process job posting content and extract structured data.
    
    Args:
        content (str): HTML or text content from job posting
        is_html (bool): Flag indicating if content is HTML (True) or plain text (False)
        
    Returns:
        dict: Structured job data including company, position, location, etc.
    """
    logger.info(f"Processing job content (HTML: {is_html})")
    
    # Initial empty result structure matching Job schema
    result = {
        "company": "",
        "position": "",
        "jobType": "full-time",  # Default value
        "jobLocation": "",
        "jobDescription": "",
        "jobUrl": "",
        "salary": {
            "min": 0,
            "max": 0,
            "currency": "INR"
        }
    }
    
    try:
        # Step 1: Extract metadata if HTML
        if is_html:
            metadata = extract_metadata_fields(content)
            result["position"] = metadata["title"]
            result["company"] = metadata["company"]
            result["jobLocation"] = metadata["location"]
            result["jobDescription"] = metadata["description"]
            result["jobUrl"] = extract_job_url(content)
        
        # Step 2: Extract clean text from HTML if needed
        clean_text = extract_text_from_html(content) if is_html else content
        
        # Step 3: Use rule-based extraction on the clean text
        # Only overwrite fields if they're empty or enhance with better data
        if not result["position"]:
            result["position"] = extract_job_title(clean_text)
        
        if not result["company"]:
            result["company"] = extract_company(clean_text)
        
        if not result["jobLocation"]:
            result["jobLocation"] = extract_location(clean_text)
        
        # Always extract job type from text as it's often not in metadata
        result["jobType"] = extract_job_type(clean_text)
        
        # Extract salary information
        result["salary"] = extract_salary(clean_text)
        
        # Extract job description if not already extracted from metadata
        if not result["jobDescription"] or len(result["jobDescription"]) < 100:
            result["jobDescription"] = extract_description(clean_text)
        
        # Step 4: Validate and clean up the extracted data
        result = clean_and_validate_job_data(result, clean_text)
        
        logger.info("Job data extraction completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error during job data extraction: {str(e)}")
        # Return whatever we have so far - partial data is better than nothing
        if not result["jobDescription"]:
            # Use the cleaned text as fallback for description
            result["jobDescription"] = clean_text[:1000] if len(clean_text) > 1000 else clean_text
        return result

def clean_and_validate_job_data(job_data, full_text):
    """
    Clean and validate extracted job data, filling in defaults if needed.
    
    Args:
        job_data (dict): Extracted job data
        full_text (str): Full job posting text
        
    Returns:
        dict: Cleaned and validated job data
    """
    # Clean position
    if not job_data["position"]:
        # Try to use the first non-empty line as a fallback for position
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            # Only use first line if it's reasonably short
            if len(first_line) < 100:
                job_data["position"] = first_line
    
    # Ensure position doesn't exceed a reasonable length
    if job_data["position"] and len(job_data["position"]) > 100:
        job_data["position"] = job_data["position"][:97] + "..."
    
    # Set default job type if not extracted
    if not job_data["jobType"]:
        job_data["jobType"] = "full-time"
    
    # Set default job location if not extracted
    if not job_data["jobLocation"]:
        # If the text contains remote work indicators, set as remote
        if any(term in full_text.lower() for term in ["remote", "work from home", "wfh"]):
            job_data["jobLocation"] = "Remote"
    
    # Ensure the job description doesn't contain the entire text if it's too long
    if job_data["jobDescription"] == full_text and len(full_text) > 2000:
        # Use the first 2000 characters as the description
        job_data["jobDescription"] = full_text[:2000] + "..."
    
    # Validate salary
    if job_data["salary"]["min"] > job_data["salary"]["max"] and job_data["salary"]["max"] > 0:
        # Swap min and max if min is greater than max
        job_data["salary"]["min"], job_data["salary"]["max"] = job_data["salary"]["max"], job_data["salary"]["min"]
    
    return job_data