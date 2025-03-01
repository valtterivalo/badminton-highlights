import os
import json
import time
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def get_authenticated_service():
    """Get an authenticated YouTube API service instance."""
    # Define OAuth 2.0 scopes
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload", 
              "https://www.googleapis.com/auth/youtube"]
    
    # Path to credential files
    creds_dir = os.path.join(os.path.dirname(__file__), "..", "credentials")
    os.makedirs(creds_dir, exist_ok=True)
    
    token_path = os.path.join(creds_dir, "token.pickle")
    secrets_path = os.path.join(creds_dir, "client_secrets.json")
    
    credentials = None
    
    # Check if token file exists
    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as token:
                credentials = pickle.load(token)
            print("Loaded credentials from saved token file")
        except Exception as e:
            print(f"Error loading token: {e}")
    
    # If credentials don't exist or are invalid, get new ones
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                print("Refreshed expired credentials")
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                credentials = None
        
        if not credentials:
            if not os.path.exists(secrets_path):
                raise FileNotFoundError(
                    f"Client secrets file not found at {secrets_path}. "
                    "Please download OAuth 2.0 client ID from Google Cloud Console "
                    "and save it as 'client_secrets.json' in the credentials directory."
                )
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                credentials = flow.run_local_server(port=0)
                print("Generated new credentials through OAuth flow")
            except Exception as e:
                raise Exception(f"Failed to authenticate: {e}")
            
            # Save the credentials for future use
            with open(token_path, "wb") as token:
                pickle.dump(credentials, token)
            print(f"Saved credentials to {token_path}")
    
    return build("youtube", "v3", credentials=credentials)

def upload_to_youtube(video_path, title="Badminton Highlights", description="Auto-generated rally highlights", 
                      tags=None, category_id="17", privacy_status="private", notify_subscribers=False,
                      language="en", retry_count=3):
    """
    Upload a video to YouTube.
    
    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: List of tags (default: ["badminton", "highlights"])
        category_id: YouTube category ID (default: 17 for Sports)
        privacy_status: Video privacy status (private, unlisted, public)
        notify_subscribers: Whether to notify subscribers
        language: Video language
        retry_count: Number of retry attempts
        
    Returns:
        YouTube video ID or None if upload failed
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")
    
    if tags is None:
        tags = ["badminton", "highlights"]
    
    # Get video file size for progress reporting
    file_size = os.path.getsize(video_path)
    print(f"Video file size: {file_size / (1024 * 1024):.2f} MB")
    
    # Attempt to get an authenticated service
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    
    # Set up the API request
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": language
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
            "notifySubscribers": notify_subscribers
        }
    }
    
    media = MediaFileUpload(video_path, 
                           chunksize=1024*1024, 
                           resumable=True, 
                           mimetype="video/mp4")
    
    # Execute the upload with retries
    for attempt in range(retry_count):
        try:
            request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Implement chunked upload with progress reporting
            print(f"Starting upload (attempt {attempt+1}/{retry_count})...")
            response = None
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"Upload progress: {progress}%")
            
            print("Upload complete!")
            
            # Return the uploaded video ID
            video_id = response["id"]
            
            # Add the video to a playlist if a playlist ID is provided
            # playlist_id = os.environ.get("YOUTUBE_PLAYLIST_ID")
            # if playlist_id:
            #     add_to_playlist(youtube, video_id, playlist_id)
            
            return video_id
            
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                # Server error, retry
                if attempt < retry_count - 1:
                    sleep_time = (2 ** attempt) + 5  # Exponential backoff
                    print(f"Server error, retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    print(f"Upload failed after {retry_count} attempts: {e}")
                    return None
            else:
                # Client error, don't retry
                print(f"Client error during upload: {e}")
                return None
                
        except Exception as e:
            print(f"Error during upload: {e}")
            if attempt < retry_count - 1:
                print(f"Retrying in 10 seconds...")
                time.sleep(10)
            else:
                print(f"Upload failed after {retry_count} attempts")
                return None
    
    return None

def add_to_playlist(youtube, video_id, playlist_id):
    """Add a video to a YouTube playlist."""
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        print(f"Added video {video_id} to playlist {playlist_id}")
        return True
    except Exception as e:
        print(f"Error adding video to playlist: {e}")
        return False

def update_video_thumbnail(youtube, video_id, thumbnail_path):
    """Upload and set a custom thumbnail for a video."""
    if not os.path.exists(thumbnail_path):
        print(f"Thumbnail file not found at {thumbnail_path}")
        return False
        
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print(f"Custom thumbnail set for video {video_id}")
        return True
    except Exception as e:
        print(f"Error setting thumbnail: {e}")
        return False