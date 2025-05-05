# Job Data Extraction API Usage Guide

This guide demonstrates how to use the Job Data Extraction API with your Chrome extension and integrate it with your Job Hunt Tracker application.

## API Overview

The API provides a single primary endpoint for extracting structured data from job postings:

- **Endpoint**: `POST /api/extract-job-data`
- **Purpose**: Extract job details from HTML or text content
- **Input**: JSON with `html` or `text` field
- **Output**: Structured job data (company, position, location, etc.)

## Using the API from the Chrome Extension

Here's how to integrate the API with your Chrome extension:

### 1. Content Script - Extract HTML from Job Posting

In your Chrome extension's content script, capture the job posting HTML:

```javascript
// content.js
// This runs when your extension is activated on a job posting page

// Capture the HTML content of the current page
const jobHtml = document.documentElement.outerHTML;

// Send message to the background script with the HTML content
chrome.runtime.sendMessage({
  action: "extractJobData",
  html: jobHtml,
});
```

### 2. Background Script - Send to API

In your background script, receive the HTML content and send it to the API:

```javascript
// background.js

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractJobData") {
    // Send HTML to the extraction API
    fetchJobData(request.html)
      .then((jobData) => {
        // Save the extracted job data to storage
        chrome.storage.local.set({ pendingJobApplication: jobData });

        // Send response back to content script
        sendResponse({ success: true, data: jobData });
      })
      .catch((error) => {
        console.error("Error extracting job data:", error);
        sendResponse({ success: false, error: error.message });
      });

    // Return true to indicate we'll respond asynchronously
    return true;
  }
});

// Function to send HTML to the extraction API
async function fetchJobData(html) {
  const apiUrl = "http://localhost:5000/api/extract-job-data";

  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ html: html }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}
```

### 3. Popup Script - Show and Edit Extracted Data

In your extension's popup page, display the extracted data and allow the user to edit it:

```javascript
// popup.js

// When popup is opened, load the extracted job data
document.addEventListener("DOMContentLoaded", () => {
  // Get extracted job data from storage
  chrome.storage.local.get(["pendingJobApplication"], (result) => {
    if (result.pendingJobApplication) {
      // Display the data in the popup form
      displayJobData(result.pendingJobApplication);
    } else {
      // No data found, show message or try to extract
      showNoDataMessage();
    }
  });
});

// Function to display job data in the popup form
function displayJobData(jobData) {
  document.getElementById("company").value = jobData.company || "";
  document.getElementById("position").value = jobData.position || "";
  document.getElementById("jobLocation").value = jobData.jobLocation || "";
  document.getElementById("jobType").value = jobData.jobType || "full-time";

  // Display salary information
  document.getElementById("salaryCurrency").value =
    jobData.salary?.currency || "INR";
  document.getElementById("salaryMin").value = jobData.salary?.min || "";
  document.getElementById("salaryMax").value = jobData.salary?.max || "";

  // Display job description preview
  const previewElement = document.getElementById("jobDescriptionPreview");
  if (jobData.jobDescription) {
    const preview =
      jobData.jobDescription.substring(0, 200) +
      (jobData.jobDescription.length > 200 ? "..." : "");
    previewElement.textContent = preview;
  } else {
    previewElement.textContent = "No job description found";
  }

  // Set job URL
  document.getElementById("jobUrl").value =
    jobData.jobUrl || window.location.href;
}

// Function to show message when no data is found
function showNoDataMessage() {
  document.getElementById("errorMessage").classList.remove("hidden");
  document.getElementById("errorMessage").textContent =
    "No job data found. Click the 'Extract' button to try again.";
}

// Send to Job Tracker App button handler
document.getElementById("sendToAppButton").addEventListener("click", () => {
  // Get the current values from the form (including user edits)
  const updatedJobData = {
    company: document.getElementById("company").value,
    position: document.getElementById("position").value,
    jobLocation: document.getElementById("jobLocation").value,
    jobType: document.getElementById("jobType").value,
    salary: {
      min: parseInt(document.getElementById("salaryMin").value) || 0,
      max: parseInt(document.getElementById("salaryMax").value) || 0,
      currency: document.getElementById("salaryCurrency").value,
    },
    jobDescription: document.getElementById("jobDescriptionPreview").dataset
      .fullDescription,
    jobUrl: document.getElementById("jobUrl").value,
    // Add other fields as needed
  };

  // Save the updated job data to storage
  chrome.storage.local.set({ pendingJobApplication: updatedJobData });

  // Open the Job Hunt Tracker app in a new tab
  chrome.tabs.create({ url: "http://localhost:3000/jobs/new" });
});
```

## Integrating with the Job Hunt Tracker React App

To use the extracted job data in your React app, you need to handle the data passed from the Chrome extension:

### 1. React App - Detecting and Loading Job Data from Extension

In your JobFormPage.js, add code to detect and load job data from the extension:

