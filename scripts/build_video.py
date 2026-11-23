import json
import math
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")
ASSETS_DIR = OUTPUT_DIR / "assets"

KEYWORDS_HIGHLIGHT = {
    "pressure", "trap", "brain", "fear", "failure", "calm", "control",
    "focus", "silence", "decisions", "stress", "energy", "emotion", "habit",
    "smart", "protect", "pause", "mind", "overthinking", "attention"
}

BG_COLOR = (250, 250, 252)
INK = (20, 24, 38)
ACCENT = (37, 99, 235)
CENTER = (540, 720)
RADIUS = 240
STROKE = 16

KEYWORD_MAP = [
    ("brain",   {"brain", "mind", "mental", "mindset", "neuro"}),
    ("idea",    {"idea", "insight", "realize", "understand", "habit", "loop", "routine"}),
    ("clock",   {"time", "delay", "wait", "pause", "seconds", "minutes", "day", "evening"}),
    ("lock",    {"control", "trap", "stuck", "locked", "confirm", "bias"}),
    ("arrow_up",{"confidence", "rise", "grow", "smart", "win", "success", "best"}),
    ("arrow_down", {"loss", "lose", "losing", "drop", "fail", "failure", "worse", "wrong"}),
    ("battery", {"energy", "willpower", "drain", "exhaust", "tired", "rest"}),
    ("warning", {"fear", "danger", "threat", "panic", "stress", "afraid"}),
    ("scale",   {"decision", "decisions", "choice", "choices", "option", "options", "choose"}),
]


def select_icon_category(text: str) -> str:
    words = set(re.sub(r"[^a-zA-Z\s]", "", text).lower().split())
    for category, keys in KEYWORD_MAP:
        if words & keys:
            return category
    return "spark"


def new_canvas() -> Image.Image:
    return Image.new("RGB", (1080, 1920), BG_COLOR)


