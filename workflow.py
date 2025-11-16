# backend/worker.py

import time
from typing import Tuple, List, Dict

from backend.db import get_next_pending_job, update_job_result, serialize_job
from main import main

from backend.generate_subheading import generate_prompt_subheading
from video_uploader import upload_video, YOUTUBE_INSTANCE

# from backend.app import YOUTUBE_INSTANCE
YOUTUBE_INSTANCE = None

def generate_video_from_job(prompt_text: str, file_path: str | None) -> Tuple[str, str, List[Dict]]:
    """
    This is a placeholder; replace with actual integration
    with your prompt->video pipeline (Sora API, custom model, etc.).
    """

    # -----------------------------
    # TODO: replace with real generation
    # -----------------------------
    # Dummy logic for now:
    description = f"Auto-generated video based on prompt: {prompt_text[:100]}..."
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    subheadings = [
        {"heading": "Introduction", "text": "This section introduces the main topic in simple terms."},
        {"heading": "Key Concepts", "text": "This section covers the core ideas in the prompt."},
        {"heading": "Summary", "text": "This section wraps up the explanation and key takeaways."},
    ]

    return description, video_url, subheadings

def process_one_job():
    """
    - Fetch one pending job from MongoDB.
    - Generate video + metadata.
    - Update job document with results.
    """
    job_doc = get_next_pending_job()
    if not job_doc:
        print("No pending jobs found.")
        return False

    job_id = str(job_doc["_id"])
    prompt_text = job_doc.get("prompt_text")
    file_path = job_doc.get("file_path")  # may be None if no file uploaded

    print(f"Processing job_id={job_id}")
    print(f"Prompt text: {prompt_text[:80]}...")
    print(f"File path  : {file_path}")

    # TODO Call video generation logic here
    # description, video_url, subheadings = generate_video_from_job(prompt_text, file_path)
    description, video_url, subheadings = main(prompt_text, file_path)

    # Update the document in Mongo
    updated_doc = update_job_result(job_id, description, video_url, subheadings)

    print("Updated job:")
    print(serialize_job(updated_doc))
    return True


def process_one_agent_job():
    job = get_next_pending_job("AGENT")
    print("agent job", job)

    if job is not None:
        base_prompt_text = job.get("prompt_text")
        print("base prmopt", base_prompt_text)
        prompt_text = generate_prompt_subheading(base_prompt_text)
        print("got new prompt text", prompt_text)
        description, video_url, subheadings = main(prompt_text, None)

        video_file = video_url  # Change to your video file path
        title = prompt_text
        description = 'This video was uploaded using the YouTube API'
        tags = ['python', 'youtube api', 'automation']

        ## upload sequence
        print("upalod to youtube", video_url)
        if YOUTUBE_INSTANCE is not None:
            video_id = upload_video(youtube=YOUTUBE_INSTANCE,
                                    video_file=video_file,
                                    title=title,
                                    description=description,
                                    tags=tags,
                                    privacy_status='public')

        print("Upload successfull", video_id)



def run_worker_loop(poll_interval: int = 5):
    """
    Every poll_interval seconds:
      - Fetch a job
      - If found, process it immediately
      - If none, just sleep and try again
    """
    print("Worker started. Polling for new jobs...")
    while True:
        success = process_one_job()
        process_one_agent_job()
        if not success:
            # No job; sleep and poll again
            time.sleep(poll_interval)

if __name__ == "__main__":
    # Option A: process a single job then exit
    # process_one_job()

    # Option B: run forever, polling for new jobs
    run_worker_loop(poll_interval=5)
