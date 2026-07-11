import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile


AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
S3_BUCKET = os.getenv("S3_BUCKET", "resume-uploads")
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "resume-analyzer")


def aws_client(service_name: str):
    return boto3.client(
        service_name,
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


s3 = aws_client("s3")
lambda_client = aws_client("lambda")


def ensure_bucket() -> None:
    last_error = None
    for _ in range(30):
        try:
            s3.head_bucket(Bucket=S3_BUCKET)
            return
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchBucket", "NotFound"}:
                s3.create_bucket(Bucket=S3_BUCKET)
                return
            last_error = exc
        except BotoCoreError as exc:
            last_error = exc
        time.sleep(1)

    raise RuntimeError(f"Could not connect to LocalStack S3: {last_error}")


def parse_lambda_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("Lambda returned an unexpected payload")

    body = payload.get("body")
    if isinstance(body, str):
        try:
            payload["body"] = json.loads(body)
        except json.JSONDecodeError:
            pass
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    yield


app = FastAPI(title="Serverless Resume Analyzer", lifespan=lifespan)


@app.get("/")
def home():
    return {
        "message": "Resume Analyzer API Running",
        "try": "POST /upload-resume with form fields file and job_description",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bucket": S3_BUCKET,
        "lambda": LAMBDA_FUNCTION_NAME,
        "localstack": LOCALSTACK_ENDPOINT,
    }


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A resume file is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded resume is empty")

    resume_id = str(uuid.uuid4())
    safe_filename = os.path.basename(file.filename).replace(" ", "_")
    object_key = f"resumes/{resume_id}-{safe_filename}"

    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=object_key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
            Metadata={"original_filename": file.filename},
        )

        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(
                {
                    "bucket": S3_BUCKET,
                    "key": object_key,
                    "filename": file.filename,
                    "job_description": job_description,
                }
            ).encode("utf-8"),
        )
        lambda_payload = parse_lambda_payload(response["Payload"].read())
    except ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    status_code = int(lambda_payload.get("statusCode", 200))
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=lambda_payload.get("body"))

    return {
        "resume_id": resume_id,
        "bucket": S3_BUCKET,
        "key": object_key,
        "analysis": lambda_payload.get("body", lambda_payload),
    }
