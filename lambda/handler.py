import json
import os
import re
from collections import Counter

import boto3


AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
LOCALSTACK_ENDPOINT = os.getenv(
    "LOCALSTACK_ENDPOINT",
    "http://localhost.localstack.cloud:4566",
)


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def parse_event(event):
    if "body" in event and isinstance(event["body"], str):
        try:
            return json.loads(event["body"])
        except json.JSONDecodeError:
            return {}
    return event


def extract_text(file_bytes, filename):
    suffix = os.path.splitext(filename or "")[1].lower()
    if suffix in {".txt", ".md", ".csv"}:
        return file_bytes.decode("utf-8", errors="ignore")

    # The first demo stays dependency-free. Add pypdf/python-docx later for
    # production-grade PDF and Word parsing.
    return file_bytes.decode("utf-8", errors="ignore")


def words(text):
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower()))


def top_terms(text, limit=12):
    ignored = {
        "and",
        "the",
        "with",
        "for",
        "from",
        "that",
        "this",
        "you",
        "your",
        "are",
        "will",
        "have",
        "has",
        "resume",
    }
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
    counts = Counter(word for word in tokens if word not in ignored)
    return [word for word, _ in counts.most_common(limit)]


def analyze_resume(resume_text, job_description):
    resume_words = words(resume_text)
    job_words = words(job_description)

    if job_words:
        matched = sorted(resume_words & job_words)
        missing = sorted(job_words - resume_words)
        score = round((len(matched) / len(job_words)) * 100)
    else:
        matched = []
        missing = []
        score = 0

    suggestions = []
    if not job_description.strip():
        suggestions.append("Add a job description to get a meaningful match score.")
    if len(resume_text.split()) < 80:
        suggestions.append("Resume text looks short; add projects, metrics, and impact.")
    if missing:
        suggestions.append("Mention the strongest missing job keywords if you truly have that experience.")
    if score >= 70:
        suggestions.append("Good keyword alignment. Tighten bullets with measurable outcomes.")

    return {
        "score": score,
        "matched_keywords": matched[:25],
        "missing_keywords": missing[:25],
        "resume_terms": top_terms(resume_text),
        "word_count": len(resume_text.split()),
        "suggestions": suggestions,
    }


def handler(event, context):
    payload = parse_event(event)
    bucket = payload.get("bucket")
    key = payload.get("key")
    filename = payload.get("filename", key or "resume.txt")
    job_description = payload.get("job_description", "")

    if not bucket or not key:
        return response(400, {"error": "bucket and key are required"})

    try:
        obj = s3_client().get_object(Bucket=bucket, Key=key)
        file_bytes = obj["Body"].read()
        resume_text = extract_text(file_bytes, filename)
        analysis = analyze_resume(resume_text, job_description)
        analysis["source"] = {"bucket": bucket, "key": key, "filename": filename}
        return response(200, analysis)
    except Exception as exc:
        return response(500, {"error": str(exc)})
