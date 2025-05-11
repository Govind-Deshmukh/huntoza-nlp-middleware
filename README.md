# PursuitPal Job Data Extractor

The Job Data Extractor service acts as a middleware between the PursuitPal job application tracking frontend and various data sources. It provides API endpoints to extract, process, and enhance job posting data from HTML or plain text sources.

## Overview

This middleware service facilitates the PursuitPal application by:

- Extracting structured data from job postings (both HTML and plain text)
- Identifying key skills, job requirements, and company information
- Generating summaries and highlights for easy review
- Providing optional LLM-enhanced analysis for more comprehensive results
- Caching results to improve performance and reduce processing time

## Technology Stack

- **Backend**: Flask-based Python API
- **Data Processing**: Rule-based extractors with optional LLM enhancement
- **LLM Integration**: Ollama integration for advanced text analysis
- **Containerization**: Docker support with docker-compose configuration

## Installation

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)
- Ollama (optional, for LLM-enhanced extraction)

### Setup

1. Clone the repository:

   ```bash
   git clone [repository-url]
   cd pursuitpal-job-data-extractor
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:

   ```bash
   # Required
   export DEBUG=False
   export PORT=5000
   export HOST=0.0.0.0

   # Optional (for LLM integration)
   export OLLAMA_URL=http://localhost:11434
   export OLLAMA_MODEL=llama2
   export OLLAMA_TIMEOUT=30
   export MAX_CONCURRENT_OLLAMA=3
   ```

### Docker Deployment

1. Build and start the services:

   ```bash
   docker-compose up -d
   ```

2. The API will be available at `http://localhost:5000`

## API Endpoints

### 1. Health Check

```
GET /
```

Returns service status information and available endpoints.

**Response Example:**

```json
{
  "status": "online",
  "service": "Job Data Processing Middleware",
  "version": "1.0.0",
  "endpoints": {
    "/api/extract-job-data": "POST - Extract structured data from job posting HTML or text"
  }
}
```

### 2. Extract Job Data

```
POST /api/extract-job-data
```

Processes job posting content and extracts structured data.

**Request Body:**

```json
{
  "html": "<html>...</html>", // OR
  "text": "Job description text...",
  "use_llm": true, // Optional, default: false
  "format": "detailed" // Optional, default: "basic"
}
```

**Response Example:**

```json
{
  "skills": ["JavaScript", "React", "Node.js", "MongoDB", "AWS"],
  "summary": "Software Engineer position at TechCorp focused on full-stack development using JavaScript technologies.",
  "highlights": [
    "Competitive salary and benefits package",
    "Remote work available",
    "Professional development opportunities"
  ],
  "analysis": {
    // Only included in "detailed" format
    "detected_job_type": "full-time",
    "education_requirements": "Bachelor's degree in Computer Science or related field",
    "experience_level": "3-5 years",
    "remote_status": "hybrid"
  },
  "_meta": {
    "cached": false,
    "processing_time_ms": 352,
    "timestamp": "2025-05-12T10:15:30.123456",
    "llm_enhanced": true
  }
}
```

## Rate Limiting

The API includes rate limiting to prevent abuse:

- `/api/extract-job-data` is limited to 20 requests per minute

## Development Guide

### Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Container orchestration
├── services/
│   ├── cache_manager.py   # In-memory caching
│   ├── llm_client.py      # Ollama integration
│   ├── extraction_service.py # Core extraction logic
│   └── extractors/        # Specialized extractors
│       ├── skills_extractor.py
│       ├── summary_extractor.py
│       └── highlights_extractor.py
└── utils/
    ├── html_utils.py      # HTML processing utilities
    └── regex_extractors.py # Pattern-based extractors
```

### Key Components

1. **Extraction Service**: The core logic for processing job data
2. **Extractors**: Specialized modules for skills, summaries, and highlights
3. **LLM Client**: Integration with Ollama for enhanced extraction
4. **Cache Manager**: In-memory caching system with TTL support

### Adding New Features

1. Create a new extractor in `services/extractors/`
2. Update the main extraction endpoint in `app.py`
3. Add any necessary utility functions in `utils/`

## Integration with PursuitPal

This middleware is designed to work with the PursuitPal job tracking application:

1. **Browser Extension**: Captures job posting data from various job boards
2. **Middleware (this service)**: Processes and enhances the job data
3. **Web Application**: Stores and displays the processed job information

The browser extension can directly communicate with this middleware to process job data before sending it to the main application.