```jsx
// In your JobFormPage component
useEffect(() => {
  // Function to check for job data from the Chrome extension
  const checkForExtensionJobData = () => {
    try {
      const storedJobData = localStorage.getItem("pendingJobData");
      if (storedJobData) {
        const jobData = JSON.parse(storedJobData);
        console.log("Received job data from extension:", jobData);

        // Update form with job data from extension
        setFormData({
          ...initialFormState,
          company: jobData.company || "",
          position: jobData.position || "",
          jobLocation: jobData.jobLocation || "remote",
          jobType: jobData.jobType || "full-time",
          jobDescription: jobData.jobDescription || "",
          jobUrl: jobData.jobUrl || "",
          priority: jobData.priority || "medium",
          favorite: jobData.favorite || false,
          salary: {
            min: jobData.salary?.min || 0,
            max: jobData.salary?.max || 0,
            currency: jobData.salary?.currency || "INR",
          },
        });

        // Set flag to show we received data from extension
        setExtensionDataReceived(true);

        // Clear the stored data after using it
        localStorage.removeItem("pendingJobData");
      }
    } catch (error) {
      console.error("Error processing extension job data:", error);
    }
  };

  // Listen for custom event from the Chrome extension
  const handleJobDataAvailable = (event) => {
    if (event.detail?.source === "chromeExtension") {
      checkForExtensionJobData();
    }
  };

  // Register the event listener
  window.addEventListener("jobDataAvailable", handleJobDataAvailable);

  // Check on initial load too
  checkForExtensionJobData();

  // Cleanup the event listener on unmount
  return () => {
    window.removeEventListener("jobDataAvailable", handleJobDataAvailable);
  };
}, []);
```

### 2. Browser Integration Script

When your Job Hunt Tracker app page loads, the Chrome extension can inject a script to transfer the job data:

```javascript
// This is injected by the Chrome extension into the Job Hunt Tracker app
function injectStateToReactApp(jobData) {
  console.log("Injecting job data into React app:", jobData);

  // Store the job data in localStorage so the React app can access it
  localStorage.setItem("pendingJobData", JSON.stringify(jobData));

  // Dispatch a custom event to notify the React app the data is ready
  window.dispatchEvent(
    new CustomEvent("jobDataAvailable", {
      detail: { source: "chromeExtension" },
    })
  );

  // Add visual feedback to let the user know the data was transferred
  showNotification("Job data transferred to form successfully!");
}

// Function to show a notification to the user
function showNotification(message) {
  // Check if notification already exists
  let notification = document.getElementById("extension-notification");

  if (!notification) {
    // Create notification element
    notification = document.createElement("div");
    notification.id = "extension-notification";

    // Style the notification
    Object.assign(notification.style, {
      position: "fixed",
      top: "20px",
      left: "50%",
      transform: "translateX(-50%)",
      backgroundColor: "#4CAF50",
      color: "white",
      padding: "12px 24px",
      borderRadius: "4px",
      boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
      zIndex: "10000",
      fontFamily: "Arial, sans-serif",
      fontSize: "14px",
      fontWeight: "bold",
      opacity: "0",
      transition: "opacity 0.3s ease-in-out",
    });

    // Set the message
    notification.textContent = message;

    // Add to the page
    document.body.appendChild(notification);

    // Trigger animation
    setTimeout(() => {
      notification.style.opacity = "1";
    }, 10);

    // Remove after 5 seconds
    setTimeout(() => {
      notification.style.opacity = "0";
      setTimeout(() => {
        if (notification && notification.parentNode) {
          document.body.removeChild(notification);
        }
      }, 300);
    }, 5000);
  }
}
```

## Deployment Options

You can deploy the Job Data Extraction API in several ways:

### 1. Local Development

Run the API locally for development and testing:

```bash
python app.py
```

The API will be available at http://localhost:5000.

### 2. Docker Deployment

Deploy using Docker for better isolation and scalability:

```bash
# Build the Docker image
docker build -t job-extraction-api .

# Run the container
docker run -d -p 5000:5000 --name job-api job-extraction-api
```

### 3. Cloud Deployment

For production, deploy to a cloud provider like AWS, Google Cloud, or Microsoft Azure:

- **AWS Elastic Beanstalk**: Simple deployment for Flask applications
- **Google Cloud Run**: Serverless container deployment
- **Azure App Service**: Managed service for web applications

## API Response Format

The API returns structured job data in this format:

```json
{
  "company": "Acme Inc",
  "position": "Senior Software Engineer",
  "jobType": "full-time",
  "jobLocation": "Remote",
  "jobDescription": "We're looking for an experienced software engineer...",
  "jobUrl": "https://example.com/jobs/123",
  "salary": {
    "min": 100000,
    "max": 150000,
    "currency": "INR"
  }
}
```

## Error Handling

The API returns clear error messages in case of problems:

```json
{
  "error": "Failed to extract job data",
  "details": "Error details here"
}
```

## Troubleshooting

If you encounter issues with the integration:

1. **API Connection Issues**: Ensure the API is running and accessible
2. **CORS Problems**: Make sure your React app's domain is allowed in the API's CORS configuration
3. **Extraction Failures**: The API might struggle with certain job posting formats
4. **Storage Issues**: Check if localStorage is available and not full

## Enhancing the Extraction

If the extraction quality needs improvement:

1. Adjust the regex patterns in `regex_extractors.py`
2. Add more patterns for specific job boards
3. Improve the HTML content extraction in `html_utils.py`
4. Add domain-specific rules for known job board sites
