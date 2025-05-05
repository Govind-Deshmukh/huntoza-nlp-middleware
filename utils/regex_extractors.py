def extract_description(text):
    """Extract job description from text"""
    # Initialize with the full text as fallback
    description = text.strip()
    
    # Look for common description section headers
    description_headers = [
        "job description:", "about the role:", "about the job:",
        "position overview:", "position description:", "role details:",
        "what you'll do:", "responsibilities:", "duties:"
    ]
    
    # Try to find the start of the description section
    start_idx = -1
    for header in description_headers:
        if header.lower() in text.lower():
            start_idx = text.lower().find(header.lower())
            if start_idx != -1:
                break
    
    # If we found a description header, extract everything after it
    if start_idx != -1:
        description = text[start_idx:].strip()
        
        # Try to find where the description ends (next major section)
        end_markers = [
            "requirements:", "qualifications:", "skills required:", 
            "what you'll need:", "about the company:", "benefits:", 
            "about us:", "who you are:", "how to apply:"
        ]
        
        end_idx = len(description)
        for marker in end_markers:
            marker_idx = description.lower().find(marker.lower())
            if marker_idx != -1 and marker_idx < end_idx:
                end_idx = marker_idx
        
        # Extract just the description section
        if end_idx < len(description):
            description = description[:end_idx].strip()
    
    # Clean up the description (remove excessive whitespace, etc.)
    description = re.sub(r'\n+', '\n', description)  # Replace multiple newlines with single
    description = re.sub(r'\s+', ' ', description)   # Replace multiple spaces with single
    
    return description