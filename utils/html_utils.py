"""
HTML processing utilities for job data extraction.
"""
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

def extract_text_from_html(html_content):
    """
    Extract clean text from HTML content.
    
    Args:
        html_content (str): HTML content from job posting
        
    Returns:
        str: Clean text with preserved structure
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Remove blank lines and join with newlines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {str(e)}")
        return html_content  # Return original content if parsing fails

def extract_job_url(html_content):
    """
    Extract job posting URL from HTML content.
    
    Args:
        html_content (str): HTML content
        
    Returns:
        str: URL of the job posting
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            return canonical.get('href')
        
        # Look for og:url meta tag
        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            return og_url.get('content')
        
        # Look for any other URL in meta tags
        meta_url = soup.find('meta', {'name': 'url'})
        if meta_url and meta_url.get('content'):
            return meta_url.get('content')
        
        # Try to find the current page URL
        base_url = soup.find('base', href=True)
        if base_url and base_url.get('href'):
            return base_url.get('href')
        
        return ""
    except Exception as e:
        logger.error(f"Error extracting URL from HTML: {str(e)}")
        return ""

def extract_metadata_fields(html_content):
    """
    Extract job-related metadata from HTML meta tags.
    
    Args:
        html_content (str): HTML content
        
    Returns:
        dict: Dictionary of metadata values
    """
    metadata = {
        "title": "",
        "company": "",
        "location": "",
        "description": ""
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            metadata["title"] = og_title.get('content')
        else:
            title_tag = soup.find('title')
            if title_tag:
                metadata["title"] = title_tag.text
        
        # Extract company
        company_meta = soup.find('meta', {'name': 'company'}) or soup.find('meta', {'property': 'og:site_name'})
        if company_meta and company_meta.get('content'):
            metadata["company"] = company_meta.get('content')
        
        # Extract location
        location_meta = soup.find('meta', {'name': 'location'}) or soup.find('meta', {'name': 'geo.placename'})
        if location_meta and location_meta.get('content'):
            metadata["location"] = location_meta.get('content')
        
        # Extract description
        description_meta = soup.find('meta', {'name': 'description'}) or soup.find('meta', {'property': 'og:description'})
        if description_meta and description_meta.get('content'):
            metadata["description"] = description_meta.get('content')
        
        return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata from HTML: {str(e)}")
        return metadata