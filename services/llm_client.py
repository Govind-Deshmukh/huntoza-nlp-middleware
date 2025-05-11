"""
services/llm_client.py - Client for interacting with Ollama LLM

Provides a simple interface for sending prompts to Ollama and handling responses.
Includes fallback processing for when Ollama is unavailable or overloaded.
"""
import os
import re
import json
import logging
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Client for interacting with Ollama LLM.
    """
    
    def __init__(self):
        """Initialize LLM client."""
        self.base_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        self.default_model = os.environ.get('OLLAMA_MODEL', 'llama2')
        self.timeout = int(os.environ.get('OLLAMA_TIMEOUT', 30))
        self.available = self._check_availability()
        
        if not self.available:
            logger.warning("Ollama is not available. Using fallback processing.")
    
    def _check_availability(self):
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"Ollama is not available: {str(e)}")
            return False
    
    @lru_cache(maxsize=10)
    def get_available_models(self):
        """Get list of available models from Ollama."""
        if not self.available:
            return []
            
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.RequestException as e:
            logger.error(f"Error getting available models: {str(e)}")
            return []
    
    def process_job(self, job_description, model=None):
        """
        Process job description using Ollama.
        
        Args:
            job_description (str): Job description text
            model (str): Model name, defaults to OLLAMA_MODEL env var
            
        Returns:
            dict: Processed job data or None if processing failed
        """
        if not self.available:
            return None
            
        # Check if model is available
        model = model or self.default_model
        
        # Build job processing prompt
        prompt = (
            "You are an AI assistant that specializes in analyzing job descriptions. "
            "Extract the following information from the job description text:\n\n"
            "1. skills: A list of required technical and soft skills (as an array of strings)\n"
            "2. summary: A brief 2-3 sentence summary of the job\n"
            "3. highlights: Top 3-5 most appealing aspects of this job (as an array of strings)\n"
            "4. notes: Additional important details a job seeker should know\n\n"
            "Format your response as JSON with these fields. Be concise and factual."
        )
        
        # Truncate job description if too long
        max_desc_length = 4000
        if len(job_description) > max_desc_length:
            truncated = job_description[:max_desc_length]
            logger.info(f"Truncated job description from {len(job_description)} to {len(truncated)} characters")
            job_description = truncated
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{prompt}\n\nJOB DESCRIPTION:\n'''\n{job_description}\n'''",
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Lower temperature for more factual outputs
                        "num_predict": 1024,  # Limit token generation
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Error from Ollama API: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            generated_text = result.get('response', '')
            
            # Try to extract JSON from response
            try:
                # Look for JSON block
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{\s*"[\w]+"\s*:[\s\S]*}', generated_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(0)
                    data = json.loads(json_str)
                    
                    # Add quality score based on completeness
                    data['quality_score'] = self._calculate_quality_score(data)
                    
                    return data
                else:
                    # Try to parse the entire response as JSON
                    data = json.loads(generated_text)
                    data['quality_score'] = self._calculate_quality_score(data)
                    return data
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from Ollama response")
                logger.debug(f"Response was: {generated_text[:500]}...")
                
                # Try to extract structured data from unstructured response
                return self._extract_data_from_text(generated_text)
                
        except requests.RequestException as e:
            logger.error(f"Error communicating with Ollama: {str(e)}")
            return None
    
    def _calculate_quality_score(self, data):
        """
        Calculate quality score for LLM output based on completeness.
        
        Args:
            data (dict): Data from LLM
            
        Returns:
            float: Quality score between 0 and 1
        """
        score = 0.0
        
        # Check for skills
        if 'skills' in data and isinstance(data['skills'], list) and len(data['skills']) > 0:
            skill_score = min(1.0, len(data['skills']) / 5)  # At least 5 skills for full score
            score += 0.3 * skill_score
        
        # Check for summary
        if 'summary' in data and isinstance(data['summary'], str) and len(data['summary']) > 10:
            summary_score = min(1.0, len(data['summary']) / 100)  # At least 100 chars for full score
            score += 0.3 * summary_score
        
        # Check for highlights
        if 'highlights' in data and isinstance(data['highlights'], list) and len(data['highlights']) > 0:
            highlight_score = min(1.0, len(data['highlights']) / 3)  # At least 3 highlights for full score
            score += 0.3 * highlight_score
        
        # Check for notes
        if 'notes' in data and isinstance(data['notes'], str) and len(data['notes']) > 0:
            note_score = min(1.0, len(data['notes']) / 50)  # At least 50 chars for full score
            score += 0.1 * note_score
        
        return score
    
    def _extract_data_from_text(self, text):
        """
        Extract structured data from unstructured text response.
        
        Args:
            text (str): Unstructured text response
            
        Returns:
            dict: Extracted data or None
        """
        result = {
            'skills': [],
            'summary': '',
            'highlights': [],
            'notes': '',
            'quality_score': 0.5  # Default lower quality score
        }
        
        # Look for skills section
        skills_match = re.search(r'(?:skills|requirements):\s*(?:\n|-)+((?:.+(?:\n|$))+)', text, re.IGNORECASE)
        if skills_match:
            # Extract skills from bullet points or comma-separated list
            skills_text = skills_match.group(1)
            skills = re.findall(r'[-•*]\s*([^-•*\n]+)', skills_text)
            if not skills:
                skills = [s.strip() for s in skills_text.split(',')]
            result['skills'] = [s.strip() for s in skills if s.strip()]
        
        # Look for summary section
        summary_match = re.search(r'(?:summary|overview):\s*([^\n]+(?:\n[^\n]+){0,2})', text, re.IGNORECASE)
        if summary_match:
            result['summary'] = summary_match.group(1).strip()
        
        # Look for highlights section
        highlights_match = re.search(r'(?:highlights|benefits|perks):\s*(?:\n|-)+((?:.+(?:\n|$))+)', text, re.IGNORECASE)
        if highlights_match:
            highlights_text = highlights_match.group(1)
            highlights = re.findall(r'[-•*]\s*([^-•*\n]+)', highlights_text)
            if not highlights:
                highlights = [h.strip() for h in highlights_text.split('\n')]
            result['highlights'] = [h.strip() for h in highlights if h.strip()]
        
        # Look for notes section
        notes_match = re.search(r'(?:notes|additional):\s*([^\n]+(?:\n[^\n]+)*)', text, re.IGNORECASE)
        if notes_match:
            result['notes'] = notes_match.group(1).strip()
        
        return result

def fallback_processing(job_description):
    """
    Fallback processing when LLM is not available.
    
    Args:
        job_description (str): Job description text
        
    Returns:
        dict: Processed job data using rule-based methods
    """
    from services.extractors.skills_extractor import extract_skills
    from services.extractors.summary_extractor import summarize_job_description
    from services.extractors.highlights_extractor import extract_highlights
    
    return {
        'skills': extract_skills(job_description),
        'summary': summarize_job_description(job_description),
        'highlights': extract_highlights(job_description),
        'notes': '',
        'quality_score': 0.7  # Rule-based extraction often works quite well
    }
