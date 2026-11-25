import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageEnhance

IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")
ASSETS_DIR = OUTPUT_DIR / "assets"
CAPTIONS_DIR = OUTPUT_DIR / "captions"

KEYWORDS_HIGHLIGHT = {
    "pressure", "trap", "brain", "fear", "failure", "calm", "control",
    "focus", "silence", "decisions", "stress", "energy", "emotion", "habit",
    "smart", "protect", "pause", "mind", "overthinking", "attention"
}

NATURE_TAGS_BY_ID = {
    1: ["dark,storm,clouds", "night,mountain,fog", "dark,ocean,waves", "misty,forest,night"],
    2: ["lonely,road,night", "rain,window,night", "dark,city,street", "foggy,woods,path"],
    3: ["calm,lake,twilight", "dark,sky,stars", "minimal,architecture,shadow", "quiet,forest,mist"],
    4: ["night,sky,clouds", "dark,clock,shadow", "ocean,horizon,dusk", "rain,forest,dark"],
    5: ["calm,water,night", "still,lake,mountains", "dark,clouds,moonlight", "zen,stones,water"],
}


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def parse_srt_time(time_str: str) -> float:
    h, m, rest = time_str.strip().split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(srt_path: Path) -> list[tuple[float, float, str]]:
    if not srt_path.exists():
        return []
    content = srt_path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    blocks = re.split(r"\n\s*\n", content)
    items: list[tuple[float, float, str]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            start_s, end_s = [p.strip() for p in lines[1].split("-->")]
            items.append((parse_srt_time(start_s), parse_srt_time(end_s), " ".join(lines[2:])))
    return items


def apply_dark_cinematic_grade(raw_img_path: Path, out_img_path: Path) -> None:
    img = Image.open(raw_img_path).convert("RGB")
    target_w, target_h = 1080, 1920
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    img = ImageEnhance.Color(img).enhance(0.65)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Brightness(img).enhance(0.38)
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", (target_w, target_h), (6, 10, 22, 95))
    graded = Image.alpha_composite(base, overlay)
    vignette = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for y in range(target_h):
        dist_center = abs(y - (target_h / 2)) / (target_h / 2)
        alpha = int(110 * (dist_center ** 1.6))
        vdraw.line([(0, y), (target_w, y)], fill=(3, 5, 12, alpha))
    final_img = Image.alpha_composite(graded, vignette).convert("RGB")
    final_img.save(out_img_path, "JPEG", quality=92)


def download_nature_images(idea: dict, count: int = 4) -> list[Path]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    idea_id = idea.get("id", 1)
    tags_list = NATURE_TAGS_BY_ID.get(
        idea_id,
        ["dark,nature,fog", "night,mountains,stars", "calm,ocean,dusk", "misty,forest,dark"],
    )
    processed_images: list[Path] = []
    for idx in range(1, count + 1):
        tags = tags_list[(idx - 1) % len(tags_list)]
        raw_path = ASSETS_DIR / f"raw_idea_{idea_id}_{idx}.jpg"
        graded_path = ASSETS_DIR / f"graded_idea_{idea_id}_{idx}.jpg"
        if graded_path.exists() and graded_path.stat().st_size > 15_000:
            processed_images.append(graded_path)
            continue
        urls = [
            f"https://loremflickr.com/1080/1920/{quote(tags)}?lock={idea_id * 10 + idx}",
            f"https://picsum.photos/seed/behaviorlab{idea_id}{idx}/1080/1920",
        ]
        downloaded = False
        for url in urls:
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=20) as resp:
                    data = resp.read()
                if len(data) > 15_000:
                    raw_path.write_bytes(data)
                    apply_dark_cinematic_grade(raw_path, graded_path)
                    if raw_path.exists():
                        raw_path.unlink()
                    processed_images.append(graded_path)
                    downloaded = True
                    print(f"Downloaded & darkened nature scene {idx}/{count} ({tags})")
                    break
            except Exception as exc:
                print(f"Image source retry ({url}): {exc}")
        if not downloaded:
            print(f"Warning: could not fetch scene {idx} from network.")
    return processed_images


