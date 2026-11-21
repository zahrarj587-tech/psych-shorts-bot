import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).resolve().parent.parent
IDEAS_FILE = BASE_DIR / "data" / "ideas.json"
PUBLISHED_FILE = BASE_DIR / "data" / "published_ids.json"
OUTPUT_DIR = BASE_DIR / "output"

def get_authenticated_service():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("ERROR: Missing YouTube credentials in environment variables.")
        sys.exit(1)

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    return build("youtube", "v3", credentials=creds)

def upload_video():
    if not IDEAS_FILE.exists():
        print(f"Error: {IDEAS_FILE} not found.")
        sys.exit(1)

    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    if not ideas:
        print("No idea selected.")
        sys.exit(1)

    # قراءة الفكرة مباشرة من ideas.json (حل مشكلة الازدواجية)
    current_idea = ideas[0]
    idea_id = current_idea["id"]

    # فحص أمان: لو الفكرة دي اترفعت قبل كده نوقف
    if PUBLISHED_FILE.exists():
        published = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        if any(p["id"] == idea_id for p in published):
            print(f"Error: Idea {idea_id} is already in published_ids.json. Aborting to prevent duplicate.")
            sys.exit(1)
    else:
        published = []

    video_file = OUTPUT_DIR / f"idea_{idea_id}.mp4"
    meta_file = OUTPUT_DIR / f"idea_{idea_id}_meta.json"

    if not video_file.exists():
        print(f"Error: Video file not found: {video_file}")
        sys.exit(1)
    if not meta_file.exists():
        print(f"Error: Metadata file not found: {meta_file}")
        sys.exit(1)

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    title = meta.get("title", current_idea.get("title", "Psychology Short"))
    description = meta.get("description", "")
    tags = meta.get("tags", [])
    privacy = os.environ.get("YOUTUBE_PRIVACY_STATUS", "private")

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy},
    }

    print(f"Uploading idea {idea_id}: {title}")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_file), chunksize=-1, resumable=True)
    )
    response = request.execute()
    video_id = response["id"]
    print(f"Done! Video ID: {video_id}")

    published.append({
        "id": idea_id,
        "title": title,
        "video_id": video_id,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    PUBLISHED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED_FILE.write_text(json.dumps(published, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {PUBLISHED_FILE} ({len(published)} total uploads)")

if __name__ == "__main__":
    upload_video()