def draw_brain(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.ellipse([cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS], outline=INK, width=STROKE)
    for i in range(3):
        y = cy - 100 + i * 100
        points = []
        for x in range(cx - 160, cx + 160, 8):
            wave = 22 * math.sin((x - cx) / 18.0)
            points.append((x, y + wave))
        draw.line(points, fill=ACCENT, width=10)


def draw_idea(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    r = RADIUS - 40
    draw.ellipse([cx - r, cy - r - 40, cx + r, cy + r - 40], outline=INK, width=STROKE)
    draw.rectangle([cx - 55, cy + r - 90, cx + 55, cy + r - 20], outline=INK, width=STROKE)
    for i in range(3):
        y = cy + r - 5 + i * 28
        draw.line([(cx - 55, y), (cx + 55, y)], fill=INK, width=8)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + (r + 30) * math.cos(rad)
        y1 = cy - 40 + (r + 30) * math.sin(rad)
        x2 = cx + (r + 70) * math.cos(rad)
        y2 = cy - 40 + (r + 70) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=ACCENT, width=10)


def draw_clock(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.ellipse([cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS], outline=INK, width=STROKE)
    draw.line([(cx, cy), (cx, cy - RADIUS + 60)], fill=INK, width=14)
    draw.line([(cx, cy), (cx + RADIUS - 100, cy + 40)], fill=ACCENT, width=14)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = cx + (RADIUS - 20) * math.cos(rad)
        y1 = cy + (RADIUS - 20) * math.sin(rad)
        x2 = cx + (RADIUS - 45) * math.cos(rad)
        y2 = cy + (RADIUS - 45) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=INK, width=8)


def draw_lock(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    w, h = 300, 220
    draw.rounded_rectangle([cx - w // 2, cy - h // 2 + 60, cx + w // 2, cy + h // 2 + 60],
                            radius=24, outline=INK, width=STROKE)
    draw.arc([cx - 110, cy - 190, cx + 110, cy + 30], start=180, end=360, fill=INK, width=STROKE)
    draw.ellipse([cx - 20, cy + 60, cx + 20, cy + 100], fill=ACCENT)


def draw_arrow_up(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.polygon([(cx, cy - RADIUS), (cx - 150, cy - RADIUS + 180), (cx - 60, cy - RADIUS + 180),
                  (cx - 60, cy + RADIUS), (cx + 60, cy + RADIUS), (cx + 60, cy - RADIUS + 180),
                  (cx + 150, cy - RADIUS + 180)], outline=ACCENT, width=STROKE)


def draw_arrow_down(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.polygon([(cx, cy + RADIUS), (cx - 150, cy + RADIUS - 180), (cx - 60, cy + RADIUS - 180),
                  (cx - 60, cy - RADIUS), (cx + 60, cy - RADIUS), (cx + 60, cy + RADIUS - 180),
                  (cx + 150, cy + RADIUS - 180)], outline=INK, width=STROKE)


def draw_battery(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    w, h = 260, 420
    draw.rounded_rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2],
                            radius=20, outline=INK, width=STROKE)
    draw.rectangle([cx - 45, cy - h // 2 - 40, cx + 45, cy - h // 2], outline=INK, width=STROKE)
    draw.rectangle([cx - w // 2 + 20, cy + h // 2 - 120, cx + w // 2 - 20, cy + h // 2 - 20],
                   fill=ACCENT)


def draw_warning(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    r = RADIUS
    draw.polygon([(cx, cy - r), (cx - r, cy + r - 40), (cx + r, cy + r - 40)],
                 outline=INK, width=STROKE)
    draw.line([(cx, cy - 60), (cx, cy + 60)], fill=ACCENT, width=18)
    draw.ellipse([cx - 12, cy + 100, cx + 12, cy + 124], fill=ACCENT)


def draw_scale(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.line([(cx, cy - RADIUS), (cx, cy + 60)], fill=INK, width=STROKE)
    draw.line([(cx - 220, cy - 120), (cx + 220, cy - 120)], fill=INK, width=14)
    for dx in (-220, 220):
        draw.arc([cx + dx - 70, cy - 120, cx + dx + 70, cy], start=0, end=180, fill=ACCENT, width=12)
    draw.line([(cx - 100, cy + 60), (cx + 100, cy + 60)], fill=INK, width=STROKE)


def draw_spark(draw: ImageDraw.ImageDraw) -> None:
    cx, cy = CENTER
    draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=ACCENT)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = cx + 60 * math.cos(rad)
        y1 = cy + 60 * math.sin(rad)
        x2 = cx + (RADIUS - 20) * math.cos(rad)
        y2 = cy + (RADIUS - 20) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=INK, width=10)


ICON_DRAWERS = {
    "brain": draw_brain, "idea": draw_idea, "clock": draw_clock, "lock": draw_lock,
    "arrow_up": draw_arrow_up, "arrow_down": draw_arrow_down, "battery": draw_battery,
    "warning": draw_warning, "scale": draw_scale, "spark": draw_spark,
}


def get_or_render_icon(category: str) -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DIR / f"icon_{category}.png"
    if path.exists():
        return path
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    ICON_DRAWERS.get(category, draw_spark)(draw)
    img.save(path, "PNG")
    return path


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


def build_icon_timeline(cues: list[tuple[float, float, str]], total_duration: float) -> list[tuple[float, str]]:
    """Returns list of (segment_duration, icon_category), covering 0..total_duration with no gaps."""
    timeline: list[tuple[float, str]] = []
    cursor = 0.0
    last_category = "spark"
    for start, end, text in cues:
        if start > cursor + 0.05:
            timeline.append((start - cursor, last_category))
            cursor = start
        category = select_icon_category(text)
        seg_dur = max(0.12, end - cursor)
        timeline.append((seg_dur, category))
        cursor = end
        last_category = category
    if cursor < total_duration - 0.05:
        timeline.append((total_duration - cursor, last_category))
    if not timeline:
        timeline = [(total_duration, "spark")]
    return timeline


def build_base_video(idea_id: int, timeline: list[tuple[float, str]], total_duration: float) -> Path:
    base_video = OUTPUT_DIR / f"tmp_base_{idea_id}.mp4"
    seg_files: list[Path] = []

    for i, (seg_dur, category) in enumerate(timeline):
        icon_path = get_or_render_icon(category)
        seg_path = OUTPUT_DIR / f"tmp_iconseg_{idea_id}_{i}.mp4"
        frames = max(1, int(seg_dur * 30))
        if i % 2 == 0:
            vf = f"zoompan=z='min(zoom+0.0010,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30"
        else:
            vf = f"zoompan=z='1.06-0.0008*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30"
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(icon_path),
            "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-t", f"{seg_dur:.3f}", str(seg_path),
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    concat_list = OUTPUT_DIR / f"tmp_iconconcat_{idea_id}.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in seg_files) + "\n", encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", "-t", f"{total_duration:.2f}", str(base_video)],
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
        "Style: Caption,DejaVu Sans,60,&H00141826&,&H000000FF&,&H00FAFAFA&,"
        "&H00FAFAFA&,-1,0,0,0,100,100,0,0,1,0,2,2,60,60,120,1\n\n"
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
                    parts.append(r"{\c&H0026F86D&}" + safe_w + r"{\c&H00141826&}")
                else:
                    parts.append(safe_w)
            line_strs.append(" ".join(parts))

        text_block = r"\N".join(line_strs)
        t0 = seconds_to_ass_time(start_sec)
        t1 = seconds_to_ass_time(end_sec)
        lines.append(
            f"Dialogue: 0,{t0},{t1},Caption,,0,0,0,,{{\\an2\\pos(540,1720)}}{text_block}\n"
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
    cues = parse_srt(srt_path)
    timeline = build_icon_timeline(cues, duration)
    base_video = build_base_video(idea_id, timeline, duration)
    build_ass_captions(srt_path, ass_path)

    brand_draw = (
        "drawtext=text='BEHAVIOR LAB':fontcolor=0x1e293b:fontsize=26:"
        "x=(w-text_w)/2:y=70:borderw=0"
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
