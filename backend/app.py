# backend/app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from db import create_job, get_job, mark_job_done, serialize_job

load_dotenv()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)  #frontend (localhost:5500) will call the API

@app.route("/api/jobs", methods=["POST"])
def create_job_route():
    """
    Input:
      - text: prompt text (required)
      - document: file (optional)

    Returns:
      { "job_id": "<id>" }
    """
    prompt_text = request.form.get("text")
    if not prompt_text:
        return jsonify({"error": "Missing 'text' field"}), 400

    file = request.files.get("document")
    file_path = None
    file_name = None

    if file and file.filename:
        file_name = file.filename
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

    job_id = create_job(prompt_text=prompt_text,
                        file_path=file_path,
                        file_name=file_name)

    # TODO: enqueue background worker to process this job,
    # generate video, and later call mark_job_done(...)
    return jsonify({"job_id": job_id}), 200


@app.route("/api/jobs", methods=["GET"])
def get_job_status_route():
    """
    Query param:
      /api/jobs?job_id=<id>

    Returns:
      {
        "job_id": "...",
        "status": "pending" | "running" | "done" | "error",
        "text": "...",         # description
        "video_url": "https://www.youtube.com/watch?v=...",
        "error": "...",        # only if any
      }
    """
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400
    try:
        job_doc = get_job(job_id)
    except ValueError:
        return jsonify({"error": "Invalid job_id"}), 400
    if not job_doc:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(serialize_job(job_doc)), 200


# Optional: dummy route to simulate completion for testing
@app.route("/api/jobs/<job_id>/complete_dummy", methods=["POST"])
def complete_job_dummy_route(job_id):
    """
    For testing only (no real worker).
    POST /api/jobs/<job_id>/complete_dummy
    JSON:
      {
        "description": "explanation...",
        "video_url": "https://www.youtube.com/watch?v=..."
      }
    """
    payload = request.get_json(force=True, silent=True) or {}
    description = payload.get("description", "Sample generated description.")
    video_url = payload.get("video_url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    try:
        job_doc = mark_job_done(job_id, description, video_url)
    except ValueError:
        return jsonify({"error": "Invalid job_id"}), 400

    if not job_doc:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(serialize_job(job_doc)), 200


if __name__ == "__main__":
    # Backend runs on port 8000
    # Frontend HTML should use: const API_BASE = 'http://localhost:8000';
    app.run(host="0.0.0.0", port=8000, debug=True)