def build_base_video(idea: dict, duration: float) -> Path:
    idea_id = idea.get("id", 1)
    base_video = OUTPUT_DIR / f"tmp_base_{idea_id}.mp4"
    nature_imgs = download_nature_images(idea, count=4)
    if not nature_imgs:
        fallback = ASSETS_DIR / f"fallback_dark_{idea_id}.jpg"
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1080, 1920), (8, 12, 24)).save(fallback, "JPEG")
        nature_imgs = [fallback]

    seg_dur = max(3.0, duration / len(nature_imgs))
    seg_files: list[Path] = []
    for i, img_path in enumerate(nature_imgs):
        seg_path = OUTPUT_DIR / f"tmp_natseg_{idea_id}_{i}.mp4"
        frames = max(1, int(seg_dur * 30))
        if i % 2 == 0:
            vf = f"scale=1300:-1,zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30"
        else:
            vf = f"scale=1300:-1,zoompan=z='1.12-0.0005*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30"
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
            "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-t", f"{seg_dur:.2f}", str(seg_path),
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    concat_list = OUTPUT_DIR / f"tmp_natconcat_{idea_id}.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in seg_files) + "\n", encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", "-t", f"{duration:.2f}", str(base_video)],
        check=True,
    )
    for p in [*seg_files, concat_list]:
        if p.exists():
            p.unlink()
    return base_video


def ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "").replace("}", "")


def seconds_to_ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass_captions(srt_path: Path, ass_path: Path) -> None:
    cues = parse_srt(srt_path)
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Caption,DejaVu Sans,66,&H00F8FAFC&,&H000000FF&,&H00000000&,"
        "&H00000000&,-1,0,0,0,100,100,0,0,1,4,2,5,60,60,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = [header]
    for start_sec, end_sec, text in cues:
        words = text.split()
        grouped: list[list[str]] = []
        current: list[str] = []
        for w in words:
            current.append(w)
            if len(current) == 2:
                grouped.append(current)
                current = []
        if current:
            grouped.append(current)
        if len(grouped) > 2 and len(grouped[-1]) == 1:
            grouped[-2].append(grouped[-1][0])
            grouped.pop()

        line_strs = []
        for line_words in grouped:
            parts = []
            for w in line_words:
                clean = re.sub(r"[^a-zA-Z]", "", w).lower()
                safe_w = ass_escape(w)
                if clean in KEYWORDS_HIGHLIGHT:
                    parts.append(r"{\c&H00F8BD38&}" + safe_w + r"{\c&H00F8FAFC&}")
                else:
                    parts.append(safe_w)
            line_strs.append(" ".join(parts))

        text_block = r"\N".join(line_strs)
        t0 = seconds_to_ass_time(start_sec)
        t1 = seconds_to_ass_time(end_sec)
        lines.append(
            f"Dialogue: 0,{t0},{t1},Caption,,0,0,0,,{{\\an5\\pos(540,950)}}{text_block}\n"
        )

    ass_path.write_text("".join(lines), encoding="utf-8")


def build_short_video(idea: dict) -> None:
    idea_id = idea.get("id", 1)
    audio_path = OUTPUT_DIR / f"idea_{idea_id}.mp3"
    srt_path = OUTPUT_DIR / f"idea_{idea_id}.srt"
    video_path = OUTPUT_DIR / f"idea_{idea_id}.mp4"
    ass_path = OUTPUT_DIR / f"idea_{idea_id}.ass"

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    duration = get_audio_duration(audio_path)
    base_video = build_base_video(idea, duration)
    build_ass_captions(srt_path, ass_path)

    brand_draw = (
        "drawtext=text='BEHAVIOR LAB':fontcolor=0x94A3B8:fontsize=26:"
        "x=(w-text_w)/2:y=70:borderw=2:bordercolor=black@0.6"
    )
    ass_escaped_path = str(ass_path.resolve()).replace("\\", "/").replace(":", r"\:")
    vf = f"{brand_draw},ass='{ass_escaped_path}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(base_video),
        "-i", str(audio_path),
        "-vf", vf,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.2f}",
        str(video_path),
    ]
    subprocess.run(cmd, check=True)

    for p in [base_video, ass_path]:
        if p.exists():
            p.unlink()
    print(f"Saved video: {video_path}")


def main() -> None:
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        build_short_video(idea)


if __name__ == "__main__":
    main()
