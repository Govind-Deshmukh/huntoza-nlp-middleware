"""
services/extractors/highlights_extractor.py - Extract key highlights and insights

Identifies important aspects of the job posting that would be valuable to include
in notes, such as benefits, company culture, growth opportunities, etc.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Patterns to identify different sections
BENEFITS_PATTERNS = [
    re.compile(r'(?:^|\n)(?:benefits|perks|what\s+we\s+offer|compensation|package|what\s+you\'ll\s+get)[:\s]*\n', re.IGNORECASE),
    re.compile(r'(?:^|\n)(?:we\s+offer|you\'ll\s+receive)[:\s]*\n', re.IGNORECASE),
]

CULTURE_PATTERNS = [
    re.compile(r'(?:^|\n)(?:our\s+culture|about\s+us|who\s+we\s+are|company\s+culture|team\s+culture|working\s+at)[:\s]*\n', re.IGNORECASE),
    re.compile(r'(?:^|\n)(?:why\s+join\s+us|why\s+work\s+(?:for|with)\s+us)[:\s]*\n', re.IGNORECASE),
]

GROWTH_PATTERNS = [
    re.compile(r'(?:^|\n)(?:growth|career|advancement|development|opportunities|learning)[:\s]*\n', re.IGNORECASE),
    re.compile(r'(?:^|\n)(?:what\s+you\'ll\s+learn|how\s+you\'ll\s+grow)[:\s]*\n', re.IGNORECASE),
]

RESPONSIBILITY_PATTERNS = [
    re.compile(r'(?:^|\n)(?:responsibilities|duties|what\s+you\'ll\s+do|role|job\s+description|day-to-day)[:\s]*\n', re.IGNORECASE),
]

# Important keywords to look for
BENEFIT_KEYWORDS = [
    'health insurance', 'dental', 'vision', 'medical', '401k', 'retirement', 
    'PTO', 'paid time off', 'vacation', 'holidays', 'sick leave', 'parental leave',
    'maternity', 'paternity', 'bonus', 'stock options', 'equity', 'flexible hours',
    'flexible schedule', 'work-life balance', 'remote work', 'work from home', 'WFH',
    'hybrid', 'gym', 'fitness', 'wellness', 'mental health', 'education', 'tuition',
    'professional development', 'training', 'lunch', 'meals', 'snacks', 'transportation',
    'commuter', 'relocation', 'child care', 'daycare', 'sabbatical', 'volunteer',
]

IMPORTANT_HIGHLIGHTS = [
    'salary', 'compensation', 'pay', 'equity', 'bonus', 'commission', 'stock', 'options',
    'promotion', 'growth', 'career path', 'advancement', 'mentor', 'training',
    'market leader', 'startup', 'fast-growing', 'fast-paced', 'work-life balance',
    'flexible', 'autonomy', 'ownership', 'impact', 'mission', 'vision', 'values',
    'diversity', 'inclusive', 'inclusion', 'equal opportunity', 'teamwork',
    'collaborate', 'collaboration', 'innovation', 'creative', 'cutting-edge',
    'latest technologies', 'tech stack', 'modern', 'tools', 'investment',
    'funded', 'profitable', 'benefits', 'perks', 'culture', 'environment',
    '4-day work week', 'unlimited vacation', 'remote-first', 'distributed team',
]

def extract_highlights(text, max_highlights=5):
    """
    Extract key highlights from a job description.
    
    Args:
        text (str): Job description text
        max_highlights (int): Maximum number of highlights to extract
        
    Returns:
        list: Extracted highlights as list of strings
    """
    if not text:
        return []
        
    try:
        highlights = []
        
        # Extract from specific sections first
        benefits = extract_from_section(text, BENEFITS_PATTERNS)
        if benefits:
            highlights.append(format_section_highlight("Benefits", benefits))
            
        culture = extract_from_section(text, CULTURE_PATTERNS)
        if culture:
            highlights.append(format_section_highlight("Company Culture", culture))
            
        growth = extract_from_section(text, GROWTH_PATTERNS)
        if growth:
            highlights.append(format_section_highlight("Growth Opportunities", growth))
        
        # Extract from bullet points
        bullet_highlights = extract_from_bullets(text)
        highlights.extend(bullet_highlights)
        
        # Look for specific benefit keywords
        benefit_highlights = extract_benefit_mentions(text)
        highlights.extend(benefit_highlights)
        
        # Extract any mentions of important keywords
        keyword_highlights = extract_keyword_mentions(text)
        highlights.extend(keyword_highlights)
        
        # Deduplicate, prioritize, and limit
        return deduplicate_highlights(highlights, max_highlights)
        
    except Exception as e:
        logger.error(f"Error extracting highlights: {str(e)}")
        return []

def extract_from_section(text, patterns):
    """
    Extract content from a specific section based on patterns.
    
    Args:
        text (str): Text to extract from
        patterns (list): List of regex patterns to match section headings
        
    Returns:
        str: Extracted section content or empty string
    """
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            start_pos = match.end()
            # Find the end of this section (next section heading or double newline)
            end_match = re.search(r'\n\s*\n|\n[A-Z][^a-z\n]+:', text[start_pos:])
            
            if end_match:
                section_text = text[start_pos:start_pos + end_match.start()]
            else:
                # Take next 250 characters if no clear end found
                section_text = text[start_pos:start_pos + 250]
                
            # Clean up the section text
            section_text = clean_section_text(section_text)
            
            if section_text:
                return section_text
    
    return ""

def clean_section_text(text):
    """Clean and format section text."""
    if not text:
        return ""
        
    # Remove excess whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # If text is too long, truncate it
    if len(text) > 150:
        text = text[:147] + "..."
        
    return text

def format_section_highlight(section_name, text):
    """Format a section highlight with section name."""
    return f"{section_name}: {text}"

def extract_from_bullets(text):
    """
    Extract highlights from bullet points in the text.
    
    Args:
        text (str): Text to extract from
        
    Returns:
        list: List of extracted bullet point highlights
    """
    highlights = []
    
    # Match bullet points (• - * · etc.)
    bullet_items = re.findall(r'(?:^|\n)[•\-*·]\s*([^\n•\-*·]+)', text)
    
    for item in bullet_items:
        item = item.strip()
        
        # Skip very short items or items that look like section headings
        if len(item) < 5 or item.isupper() or item.endswith(':'):
            continue
            
        # Check if bullet contains important keywords
        if any(keyword.lower() in item.lower() for keyword in IMPORTANT_HIGHLIGHTS):
            # Clean and format
            if len(item) > 100:
                item = item[:97] + "..."
                
            highlights.append(item)
            
    # Return top bullets
    return highlights[:3]  # Limit to 3 bullet points

def extract_benefit_mentions(text):
    """
    Extract mentions of benefits from the text.
    
    Args:
        text (str): Text to extract from
        
    Returns:
        list: List of benefit highlights
    """
    highlights = []
    text_lower = text.lower()
    
    # Check for specific benefits
    found_benefits = []
    for benefit in BENEFIT_KEYWORDS:
        if benefit.lower() in text_lower:
            found_benefits.append(benefit)
    
    # Group similar benefits
    grouped_benefits = group_similar_items(found_benefits)
    
    # Format benefit highlights
    if grouped_benefits:
        benefits_str = ", ".join(grouped_benefits[:5])  # Limit to 5 benefits
        if len(grouped_benefits) > 5:
            benefits_str += ", and more"
        highlights.append(f"Benefits include: {benefits_str}")
    
    return highlights

def extract_keyword_mentions(text):
    """
    Extract mentions of important keywords from text.
    
    Args:
        text (str): Text to extract from
        
    Returns:
        list: List of keyword-based highlights
    """
    highlights = []
    text_lower = text.lower()
    
    # Look for important highlight phrases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        # Skip very short or very long sentences
        if len(sentence) < 10 or len(sentence) > 150:
            continue
            
        # Check if sentence contains important keywords
        contains_keyword = False
        for keyword in IMPORTANT_HIGHLIGHTS:
            if keyword.lower() in sentence.lower():
                contains_keyword = True
                break
                
        if contains_keyword:
            # Clean and format
            cleaned = sentence.strip()
            if not cleaned.endswith(('.', '!', '?')):
                cleaned += '.'
            highlights.append(cleaned)
    
    # Return top sentences
    return highlights[:2]  # Limit to 2 sentences

def group_similar_items(items):
    """
    Group similar items to avoid redundancy.
    
    Args:
        items (list): List of items to group
        
    Returns:
        list: Grouped items
    """
    if not items:
        return []
        
    # Define groups of related terms
    groups = [
        {'health insurance', 'medical', 'health', 'healthcare'},
        {'dental', 'vision'},
        {'401k', 'retirement'},
        {'PTO', 'paid time off', 'vacation', 'holidays', 'sick leave'},
        {'parental leave', 'maternity', 'paternity'},
        {'bonus', 'stock options', 'equity'},
        {'flexible hours', 'flexible schedule', 'work-life balance'},
        {'remote work', 'work from home', 'WFH', 'hybrid'},
        {'gym', 'fitness', 'wellness', 'mental health'},
        {'education', 'tuition', 'professional development', 'training'}
    ]
    
    # Standardized terms for each group
    group_names = [
        'Health insurance',
        'Dental & vision',
        'Retirement plan',
        'Paid time off',
        'Parental leave',
        'Performance bonuses/equity',
        'Flexible schedule',
        'Remote/hybrid work',
        'Wellness programs',
        'Education & development'
    ]
    
    result = []
    used_groups = set()
    
    # First pass - handle grouped items
    for item in items:
        item_lower = item.lower()
        
        for i, group in enumerate(groups):
            if i in used_groups:
                continue
                
            if any(term in item_lower for term in group):
                result.append(group_names[i])
                used_groups.add(i)
                break
    
    # Second pass - add remaining items that don't belong to any group
    for item in items:
        item_lower = item.lower()
        
        if not any(any(term in item_lower for term in group) for group in groups):
            # Capitalize first letter of each word
            item = ' '.join(word.capitalize() for word in item.split())
            result.append(item)
    
    return result

def deduplicate_highlights(highlights, max_highlights):
    """
    Deduplicate and prioritize highlights.
    
    Args:
        highlights (list): List of highlights
        max_highlights (int): Maximum number of highlights to return
        
    Returns:
        list: Deduplicated and prioritized highlights
    """
    if not highlights:
        return []
        
    # Remove exact duplicates
    seen = set()
    unique_highlights = []
    
    for highlight in highlights:
        if highlight.lower() not in seen:
            seen.add(highlight.lower())
            unique_highlights.append(highlight)
    
    # Check for similar highlights and remove less informative ones
    filtered_highlights = []
    for highlight in unique_highlights:
        # Skip if this highlight is a subset of another one
        if not any(
            highlight.lower() in other.lower() and highlight.lower() != other.lower()
            for other in unique_highlights
        ):
            filtered_highlights.append(highlight)
    
    # Prioritize section-based highlights
    section_highlights = [h for h in filtered_highlights if any(
        h.startswith(prefix) for prefix in ["Benefits:", "Company Culture:", "Growth Opportunities:"]
    )]
    
    other_highlights = [h for h in filtered_highlights if h not in section_highlights]
    
    # Combine and limit
    result = section_highlights + other_highlights
    return result[:max_highlights]