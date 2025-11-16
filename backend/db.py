# backend/db.py
import os
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
from pymongo import ReturnDocument

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = "hack_nyu"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
jobs_col = db["jobs"]
agent_jobs_col = db["agent_jobs"]

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

def get_all_new_jobs():
    return jobs_col.find_one({"status": "pending"})


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

def get_next_pending_job(job_type = "NORMAL") -> dict | None:
    """
    Atomically find ONE pending job, mark it as 'running', and return it.
    Returns the job document or None if nothing is pending.
    """
    if job_type == "NORMAL":
        job_doc = jobs_col.find_one_and_update(
            {"status": "pending"},
            {"$set": {"status": "running"}},
            sort=[("created_at", 1)],  # oldest first
            return_document=ReturnDocument.AFTER,
        )
        return job_doc
    else:
        print("fidingg agent jobs")
        job_doc = agent_jobs_col.find_one(
            {},
            sort=[("created_at", 1)],
        )
        print("found job")

        dt = job_doc["created_at"]

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        is_past = dt < now

        if is_past:
            #  lets not upadate it now

            # new_created_at = datetime.now(timezone.utc) + timedelta(days=2)
            #
            # # Update this job only
            # agent_jobs_col.update_one(
            #     {"_id": job_doc["_id"]},
            #     {"$set": {"created_at": new_created_at}}
            # )

            return job_doc

        return None


def update_job_result(job_id: str, description: str | None, video_url: str | None, subheadings: list[dict]) -> dict | None:
    """
    Returns updated document or None if not found.
    """
    oid = _to_object_id(job_id)
    result = jobs_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "status": "done",
                "description": description,
                "video_url": video_url,
                "subheadings": subheadings,
                "error": None,
            }
        },
    )
    if result.matched_count == 0:
        return None
    return jobs_col.find_one({"_id": oid})
