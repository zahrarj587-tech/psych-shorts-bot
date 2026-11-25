import asyncio
import json
import subprocess
from pathlib import Path
import edge_tts

# قائمة بأصوات Neural واقعية ومتنوعة
VOICES = [
    "en-US-ChristopherNeural", # رجالي أمريكي واثق
    "en-US-AriaNeural",        # نسائي أمريكي معبر
    "en-GB-RyanNeural",        # رجالي بريطاني راقي
    "en-US-GuyNeural",         # رجالي أمريكي (إخباري)
    "en-US-JennyNeural",       # نسائي أمريكي ودود
    "en-GB-SoniaNeural"        # نسائي بريطاني أنيق
]

IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")

def format_srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    ms = millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

def get_duration(mp3_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp3_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return max(1.0, float(res.stdout.strip()))

def build_timed_srt(text: str, duration: float) -> str:
    words = text.split()
    if not words:
        return ""
    chunk_size = 4
    chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
    total_words = len(words)
    current_t = 0.0
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        w_count = len(chunk.split())
        seg_dur = duration * (w_count / total_words)
        start_t = current_t
        end_t = duration if idx == len(chunks) else current_t + seg_dur
        current_t = end_t
        lines.append(str(idx))
        lines.append(f"{format_srt_time(start_t)} --> {format_srt_time(end_t)}")
        lines.append(chunk)
        lines.append("")
    return "\n".join(lines).strip() + "\n"

async def generate_for_idea(idea: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    idea_id = idea.get("id", 1)
    script_text = idea.get("script", "").strip()
    if not script_text:
        raise ValueError(f"Empty script for idea id={idea_id}")

    # اختيار الصوت بناءً على رقم الفكرة لضمان التنويع
    selected_voice = VOICES[idea_id % len(VOICES)]

    audio_path = OUTPUT_DIR / f"idea_{idea_id}.mp3"
    srt_path = OUTPUT_DIR / f"idea_{idea_id}.srt"

    raw_audio_path = OUTPUT_DIR / f"idea_{idea_id}_raw.mp3"
    communicate = edge_tts.Communicate(text=script_text, voice=selected_voice, rate="-4%")
    await communicate.save(str(raw_audio_path))

    # توحيد مستوى الصوت وتحسين الوضوح (يحل مشكلة الصوت "الرخيص")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_audio_path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=80",
            "-ar", "44100", "-b:a", "192k",
            str(audio_path),
        ],
        check=True,
    )
    raw_audio_path.unlink()

    duration = get_duration(audio_path)
    srt_content = build_timed_srt(script_text, duration)
    srt_path.write_text(srt_content, encoding="utf-8")
    print(f"OK -> {audio_path} ({duration:.1f}s) | Voice: {selected_voice} | {srt_path}")

async def main() -> None:
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        await generate_for_idea(idea)

if __name__ == "__main__":
    asyncio.run(main())
