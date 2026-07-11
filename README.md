# Resume Analyzer

A simple serverless application that analyzes your resume against job descriptions.

## What It Does

- Upload your resume (as a text file)
- Provide a job description you're interested in
- Get a match score showing how well your resume fits the job
- See which keywords from the job description are in your resume
- Find out which keywords you might be missing

## How to Use

### 1. Start the Application
Run Docker to start the backend:
```
docker compose up --build
```

### 2. Upload Your Resume
Open your browser at: **http://localhost:8000/docs**

Click on "POST /upload-resume" and:
- Upload your resume file
- Paste the job description in the text field
- Click Execute

### 3. See Your Results
The application returns:
- **Score**: How well your resume matches the job (0-100%)
- **Matched Keywords**: Keywords from the job that are in your resume
- **Missing Keywords**: Keywords you don't have but should mention
- **Top Terms**: The most common words in your resume
- **Suggestions**: Tips to improve your resume

## What You Need

- Docker (for running the application locally)
- A resume file (txt, md, or csv format)
- A job description to compare against

## How It Works Behind the Scenes

1. **FastAPI Backend**: Receives your resume and job description
2. **AWS Lambda**: Processes the resume and extracts keywords
3. **S3 Storage**: Stores your uploaded resume
4. **LocalStack**: Simulates AWS services locally

## Example

**Resume contains**: python, docker, fastapi, git
**Job description**: python, docker, aws, kubernetes

**Result**: 75% match with 3 matched keywords and 2 missing keywords

## Next Steps

- Add PDF and Word document support
- Create a web interface (not just the API)
- Make the analysis more advanced