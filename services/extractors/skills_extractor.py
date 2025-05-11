"""
services/extractors/skills_extractor.py - Extract skills from job descriptions

Identifies technical and soft skills mentioned in job descriptions using pattern matching
and keyword recognition.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Technical skills database with categories
TECHNICAL_SKILLS = {
    'programming_languages': [
        'python', 'java', 'javascript', 'js', 'typescript', 'c++', 'c#', 'ruby', 'go', 'golang',
        'php', 'swift', 'kotlin', 'rust', 'scala', 'perl', 'r', 'dart', 'sql', 'bash',
        'shell', 'powershell', 'vba', 'matlab', 'objective-c', 'assembly', 'fortran', 'cobol',
        'html', 'css', 'sass', 'less', 'xml'
    ],
    'frameworks_libraries': [
        'react', 'angular', 'vue', 'django', 'flask', 'spring', 'node.js', 'nodejs', 'express',
        'laravel', 'symfony', 'rails', 'jquery', 'bootstrap', 'tailwind', 'redux', 'next.js',
        'gatsby', 'svelte', 'ember', 'backbone', 'nuxt', 'flask', 'fastapi', 'tensorflow',
        'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 
        'opencv', 'spring boot', 'hibernate', '.net', '.net core', 'asp.net', 'xamarin', 
        'flutter', 'react native', 'ionic', 'electron', 'rxjs', 'matplotlib', 'puppeteer'
    ],
    'databases': [
        'sql', 'mysql', 'postgresql', 'postgres', 'oracle', 'mongodb', 'cassandra', 'redis',
        'sqlite', 'mariadb', 'dynamodb', 'couchdb', 'firebase', 'firestore', 'neo4j', 
        'graphql', 'elasticsearch', 'solr', 'hadoop', 'hive', 'snowflake', 'teradata',
        'cosmosdb', 'ms sql', 'microsoft sql server', 'bigtable', 'influxdb', 'memcached',
        'hbase', 'realm', 'supabase', 'fauna'
    ],
    'cloud_devops': [
        'aws', 'amazon web services', 'azure', 'google cloud', 'gcp', 'docker', 'kubernetes',
        'terraform', 'jenkins', 'gitlab ci', 'github actions', 'circleci', 'travis ci',
        'ansible', 'puppet', 'chef', 'prometheus', 'grafana', 'elk stack', 'cloudformation',
        'pulumi', 'heroku', 'digitalocean', 'vercel', 'netlify', 's3', 'ec2', 'lambda',
        'serverless', 'microservices', 'ci/cd', 'continuous integration', 'continuous deployment',
        'cloud native', 'helm', 'istio', 'service mesh', 'devops', 'sre', 'site reliability'
    ],
    'tools_platforms': [
        'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'trello', 'slack',
        'asana', 'notion', 'figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator',
        'visual studio', 'intellij', 'pycharm', 'eclipse', 'vscode', 'sublime text',
        'atom', 'vim', 'emacs', 'postman', 'insomnia', 'webpack', 'babel', 'gulp', 'grunt',
        'npm', 'yarn', 'pip', 'gradle', 'maven', 'make', 'cmake', 'jupyter', 'tableau',
        'power bi', 'looker', 'airflow', 'linux', 'unix', 'windows', 'macos'
    ],
    'data_science_ai': [
        'machine learning', 'ml', 'deep learning', 'dl', 'ai', 'artificial intelligence',
        'nlp', 'natural language processing', 'computer vision', 'neural networks', 'cnn',
        'rnn', 'lstm', 'reinforcement learning', 'data mining', 'etl', 'data analysis',
        'statistical analysis', 'a/b testing', 'hypothesis testing', 'time series',
        'regression', 'classification', 'clustering', 'bayesian', 'data visualization',
        'feature engineering', 'dimensionality reduction', 'big data', 'data pipeline',
        'data modeling', 'data warehouse', 'data lake', 'predictive modeling', 
        'recommendation systems'
    ]
}

# Flatten the technical skills dictionary for easier searching
ALL_TECHNICAL_SKILLS = set()
for category in TECHNICAL_SKILLS.values():
    ALL_TECHNICAL_SKILLS.update(category)

# Soft skills to look for
SOFT_SKILLS = [
    'communication', 'teamwork', 'collaboration', 'problem solving', 'problem-solving', 
    'critical thinking', 'leadership', 'time management', 'adaptability', 'creativity',
    'flexibility', 'interpersonal', 'attention to detail', 'detail-oriented',
    'project management', 'planning', 'organization', 'organizational', 'multitasking',
    'prioritization', 'analytical', 'analytical thinking', 'presentation', 'writing',
    'verbal communication', 'written communication', 'persuasion', 'negotiation',
    'conflict resolution', 'customer service', 'team player', 'proactive', 'initiative',
    'self-motivated', 'self-starter', 'goal-oriented', 'results-driven', 'decision making',
    'decision-making', 'research', 'mentoring', 'coaching', 'emotional intelligence',
    'cultural awareness', 'cross-cultural', 'public speaking', 'relationship building',
    'active listening', 'empathy', 'work ethic', 'patience', 'resilience', 'networking',
    'strategic thinking', 'innovation', 'stress management', 'people management'
]

def extract_skills(text):
    """
    Extract skills from job description text.
    
    Args:
        text (str): Job description text
        
    Returns:
        list: List of extracted skills
    """
    if not text:
        return []
        
    try:
        # Normalize text for better matching
        normalized_text = normalize_text(text)
        
        # Extract skills using different approaches
        skills = []
        
        # Method 1: Extract from "Skills" and "Requirements" sections
        skills_from_sections = extract_from_sections(normalized_text)
        skills.extend(skills_from_sections)
        
        # Method 2: Extract from bullet points
        skills_from_bullets = extract_from_bullets(normalized_text)
        skills.extend(skills_from_bullets)
        
        # Method 3: Look for known skills throughout the text
        skills_from_keywords = extract_from_keywords(normalized_text)
        skills.extend(skills_from_keywords)
        
        # Deduplicate, clean up and rank skills
        return rank_and_clean_skills(skills)
        
    except Exception as e:
        logger.error(f"Error extracting skills: {str(e)}")
        return []

def normalize_text(text):
    """Normalize text for better pattern matching."""
    # Convert to lowercase
    text = text.lower()
    
    # Replace common abbreviations and variations
    replacements = {
        'js': 'javascript',
        'react.js': 'react',
        'reactjs': 'react',
        'vue.js': 'vue',
        'vuejs': 'vue',
        'node.js': 'nodejs',
        'next.js': 'nextjs',
        'gatsby.js': 'gatsby',
        'express.js': 'express',
        'postgresql': 'postgres',
    }
    
    for original, replacement in replacements.items():
        text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text)
    
    # Keep the original text, just with replacements
    return text

def extract_from_sections(text):
    """Extract skills from specific sections like 'Skills' or 'Requirements'."""
    skills = []
    
    # Common section headers
    section_patterns = [
        r'(?:^|\n)(?:technical\s+)?(?:skills|qualifications)(?:\s+required)?(?:\s+and\s+experience)?[:\s]*\n',
        r'(?:^|\n)requirements[:\s]*\n',
        r'(?:^|\n)(?:what\s+you\'ll\s+need|what\s+you\s+need|you\s+have)[:\s]*\n',
        r'(?:^|\n)(?:required|minimum)\s+(?:skills|qualifications)[:\s]*\n',
        r'(?:^|\n)(?:technical\s+requirements|technical\s+skills)[:\s]*\n',
        r'(?:^|\n)(?:your\s+skills|your\s+experience)[:\s]*\n',
    ]
    
    for pattern in section_patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            # Get the position right after the header
            start_pos = matches.end()
            
            # Find the end of this section (next section heading or double newline)
            end_match = re.search(r'\n\s*\n|\n[A-Z][^a-z\n]+:', text[start_pos:])
            
            if end_match:
                section_text = text[start_pos:start_pos + end_match.start()]
            else:
                # Take next 500 characters if no clear end found
                section_text = text[start_pos:start_pos + 500]
            
            # Extract skills from this section
            skills_in_section = []
            
            # Look for bullet points first
            bullet_matches = re.findall(r'(?:^|\n)[•\-\*]\s*([^\n•\-\*]+)', section_text)
            for bullet in bullet_matches:
                bullet = bullet.strip()
                if len(bullet) > 3:  # Skip very short bullets
                    skills_in_section.append(bullet)
            
            # If no bullet points, look for sentence fragments
            if not skills_in_section:
                sentences = re.split(r'(?<=[.!?])\s+', section_text)
                for sentence in sentences:
                    if 3 < len(sentence) < 150:  # Reasonable size for a skill description
                        skills_in_section.append(sentence.strip())
            
            skills.extend(skills_in_section)
    
    return skills

def extract_from_bullets(text):
    """Extract skills from bullet points throughout the text."""
    skills = []
    
    # Look for bullet points followed by text
    bullet_matches = re.findall(r'(?:^|\n)[•\-\*]\s*([^\n•\-\*]+)', text)
    
    for bullet in bullet_matches:
        bullet = bullet.strip()
        
        # Skip very short bullets or bullets that look like headings
        if len(bullet) < 3 or bullet.isupper():
            continue
            
        # Check if bullet contains skill keywords
        if (
            any(skill in bullet for skill in ALL_TECHNICAL_SKILLS) or
            any(skill in bullet for skill in SOFT_SKILLS)
        ):
            skills.append(bullet)
    
    return skills

def extract_from_keywords(text):
    """Extract skills by looking for direct keyword matches."""
    skills = []
    
    # Technical skills
    for skill in ALL_TECHNICAL_SKILLS:
        # Ensure we match whole words only to avoid partial matches
        # e.g. 'css' shouldn't match 'access'
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            skills.append(skill)
    
    # Soft skills
    for skill in SOFT_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            skills.append(skill)
    
    return skills

def rank_and_clean_skills(skills_list):
    """
    Deduplicate, clean and rank extracted skills.
    
    Args:
        skills_list (list): Raw extracted skills
        
    Returns:
        list: Cleaned and ranked skills
    """
    if not skills_list:
        return []
    
    # First, extract known skills from each raw skill phrase
    extracted_skills = []
    for raw_skill in skills_list:
        # Direct matches (simple skills)
        if raw_skill in ALL_TECHNICAL_SKILLS or raw_skill in SOFT_SKILLS:
            extracted_skills.append(raw_skill)
            continue
            
        # For longer texts, look for known skills within them
        found = False
        for skill in ALL_TECHNICAL_SKILLS:
            if re.search(r'\b' + re.escape(skill) + r'\b', raw_skill):
                extracted_skills.append(skill)
                found = True
                
        for skill in SOFT_SKILLS:
            if re.search(r'\b' + re.escape(skill) + r'\b', raw_skill):
                extracted_skills.append(skill)
                found = True
                
        # If no known skill found, keep the original if it's reasonably short
        if not found and len(raw_skill) < 50:
            extracted_skills.append(raw_skill)
    
    # Count frequencies to identify most common skills
    skill_counter = Counter(extracted_skills)
    
    # Deduplicate, keeping most frequent skills and ensuring a mix of technical and soft skills
    tech_skills = []
    soft_skills = []
    other_skills = []
    
    for skill, count in skill_counter.most_common():
        # Normalize skill name
        normalized = skill.lower()
        
        # Skip very short skills unless they're known technical terms
        if len(normalized) < 3 and normalized not in ALL_TECHNICAL_SKILLS:
            continue
            
        # Categorize the skill
        if normalized in ALL_TECHNICAL_SKILLS:
            if normalized not in [s.lower() for s in tech_skills]:
                # Format known technical skills properly (e.g., JavaScript not javascript)
                for category in TECHNICAL_SKILLS.values():
                    if normalized in category:
                        idx = category.index(normalized)
                        tech_skills.append(category[idx])
                        break
        elif normalized in SOFT_SKILLS:
            if normalized not in [s.lower() for s in soft_skills]:
                # Capitalize first letter of soft skills
                soft_skills.append(normalized.capitalize())
        else:
            if normalized not in [s.lower() for s in other_skills]:
                # Capitalize first letter of other skills
                other_skills.append(normalized.capitalize())
    
    # Combine lists, prioritizing technical and soft skills
    result = tech_skills[:15] + soft_skills[:10] + other_skills[:5]
    
    # Limit total skills to 20
    return result[:20]