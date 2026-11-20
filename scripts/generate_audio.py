import asyncio
import json
from pathlib import Path
import edge_tts

VOICE = "en-US-ChristopherNeural"
IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")


def format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    ms = millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt_from_events(events: list[dict]) -> str:
    word_events = [e for e in events if e.get("type") == "WordBoundary"]
    if not word_events:
        return ""

    chunks = []
    chunk_size = 5
    for idx in range(0, len(word_events), chunk_size):
        group = word_events[idx : idx + chunk_size]
        start_sec = group[0]["offset"] / 10_000_000
        last = group[-1]
        end_sec = (last["offset"] + last["duration"]) / 10_000_000
        text = " ".join(w["text"].strip() for w in group if w.get("text", "").strip())
        if text:
            chunks.append((start_sec, end_sec, text))

    lines = []
    for i, (start_s, end_s, text) in enumerate(chunks, start=1):
        lines.append(str(i))
        lines.append(f"{format_srt_time(start_s)} --> {format_srt_time(end_s)}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


async def generate_for_idea(idea: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    idea_id = idea.get("id", 1)
    script_text = idea.get("script", "").strip()
    if not script_text:
        raise ValueError(f"Empty script for idea id={idea_id}")

    audio_path = OUTPUT_DIR / f"idea_{idea_id}.mp3"
    srt_path = OUTPUT_DIR / f"idea_{idea_id}.srt"

    communicate = edge_tts.Communicate(text=script_text, voice=VOICE)
    events = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                events.append(chunk)

    srt_content = build_srt_from_events(events)
    if srt_content.strip():
        srt_path.write_text(srt_content, encoding="utf-8")
        print(f"Saved audio & subtitles: {audio_path}, {srt_path}")
    else:
        print(f"Saved audio: {audio_path} (no word boundary events returned)")


async def main() -> None:
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        await generate_for_idea(idea)


if __name__ == "__main__":
    asyncio.run(main())
