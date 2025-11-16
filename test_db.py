#!/usr/bin/env python3
# test_db.py
from backend.db import create_job, get_job, serialize_job

# Test creating a job
job_id = create_job(prompt_text="Test prompt", file_path=None, file_name=None)
print(f"Created job with ID: {job_id}")

# Test getting the job
job_doc = get_job(job_id)
if job_doc:
    print("Job retrieved successfully:")
    print(serialize_job(job_doc))
else:
    print("Failed to retrieve job")
