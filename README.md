# Serverless Resume Analyzer

Local demo flow:

1. FastAPI receives a resume upload.
2. FastAPI stores the file in LocalStack S3.
3. FastAPI invokes a LocalStack Lambda.
4. Lambda reads the resume from S3 and returns a simple keyword match analysis.

## Run

```powershell
docker compose up --build
```

Open:

- API root: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

## Test Upload

Use the Swagger UI at `/docs`, or run:

```powershell
curl.exe -X POST "http://localhost:8000/upload-resume" `
  -F "file=@sample.txt" `
  -F "job_description=python fastapi docker aws lambda s3"
```

The first version supports text-like resumes best. PDF and DOCX parsing can be added next with `pypdf` and `python-docx`.

I built this projet to demonstrate my knowlege in cloud and experiment