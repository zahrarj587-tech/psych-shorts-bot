import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")

def extract_code(raw_input: str) -> str:
    val = raw_input.strip()
    if "code=" in val:
        parsed = urlparse(val)
        qs = parse_qs(parsed.query)
        if "code" in qs and qs["code"]:
            return qs["code"][0].strip()
    return val


def get_credentials() -> Credentials:
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()

    if not (client_id and client_secret and refresh_token):
    raise SystemExit(
        "ERROR: Missing env vars. Set YOUTUBE_CLIENT_ID, "
        "YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN in GitHub Secrets."
    )
 
    
 

    if refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        SCOPES,
        redirect_uri="http://localhost",
    )

    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    print("\n========================================================")
    print("Open this link in your mobile browser and approve:")
    print(auth_url)
    print("========================================================\n")
    raw = input("Paste the full redirected URL (or code) and press Enter: ").strip()
    code = extract_code(raw)
    flow.fetch_token(code=code)
    creds = flow.credentials

    print("\n================ REFRESH TOKEN (SAVE THIS) ================")
    print("===========================================================\n")
    return creds


def upload_idea_video(youtube, idea: dict, privacy_status: str = "private") -> str:
    idea_id = idea.get("id", 1)
    video_path = OUTPUT_DIR / f"idea_{idea_id}.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"Video missing: {video_path}")

    raw_title = idea.get("title", f"Psychology Short #{idea_id}").strip()
    title = (raw_title if "#shorts" in raw_title.lower() else f"{raw_title} #Shorts")[:100]

    hook = idea.get("hook", "").strip()
    description = (
        f"{hook}\n\n"
        "Bite-sized psychology and human behavior insights from Behavior Lab.\n"
        "#psychology #humanbehavior #mindset #shorts"
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["psychology", "human behavior", "mindset", "shorts", "behavior lab"],
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    vid_id = response.get("id", "")
    print(f"Uploaded idea_{idea_id}.mp4 -> https://youtube.com/shorts/{vid_id} ({privacy_status})")
    return vid_id


def main() -> None:
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    target_id_env = os.getenv("UPLOAD_IDEA_ID", "1").strip()
    privacy_status = os.getenv("YOUTUBE_PRIVACY_STATUS", "private").strip() or "private"

    if target_id_env:
        target_id = int(target_id_env)
        ideas = [item for item in ideas if int(item.get("id", -1)) == target_id]

    for idea in ideas:
        upload_idea_video(youtube, idea, privacy_status=privacy_status)


if __name__ == "__main__":
    main()
