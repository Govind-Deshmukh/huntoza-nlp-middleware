"""
services/extractors/summary_extractor.py - Generate concise job summaries

Creates brief summaries of job descriptions by extracting key sentences
or generating abstracts using rule-based techniques.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Important keywords to prioritize sentences containing them
PRIORITY_KEYWORDS = [
    'job description', 'overview', 'summary', 'role', 'position',
    'opportunity', 'responsibilities', 'duties', 'mission',
    'looking for', 'seeking', 'hiring', 'ideal candidate',
    'position summary', 'job summary', 'about the role'
]

# Stopwords for filtering
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
    'while', 'of', 'to', 'in', 'for', 'with', 'on', 'at', 'from', 'by',
    'about', 'against', 'between', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'up', 'down', 'is', 'are', 'am', 'was',
    'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
    'does', 'did', 'doing', 'would', 'should', 'could', 'ought', 'i',
    'you', 'he', 'she', 'it', 'we', 'they', 'myself', 'yourself',
    'himself', 'herself', 'itself', 'ourselves', 'themselves', 'which',
    'who', 'whom', 'this', 'that', 'these', 'those'
}

def summarize_job_description(text, max_sentences=3, max_length=300):
    """
    Create a concise summary of a job description.
    
    Args:
        text (str): Job description text
        max_sentences (int): Maximum number of sentences to include
        max_length (int): Maximum total length of summary
        
    Returns:
        str: Summarized job description
    """
    if not text:
        return ""
        
    try:
        # Check if the text is very short
        if len(text) < max_length:
            # If text is already short enough, clean it and return
            return clean_short_text(text)
        
        # First, try to find an existing summary or intro paragraph
        intro_summary = extract_intro_or_summary(text)
        if intro_summary and len(intro_summary) <= max_length:
            return intro_summary
            
        # Otherwise, generate a summary by extracting key sentences
        return extract_key_sentences(text, max_sentences, max_length)
        
    except Exception as e:
        logger.error(f"Error summarizing job description: {str(e)}")
        # Fallback: return first few characters
        return text[:max_length].strip() + "..."

def clean_short_text(text):
    """Clean a short text to serve as a summary."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # If the text contains newlines, use only the first paragraph
    paragraphs = text.split('\n\n')
    if len(paragraphs) > 1:
        return paragraphs[0].strip()
    
    return text

def extract_intro_or_summary(text):
    """
    Try to find an existing summary or introduction in the text.
    
    Args:
        text (str): Job description text
        
    Returns:
        str or None: Extracted summary or None if not found
    """
    # Look for common summary section headers
    summary_patterns = [
        r'(?:^|\n)(?:job\s+summary|position\s+summary|role\s+summary|about\s+the\s+role|about\s+the\s+position|job\s+description)[:\s]*\n',
        r'(?:^|\n)(?:overview|summary|introduction)[:\s]*\n',
        r'(?:^|\n)(?:about\s+the\s+job|about\s+the\s+opportunity)[:\s]*\n',
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get text after the header
            start_pos = match.end()
            
            # Find the end of this section (next section heading or double newline)
            end_match = re.search(r'\n\s*\n|\n[A-Z][^a-z\n]+:', text[start_pos:])
            
            if end_match:
                section_text = text[start_pos:start_pos + end_match.start()]
            else:
                # Take next 500 characters if no clear end found
                section_text = text[start_pos:start_pos + 500]
            
            # Clean up and return the found section
            return clean_and_format_summary(section_text)
    
    # If no summary section found, use the first paragraph that's reasonably sized
    paragraphs = text.split('\n\n')
    for paragraph in paragraphs[:3]:  # Check only first few paragraphs
        # Skip headers, bullet points, and very short paragraphs
        if (
            len(paragraph) > 50 and 
            not paragraph.isupper() and
            not re.match(r'^[•\-\*]', paragraph.strip())
        ):
            return clean_and_format_summary(paragraph)
    
    return None

def extract_key_sentences(text, max_sentences=3, max_length=300):
    """
    Extract key sentences from text based on importance.
    
    Args:
        text (str): Job description text
        max_sentences (int): Maximum number of sentences
        max_length (int): Maximum characters
        
    Returns:
        str: Summary composed of key sentences
    """
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out very short sentences, bullets, or ones that look like headings
    sentences = [s for s in sentences if len(s) > 20 and not s.isupper() and not re.match(r'^[•\-\*]', s.strip())]
    
    if not sentences:
        return ""
    
    # Score sentences based on position and keywords
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        score = score_sentence(sentence, i, len(sentences))
        scored_sentences.append((score, sentence))
    
    # Sort by score (highest first) and take top sentences
    scored_sentences.sort(reverse=True)
    top_sentences = [s[1] for s in scored_sentences[:max_sentences]]
    
    # Sort sentences back in their original order for readability
    original_order = []
    for sentence in top_sentences:
        original_order.append((sentences.index(sentence), sentence))
    original_order.sort()
    
    # Combine sentences and truncate if necessary
    result = ' '.join([s[1] for s in original_order])
    
    # Truncate if still too long
    if len(result) > max_length:
        return result[:max_length].strip() + "..."
        
    return result

def score_sentence(sentence, position, total_sentences):
    """
    Score a sentence based on various factors.
    
    Args:
        sentence (str): The sentence to score
        position (int): Position in the text
        total_sentences (int): Total number of sentences
        
    Returns:
        float: Score value
    """
    score = 0.0
    sentence_lower = sentence.lower()
    
    # Position score (higher for sentences at the beginning)
    position_score = 1.0 - (position / total_sentences)
    score += position_score * 2  # Weight position highly
    
    # Length score (favor medium length sentences)
    length = len(sentence)
    if 30 <= length <= 150:
        length_score = 1.0
    elif length < 30:
        length_score = length / 30
    else:
        length_score = 1.0 - ((length - 150) / 200)
    score += length_score
    
    # Keyword score
    keyword_count = sum(1 for keyword in PRIORITY_KEYWORDS if keyword.lower() in sentence_lower)
    keyword_score = min(1.0, keyword_count / 3)  # Cap at 1.0
    score += keyword_score * 3  # Weight keywords highly
    
    # Informational score (based on word importance)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence_lower)
    informational_words = [w for w in words if w not in STOPWORDS]
    
    # More informational words relative to total words is better
    if words:
        information_ratio = len(informational_words) / len(words)
        score += information_ratio
    
    return score

def clean_and_format_summary(text):
    """Clean and format extracted summary text."""
    # Remove excess whitespace, bullet points, etc.
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[•\-\*]\s*', '', text)
    
    # Add period at the end if missing
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    
    # Ensure first letter is capitalized
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text