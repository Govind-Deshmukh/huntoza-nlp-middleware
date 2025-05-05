import spacy
import re
from typing import Dict, Any, List, Optional

# Load the English NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Fallback if model isn't installed
    print("Downloading spaCy model...")
    import subprocess
    subprocess.call([
        "python", "-m", "spacy", "download", "en_core_web_sm"
    ])
    nlp = spacy.load("en_core_web_sm")

def enhance_extraction_with_nlp(text: str) -> Dict[str, Any]:
    """
    Use NLP techniques to extract job information from text when regex patterns fail.
    
    Args:
        text: The cleaned text content of a job posting
        
    Returns:
        Dictionary with extracted job details
    """
    # Initialize results dictionary
    results = {
        "title": "",
        "company": "",
        "location": "",
        "job_type": "",
        "skills": [],
        "experience": "",
        "education": "",
        "salary": {"min": 0, "max": 0, "currency": "INR"}
    }
    
    # Process text with spaCy
    doc = nlp(text[:20000])  # Limit text length to avoid processing too much
    
    # Extract job title using NLP patterns
    results["title"] = extract_job_title_nlp(doc)
    
    # Extract company name
    results["company"] = extract_company_nlp(doc)
    
    # Extract location
    results["location"] = extract_location_nlp(doc)
    
    # Extract job type
    results["job_type"] = extract_job_type_nlp(doc, text)
    
    # Extract skills
    results["skills"] = extract_skills(doc, text)
    
    # Extract salary information
    results["salary"] = extract_salary_nlp(doc, text)
    
    return results

def extract_job_title_nlp(doc) -> str:
    """Extract job title using NLP techniques"""
    # Common job title indicators
    title_indicators = [
        "job title:", "position:", "role:", "designation:", "we are hiring"
    ]
    
    # Try to find job title by looking at sentences with title indicators
    for sent in doc.sents:
        sent_text = sent.text.lower()
        
        for indicator in title_indicators:
            if indicator in sent_text:
                # Get the text after the indicator
                title_part = sent_text.split(indicator)[1].strip()
                
                # Extract the first noun phrase or up to next punctuation
                for token in sent:
                    if token.text.lower() in indicator:
                        # Get the next 5-7 tokens as potential job title
                        title_candidate = " ".join([t.text for t in token.rights if not t.is_punct][:7])
                        if title_candidate:
                            return title_candidate.strip()
    
    # Fallback: Look for job title patterns at the beginning
    # Many job postings start with the title or have it in the first few sentences
    first_sentences = list(doc.sents)[:3]
    for sent in first_sentences:
        # Check if first sentence is short (likely to be title)
        if len(sent) < 10 and any(token.pos_ == "NOUN" for token in sent):
            return sent.text.strip()
    
    # Get the most frequent NOUN + NOUN or ADJ + NOUN pattern
    noun_phrases = []
    for chunk in doc.noun_chunks:
        if len(chunk) <= 5 and any(token.pos_ == "NOUN" for token in chunk):
            noun_phrases.append(chunk.text)
    
    # Common job title keywords to match
    job_keywords = ["engineer", "developer", "manager", "specialist", "analyst", 
                   "designer", "consultant", "coordinator", "associate", "assistant",
                   "director", "lead", "head", "architect", "scientist", "technician"]
    
    # Filter noun phrases that contain job keywords
    job_related_phrases = [phrase for phrase in noun_phrases 
                          if any(keyword in phrase.lower() for keyword in job_keywords)]
    
    # Return the first job-related phrase if found
    if job_related_phrases:
        return job_related_phrases[0]
    
    return ""

def extract_company_nlp(doc) -> str:
    """Extract company name using NLP techniques"""
    # Look for company name patterns
    company_indicators = [
        "at", "with", "for", "company:", "organization:", "employer:", "client:"
    ]
    
    for sent in doc.sents:
        sent_text = sent.text.lower()
        
        for indicator in company_indicators:
            if indicator in sent_text and indicator + " " in sent_text:
                # Get text after the indicator
                parts = sent_text.split(indicator + " ")
                if len(parts) > 1:
                    # Take the next 1-3 tokens
                    company_part = parts[1].strip().split()[:3]
                    if company_part:
                        # Cut off at next punctuation if needed
                        company = " ".join(company_part)
                        for punct in [",", ".", ";"]:
                            if punct in company:
                                company = company.split(punct)[0]
                        return company.strip()
    
    # Look for Organizations (companies) identified by spaCy
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    
    if orgs:
        # Get the most mentioned organization
        org_counts = {}
        for org in orgs:
            if len(org.split()) <= 4:  # Avoid very long org names that are likely not companies
                org_counts[org] = org_counts.get(org, 0) + 1
        
        if org_counts:
            return max(org_counts.items(), key=lambda x: x[1])[0]
    
    return ""

def extract_location_nlp(doc) -> str:
    """Extract job location using NLP"""
    # Look for location indicators
    location_indicators = [
        "location:", "place:", "based in", "position is in", "job location"
    ]
    
    for sent in doc.sents:
        sent_text = sent.text.lower()
        
        for indicator in location_indicators:
            if indicator in sent_text:
                # Get text after the indicator
                parts = sent_text.split(indicator)
                if len(parts) > 1:
                    location_part = parts[1].strip().split()[:4]
                    if location_part:
                        # Cut off at punctuation
                        location = " ".join(location_part)
                        for punct in [",", ".", ";"]:
                            if punct in location:
                                location = location.split(punct)[0]
                        return location.strip()
    
    # Look for locations identified by spaCy
    locs = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
    
    if locs:
        # Return the most common location
        loc_counts = {}
        for loc in locs:
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
        
        return max(loc_counts.items(), key=lambda x: x[1])[0]
    
    # Check for remote work indicators
    remote_keywords = ["remote", "work from home", "wfh", "telecommute", "virtual"]
    for keyword in remote_keywords:
        if keyword in doc.text.lower():
            return "Remote"
    
    return ""

