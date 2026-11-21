import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

IDEAS_FILE = Path("data/ideas.json")
PUBLISHED_FILE = Path("data/published_ids.json")
OUTPUT_DIR = Path("output")


def load_published() -> list:
    if PUBLISHED_FILE.exists():
        return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
    return []


def pick_next_idea(ideas: list, published: list) -> dict:
    idx = len(published) % len(ideas)
    return ideas[idx]


def upload_video():
    client_id     = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
    privacy       = os.getenv("YOUTUBE_PRIVACY_STATUS", "private").strip()

    if not (client_id and client_secret and refresh_token):
        sys.exit("ERROR: Missing YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN")

    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    published = load_published()
    idea = pick_next_idea(ideas, published)
    idea_id = idea["id"]

    video_file = OUTPUT_DIR / f"idea_{idea_id}.mp4"
    meta_file  = OUTPUT_DIR / f"idea_{idea_id}_meta.json"

    if not video_file.exists():
        sys.exit(f"ERROR: Video file not found: {video_file}")

    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        title = meta.get("title", idea.get("title", "Psychology Short"))
        description = meta.get("description", "")
        tags = meta.get("tags", [])
    else:
        title = idea.get("title", "Psychology Short")
        description = idea.get("hook", "")
        tags = []

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",
            },
            "status": {"privacyStatus": privacy},
        },
        media_body=MediaFileUpload(str(video_file), chunksize=-1, resumable=True),
    )

    print(f"Uploading idea {idea_id}: {title}")
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
