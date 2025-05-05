"""
Regular expression based extractors for job data.
"""
import re
import logging

logger = logging.getLogger(__name__)

def extract_job_title(text):
    """
    Extract job title from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        str: Extracted job title
    """
    # Common patterns for job titles
    patterns = [
        r'(?:job title|position|role|job)[\s:]+([A-Za-z0-9\s\-\&\/\(\)\,\.]+)(?:\n|\.|,)',
        r'hiring(?:[\s:]+)(?:a|an)?(?:[\s:]+)([A-Za-z0-9\s\-\&\/\(\)]+)(?:\n|\.|,)',
        r'([A-Za-z0-9\s\-\&\/\(\)]+)(?:\s+)(?:position|job|role)(?:\s+)'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            title = matches.group(1).strip()
            # Limit title length and clean common noise
            if 3 < len(title) < 100:  # Reasonable title length
                # Clean common noise
                title = re.sub(r'^\s*(?:for|the|a|an)\s+', '', title, flags=re.IGNORECASE)
                return title
    
    # Fallback: Look for the first line that might be a title
    lines = text.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if 10 < len(line) < 100 and not re.search(r'(apply|about|company|www|http|location)', line, re.IGNORECASE):
            # Match common job title patterns
            if re.search(r'(?:developer|engineer|manager|analyst|designer|specialist|coordinator)\b', line, re.IGNORECASE):
                return line
    
    return ""

def extract_company(text):
    """
    Extract company name from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        str: Extracted company name
    """
    # Common patterns for company names
    patterns = [
        r'(?:company|organization|employer)[\s:]+([A-Za-z0-9\s\-\&\.]+)(?:\n|\.|,)',
        r'(?:at|with|for|by)\s+([A-Za-z0-9\s\-\&\.]+?)(?:\s+is|\s+are|\s+has|\s+have|\n|\.|,)',
        r'about\s+([A-Za-z0-9\s\-\&\.]+?)(?:\n|\.|,|:)'
    ]
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            company = matches.group(1).strip()
            # Remove common words that might be captured
            company = re.sub(r'\b(the|a|an|is|are|we|our|this|that)\b', '', company, flags=re.IGNORECASE).strip()
            if 3 < len(company) < 50:  # Reasonable company name length
                return company
    
    # Try looking for company in the first paragraph
    first_paragraph = text.split('\n\n')[0] if '\n\n' in text else text.split('\n')[0]
    company_indicators = ['Inc', 'LLC', 'Ltd', 'Limited', 'Corporation', 'Corp', 'GmbH']
    
    for indicator in company_indicators:
        if indicator in first_paragraph:
            # Try to extract company name + indicator
            pattern = r'([A-Za-z0-9\s\-\&\.]+' + re.escape(indicator) + r')'
            match = re.search(pattern, first_paragraph)
            if match:
                return match.group(1).strip()
    
    return ""

def extract_location(text):
    """
    Extract job location from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        str: Job location (or "Remote" if remote position)
    """
    # Check for remote indicators first - they're the most reliable
    remote_patterns = [
        r'\b(?:fully[\s-]+remote|100%[\s-]+remote)\b',
        r'\b(?:remote(?:\s+position|\s+job|\s+work|\s+opportunity)?)\b',
        r'\b(?:work[\s-]+from[\s-]+home|wfh)\b'
    ]
    
    for pattern in remote_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "Remote"
    
    # Check for hybrid indicators
    hybrid_patterns = [
        r'\b(?:hybrid(?:\s+position|\s+job|\s+work|\s+opportunity)?)\b',
        r'\b(?:remote\/on[\s-]*site|on[\s-]*site\/remote)\b',
        r'\b(?:partially[\s-]+remote|work[\s-]+from[\s-]+home[\s-]+part[\s-]+time)\b'
    ]
    
    for pattern in hybrid_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "Hybrid"
    
    # Common patterns for job locations
    location_patterns = [
        r'(?:location|place|based\s+in|located\s+in|position\s+is\s+in)[\s:]+([A-Za-z0-9\s\-\,\.]+)(?:\n|\.|,)',
        r'(?:in|at)\s+([A-Za-z]+(?:\s*,\s*[A-Za-z]+)?)',
        r'([A-Za-z]+(?:\s*,\s*[A-Za-z]+)?)(?:\s+office)'
    ]
    
    for pattern in location_patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            location = matches.group(1).strip()
            # Clean up location
            location = re.sub(r'\b(the|a|an|is|are|we|our|this|that)\b', '', location, flags=re.IGNORECASE).strip()
            if 2 < len(location) < 50:  # Reasonable location length
                return location
    
    return ""

def extract_job_type(text):
    """
    Extract job type from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        str: Job type (e.g., full-time, part-time, contract)
    """
    # Common job types
    job_types = {
        "full-time": ["full time", "full-time", "permanent", "ft", "regular", "permanent role"],
        "part-time": ["part time", "part-time", "pt"],
        "contract": ["contract", "temporary", "temp", "fixed term", "fixed-term"],
        "internship": ["intern", "internship", "trainee", "training"],
        "freelance": ["freelance", "freelancer", "self-employed"]
    }
    
    text_lower = text.lower()
    
    # Check for each job type in the text
    for job_type, keywords in job_types.items():
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                return job_type
    
    # Default to full-time if no match found
    return "full-time"

def extract_salary(text):
    """
    Extract salary information from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        dict: Salary information with min, max, and currency
    """
    salary = {
        "min": 0,
        "max": 0,
        "currency": "INR"  # Default currency
    }
    
    # Common patterns for salary ranges
    patterns = [
        # Currency symbol + numbers with optional K/L + range separator + numbers with optional K/L
        r'([$₹€£¥])(\d+(?:[,.]\d+)?)\s*(?:k|K|L|lakh|lakhs)?\s*(?:-|to|–)\s*(?:\1)?(\d+(?:[,.]\d+)?)\s*(?:k|K|L|lakh|lakhs)?',
        
        # Numbers with optional K/L + range separator + numbers with optional K/L + currency symbol
        r'(\d+(?:[,.]\d+)?)\s*(?:k|K|L|lakh|lakhs)?\s*(?:-|to|–)\s*(\d+(?:[,.]\d+)?)\s*(?:k|K|L|lakh|lakhs)?\s*([₹$€£¥])',
        
        # Salary keywords + optional currency symbol + numbers with optional K/L + range separator + numbers with optional K/L
        r'(?:salary|compensation|pay|ctc|package)(?:\s+range)?[\s:]*([₹$€£¥])?(\d+(?:[,.]\d+)?)(?:\s*k|\s*K|L|lakh|lakhs)?\s*(?:-|to|–)\s*(?:[₹$€£¥])?(\d+(?:[,.]\d+)?)(?:\s*k|\s*K|L|lakh|lakhs)?',
        
        # Numbers + range separator + numbers + per annum/year/month
        r'(\d+)(?:[,.]\d+)?\s*(?:-|to|–)\s*(\d+)(?:[,.]\d+)?\s*(?:per\s+(?:year|annum|pa|month|annum))'
    ]
    
    # Currency symbols to currency codes
    currency_map = {
        "$": "USD", 
        "₹": "INR", 
        "€": "EUR", 
        "£": "GBP", 
        "¥": "JPY"
    }
    
    for pattern in patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            # Different handling based on which pattern matched
            if pattern == patterns[0]:  # First pattern with currency symbol
                currency_symbol = matches.group(1)
                min_salary = matches.group(2).replace(",", "")
                max_salary = matches.group(3).replace(",", "")
                
                # Update currency
                if currency_symbol in currency_map:
                    salary["currency"] = currency_map[currency_symbol]
                
            elif pattern == patterns[1]:  # Numbers followed by currency
                min_salary = matches.group(1).replace(",", "")
                max_salary = matches.group(2).replace(",", "")
                currency_symbol = matches.group(3)
                
                # Update currency
                if currency_symbol in currency_map:
                    salary["currency"] = currency_map[currency_symbol]
                        
            elif pattern == patterns[2]:  # Salary keywords pattern
                currency_symbol = matches.group(1) if matches.group(1) else ""
                min_salary = matches.group(2).replace(",", "")
                max_salary = matches.group(3).replace(",", "")
                
                # Update currency
                if currency_symbol in currency_map:
                    salary["currency"] = currency_map[currency_symbol]
            
            else:  # Numbers with per annum/year/month
                min_salary = matches.group(1).replace(",", "")
                max_salary = matches.group(2).replace(",", "")
            
            # Convert to numbers
            try:
                match_text = text[matches.start():matches.end()].lower()
                
                # Check for multipliers
                multiplier = 1
                if any(x in match_text for x in ['k', 'K']):
                    multiplier = 1000
                elif any(x in match_text for x in ['l', 'L', 'lakh', 'lakhs']):
                    multiplier = 100000  # 1 lakh = 100,000
                
                salary["min"] = int(float(min_salary) * multiplier)
                salary["max"] = int(float(max_salary) * multiplier)
                
                # Check for potential currency mentions if not already set
                if currency_symbol == "":
                    for symbol, code in currency_map.items():
                        if symbol in text[max(0, matches.start()-10):matches.end()+10]:
                            salary["currency"] = code
                            break
                
                # Check for INR or Indian Rupees mentions
                if "inr" in match_text or "rupee" in match_text or "rs." in match_text or "rs " in match_text:
                    salary["currency"] = "INR"
                
                # If found valid salary, return it
                break
            except (ValueError, IndexError):
                continue
    
    return salary

def extract_description(text):
    """
    Extract job description from text.
    
    Args:
        text (str): Cleaned job posting text
        
    Returns:
        str: Job description
    """
    # Initialize with the full text as fallback
    description = text
    
    # Look for common description section headers
    description_headers = [
        "job description", "about the role", "about the job",
        "position overview", "position description", "role details",
        "what you'll do", "responsibilities", "duties", 
        "about the position", "the role"
    ]
    
    # Try to find the start of the description section
    start_idx = -1
    for header in description_headers:
        pattern = r'\b' + re.escape(header) + r'(?:s)?[\s:]*\n?'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start_idx = match.start()
            break
    
    # If we found a description header, extract everything after it
    if start_idx != -1:
        description = text[start_idx:].strip()
        
        # Try to find where the description ends (next major section)
        end_markers = [
            "requirements", "qualifications", "skills required", 
            "what you'll need", "about the company", "benefits", 
            "about us", "who you are", "how to apply", "education",
            "experience required", "key skills", "desired skills",
            "application process", "apply now"
        ]
        
        end_idx = len(description)
        for marker in end_markers:
            pattern = r'\n\s*' + re.escape(marker) + r'(?:s)?[\s:]*\n?'
            match = re.search(pattern, description, re.IGNORECASE)
            if match and match.start() < end_idx:
                end_idx = match.start()
        
        # Extract just the description section
        if end_idx < len(description):
            description = description[:end_idx].strip()
    
    # Clean up excessive whitespace and line breaks
    description = re.sub(r'\n\s*\n', '\n\n', description)
    description = re.sub(r'\n{3,}', '\n\n', description)
    
    return description