def extract_job_type_nlp(doc, text: str) -> str:
    """Determine job type using NLP and keyword matching"""
    # Check for common job type indicators
    job_type_patterns = {
        "full-time": ["full time", "full-time", "permanent", "ft"],
        "part-time": ["part time", "part-time", "pt"],
        "contract": ["contract", "temporary", "temp", "contractor"],
        "internship": ["intern", "internship", "trainee"],
        "remote": ["remote", "work from home", "wfh", "telecommute", "virtual"],
        "freelance": ["freelance", "freelancer"]
    }
    
    text_lower = text.lower()
    
    # Count mentions of each job type
    type_scores = {job_type: 0 for job_type in job_type_patterns.keys()}
    
    for job_type, patterns in job_type_patterns.items():
        for pattern in patterns:
            type_scores[job_type] += text_lower.count(pattern)
    
    # Get the job type with the highest score
    if any(type_scores.values()):
        best_match = max(type_scores.items(), key=lambda x: x[1])
        if best_match[1] > 0:
            return best_match[0]
    
    # Default to full-time if no match found
    return "full-time"

def extract_skills(doc, text: str) -> List[str]:
    """Extract skills mentioned in the job posting"""
    # Common skill keywords and frameworks
    tech_skills = [
        "python", "java", "javascript", "html", "css", "react", "angular", "vue", 
        "node", "express", "django", "flask", "spring", "sql", "nosql", "mongodb",
        "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "git", "agile",
        "scrum", "devops", "machine learning", "ai", "data science", "rest api",
        "graphql", "microservices", "cloud", "linux", "windows", "unix"
    ]
    
    soft_skills = [
        "communication", "teamwork", "leadership", "problem solving", 
        "critical thinking", "time management", "adaptability", "project management",
        "creativity", "analytical", "collaboration", "organization"
    ]
    
    # Combine all skills
    all_skills = tech_skills + soft_skills
    
    # Extract skills
    found_skills = set()
    text_lower = text.lower()
    
    for skill in all_skills:
        if skill in text_lower:
            found_skills.add(skill)
    
    # Extract skills that might be in bullet points or requirements section
    requirements_section = extract_requirements_section(text)
    if requirements_section:
        # Check for skills in the requirements section
        for skill in all_skills:
            if skill in requirements_section.lower() and skill not in found_skills:
                found_skills.add(skill)
    
    return list(found_skills)

def extract_requirements_section(text: str) -> str:
    """Extract the requirements/qualifications section from job posting"""
    section_headers = [
        "requirements", "qualifications", "skills required", "what you'll need",
        "what we're looking for", "required skills", "key qualifications"
    ]
    
    text_lower = text.lower()
    
    for header in section_headers:
        if header in text_lower:
            # Find the section start
            start_idx = text_lower.find(header)
            if start_idx != -1:
                # Get text after the header
                section_text = text[start_idx:]
                # Find the end of the section (next section header or end of text)
                end_idx = len(section_text)
                for line in section_text.split('\n'):
                    if line.strip() and line.strip()[-1] == ':' and len(line) < 50:
                        end_idx = section_text.find(line)
                        if end_idx > 100:  # Make sure we're not cutting off too early
                            break
                
                return section_text[:end_idx].strip()
    
    return ""

def extract_salary_nlp(doc, text: str) -> Dict[str, Any]:
    """Extract salary information using NLP patterns"""
    salary_info = {"min": 0, "max": 0, "currency": "INR"}
    
    # Look for common salary patterns
    salary_patterns = [
        r'(?:salary|compensation|pay)(?:\s+range)?(?:\s+is)?(?:\s+up\s+to)?[:\s]+([$€£₹¥])?(\d+(?:[,\.]\d+)?)\s*(?:K|k|,000)?\s*(?:-|to|–|and)\s*([$€£₹¥])?(\d+(?:[,\.]\d+)?)\s*(?:K|k|,000)?',
        r'([$€£₹¥])?(\d+(?:[,\.]\d+)?)\s*(?:K|k|,000)?\s*(?:-|to|–|and)\s*([$€£₹¥])?(\d+(?:[,\.]\d+)?)\s*(?:K|k|,000)?\s+(?:per|/)\s+(?:year|annum|annual)',
        r'([$€£₹¥])?(\d+(?:[,\.]\d+)?)(?:K|k)?\s*-\s*([$€£₹¥])?(\d+(?:[,\.]\d+)?)(?:K|k)?'
    ]
    
    for pattern in salary_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            match = matches[0]
            
            # Get currency symbol (if present)
            currency_symbol = match[0] if len(match) > 2 and match[0] else match[2] if len(match) > 2 else ""
            
            # Map currency symbol to code
            currency_map = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}
            if currency_symbol in currency_map:
                salary_info["currency"] = currency_map[currency_symbol]
            
            # Parse min and max amounts
            try:
                min_amount = float(match[1].replace(",", ""))
                max_amount = float(match[3].replace(",", ""))
                
                # Check if values are in thousands (K)
                if "k" in text.lower() or "K" in text:
                    min_amount *= 1000
                    max_amount *= 1000
                
                salary_info["min"] = int(min_amount)
                salary_info["max"] = int(max_amount)
                break
            except (ValueError, IndexError):
                continue
    
    return salary_info