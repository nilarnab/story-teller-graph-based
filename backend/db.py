# backend/db.py
import os
from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "prompt_video_app")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
jobs_col = db["jobs"]

def _to_object_id(job_id: str) -> ObjectId:
    """Convert string job_id to ObjectId, or raise ValueError."""
    try:
        return ObjectId(job_id)
    except Exception:
        raise ValueError("Invalid job_id")

def create_job(prompt_text: str, file_path: str | None, file_name: str | None) -> str:
    """Insert a new job into MongoDB and return its string job_id."""
    job_doc = {
        "prompt_text": prompt_text,
        "file_path": file_path,
        "file_name": file_name,
        "status": "pending",      
        "description": None,
        "video_url": None,
        "error": None,
        "created_at": datetime.utcnow(),
    }

    result = jobs_col.insert_one(job_doc)
    return str(result.inserted_id)

def get_job(job_id: str) -> dict | None:
    oid = _to_object_id(job_id)
    return jobs_col.find_one({"_id": oid})

def mark_job_done(job_id: str, description: str, video_url: str) -> dict | None:
    oid = _to_object_id(job_id)
    result = jobs_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "status": "done",
                "description": description,
                "video_url": video_url,
                "error": None,
            }
        },
    )
    if result.matched_count == 0:
        return None
    return jobs_col.find_one({"_id": oid})

def serialize_job(job_doc: dict) -> dict:
    if not job_doc:
        return None

    return {
        "job_id": str(job_doc["_id"]),
        "status": job_doc.get("status", "unknown"),
        "text": job_doc.get("description"), 
        "video_url": job_doc.get("video_url"),
        "error": job_doc.get("error"),
    }
