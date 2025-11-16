import os
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Scopes required for uploading videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate():
    """Authenticate and return YouTube API service"""
    creds= None
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(script_dir, 'token.json')
    secrets_path = os.path.join(script_dir, 'client_secrets.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_path, SCOPES)
            # Use a fixed port instead of port=0
            creds = flow.run_local_server(port=8080)
    
    
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_path, SCOPES)  # Use absolute path
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, video_file, title, description, category_id='22', 
                 privacy_status='private', tags=None):
    """
    Upload a video to YouTube
    
    Args:
        youtube: Authenticated YouTube API service
        video_file: Path to video file
        title: Video title
        description: Video description
        category_id: YouTube category ID (22 = People & Blogs)
        privacy_status: 'public', 'private', or 'unlisted'
        tags: List of tags for the video
    
    Returns:
        Video ID of uploaded video
    """
    
    if tags is None:
        tags = []
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }
    
    # Create MediaFileUpload object
    media = MediaFileUpload(
        video_file,
        chunksize=-1,  # Upload in a single request
        resumable=True
    )
    
    try:
        # Call the API's videos.insert method
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")
        
        print(f"Upload complete! Video ID: {response['id']}")
        print(f"Video URL: https://www.youtube.com/watch?v={response['id']}")
        return response['id']
        
    except HttpError as e:
        print(f"An HTTP error occurred: {e.resp.status} - {e.content}")
        return None

def main():
    """Main function to demonstrate video upload"""
    
    # Authenticate
    youtube = authenticate()
    
    # Upload parameters
    video_file = 'testvideo.mp4'  # Change to your video file path
    title = 'My Awesome Video'
    description = 'This video was uploaded using the YouTube API'
    tags = ['python', 'youtube api', 'automation']
    
    # Upload the video
    video_id = upload_video(
        youtube=youtube,
        video_file=video_file,
        title=title,
        description=description,
        privacy_status='private',  # Start as private for safety
        tags=tags
    )
    
    if video_id:
        print(f"Successfully uploaded video with ID: {video_id}")
    else:
        print("Upload failed")

if __name__ == '__main__':
    main()