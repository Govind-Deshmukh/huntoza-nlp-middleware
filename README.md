# Job Data Extraction API

This API service extracts structured job information from job postings. It can process both HTML and plain text inputs to extract relevant job details such as company name, position, location, salary, etc.

## Features

- Extract company names
- Extract job titles/positions
- Identify job location (including remote/hybrid detection)
- Determine job type (full-time, part-time, contract, etc.)
- Extract salary information with currency detection
- Extract job descriptions
- Process both HTML and plain text inputs

## Setup

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```

The API will be available at http://localhost:5000.

### Docker Installation

Alternatively, you can use Docker:

```
docker build -t job-extraction-api .
docker run -p 5000:5000 job-extraction-api
```

## API Usage

### Extract Job Data

**Endpoint:** `POST /api/extract-job-data`

**Request Body:**

For HTML content:

```json
{
  "html": "<html>... job posting HTML ...</html>"
}
```

For plain text:

```json
{
  "text": "Job Title: Software Engineer\nCompany: Acme Inc\n..."
}
```

**Response:**

```json
{
  "company": "Acme Inc",
  "position": "Software Engineer",
  "jobType": "full-time",
  "jobLocation": "Remote",
  "jobDescription": "We are looking for a skilled software engineer...",
  "jobUrl": "https://example.com/job/123",
  "salary": {
    "min": 100000,
    "max": 150000,
    "currency": "INR"
  }
}
```

## Integration with Job Hunt Tracker

This API is designed to work with the Job Hunt Tracker application. You can easily integrate it by:

1. Running this API service on your server
2. Configuring the Job Hunt Tracker to use this API endpoint
3. Using the Chrome extension to extract job data and send it to your job tracker app

## Example Code

Here's an example of how to use the API from JavaScript:

```javascript
async function extractJobData(htmlContent) {
  const response = await fetch("http://localhost:5000/api/extract-job-data", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      html: htmlContent,
    }),
  });

  return await response.json();
}
```

## License

MIT License
