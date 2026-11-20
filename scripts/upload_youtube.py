import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_video():
    client_id     = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()

    if not (client_id and client_secret and refresh_token):
        sys.exit("ERROR: Missing YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    youtube = build("youtube", "v3", credentials=creds)

    video_file = os.getenv("VIDEO_FILE", "output/final_video.mp4")
    title      = os.getenv("VIDEO_TITLE", "Psychology Short")
    desc       = os.getenv("VIDEO_DESC", "")
    privacy    = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")

    if not os.path.exists(video_file):
        sys.exit(f"ERROR: Video file not found: {video_file}")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": desc, "categoryId": "22"},
            "status":  {"privacyStatus": privacy},
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True),
    )

    print(f"Uploading: {video_file}")
    response = request.execute()
    print(f"Done! Video ID: {response['id']}")

if __name__ == "__main__":
    upload_video()
