import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")
ASSETS_DIR = OUTPUT_DIR / "assets"


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def download_pexels_clips(query: str, idea_id: int, count: int = 3) -> list[Path]:
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        return []

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://api.pexels.com/videos/search?query={quote(query)}&orientation=portrait&per_page={count}"
    req = Request(url, headers={"Authorization": api_key, "User-Agent": "Mozilla/5.0"})

    clips: list[Path] = []
    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for idx, video in enumerate(data.get("videos", [])[:count], start=1):
            files = video.get("video_files", [])
            # Prefer HD portrait-friendly mp4 files
            mp4_files = [
                f for f in files
                if f.get("file_type") == "video/mp4" and f.get("link")
            ]
            if not mp4_files:
                continue
            chosen = sorted(mp4_files, key=lambda x: x.get("width", 0), reverse=True)[0]
            clip_path = ASSETS_DIR / f"idea_{idea_id}_clip_{idx}.mp4"
            clip_req = Request(chosen["link"], headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(clip_req, timeout=30) as clip_resp:
                clip_path.write_bytes(clip_resp.read())
            clips.append(clip_path)
    except Exception as exc:
        print(f"Pexels fallback triggered: {exc}")
        return []

    return clips


def build_fallback_scenes_video(audio_path: Path, srt_path: Path, video_path: Path, duration: float) -> None:
    colors = ["0x0b132b", "0x1c2541", "0x16213e"]
    seg_dur = max(4.0, duration / len(colors))
    seg_files: list[Path] = []

    for i, hex_color in enumerate(colors):
        seg_path = OUTPUT_DIR / f"tmp_seg_{i}.mp4"
        frames = max(1, int(seg_dur * 30))
        vf = f"zoompan=z='min(zoom+0.0005,1.12)':d={frames}:s=1080x1920:fps=30"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={hex_color}:s=1920x3413:r=30",
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-t", f"{seg_dur:.2f}",
            str(seg_path),
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    concat_list = OUTPUT_DIR / "tmp_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in seg_files) + "\n",
        encoding="utf-8",
    )

    merged_bg = OUTPUT_DIR / "tmp_bg.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-t", f"{duration:.2f}",
            str(merged_bg),
        ],
        check=True,
    )

    vf_final = "scale=1080:1920"
    if srt_path.exists() and srt_path.stat().st_size > 0:
        safe_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
        vf_final = (
            f"scale=1080:1920,subtitles='{safe_srt}':force_style='FontName=Sans,"
            f"FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"BackColour=&H80000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=10,MarginV=80'"
        )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(merged_bg),
            "-i", str(audio_path),
            "-vf", vf_final,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(video_path),
        ],
        check=True,
    )

    for p in [*seg_files, concat_list, merged_bg]:
        if p.exists():
            p.unlink()


def build_from_clips(clips: list[Path], audio_path: Path, srt_path: Path, video_path: Path, duration: float) -> None:
    seg_dur = max(3.5, duration / len(clips))
    normalized_segs: list[Path] = []

    for idx, clip in enumerate(clips):
        seg_out = OUTPUT_DIR / f"tmp_clip_seg_{idx}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(clip),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-an",
            "-pix_fmt", "yuv420p",
            "-t", f"{seg_dur:.2f}",
            str(seg_out),
        ]
        subprocess.run(cmd, check=True)
        normalized_segs.append(seg_out)

    concat_list = OUTPUT_DIR / "tmp_clips_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in normalized_segs) + "\n",
        encoding="utf-8",
    )

    merged_bg = OUTPUT_DIR / "tmp_clips_bg.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-t", f"{duration:.2f}",
            str(merged_bg),
        ],
        check=True,
    )

    vf_final = "scale=1080:1920,eq=brightness=-0.08"
    if srt_path.exists() and srt_path.stat().st_size > 0:
        safe_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
        vf_final = (
            f"scale=1080:1920,eq=brightness=-0.08,subtitles='{safe_srt}':force_style='FontName=Sans,"
            f"FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"BackColour=&H80000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=10,MarginV=80'"
        )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(merged_bg),
            "-i", str(audio_path),
            "-vf", vf_final,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(video_path),
        ],
        check=True,
    )

    for p in [*normalized_segs, concat_list, merged_bg]:
        if p.exists():
            p.unlink()


def build_short_video(idea: dict) -> None:
    idea_id = idea.get("id", 1)
    query = idea.get("visual_query", "mind thinking shadow moody")
    audio_path = OUTPUT_DIR / f"idea_{idea_id}.mp3"
    srt_path = OUTPUT_DIR / f"idea_{idea_id}.srt"
    video_path = OUTPUT_DIR / f"idea_{idea_id}.mp4"

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    duration = get_audio_duration(audio_path)
    clips = download_pexels_clips(query=query, idea_id=idea_id, count=3)

    if len(clips) >= 2:
        build_from_clips(clips, audio_path, srt_path, video_path, duration)
    else:
        build_fallback_scenes_video(audio_path, srt_path, video_path, duration)

    print(f"Saved enhanced video: {video_path}")


def main() -> None:
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        build_short_video(idea)


if __name__ == "__main__":
    main()
