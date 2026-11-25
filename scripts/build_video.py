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
INK = (18, 22, 30)
ACCENT = (37, 99, 235)
W, H = 1080, 1920
HEAD_CX, HEAD_CY, HEAD_R = 540, 760, 130
STROKE = 14

POSE_MAP = [
    ("think",   {"think", "thinking", "brain", "mind", "mental", "mindset", "idea", "realize", "understand"}),
    ("run",     {"fast", "speed", "rush", "run", "quick", "immediate", "instant", "react", "reaction"}),
    ("shock",   {"fear", "danger", "threat", "panic", "stress", "afraid", "shock", "sudden", "fail", "failure"}),
    ("power",   {"control", "confidence", "strong", "smart", "win", "success", "best", "power", "protect"}),
    ("focus",   {"focus", "attention", "decision", "decisions", "choice", "choices", "option", "options"}),
    ("win",     {"win", "success", "achieve", "best", "growth", "grow", "rise", "calm", "habit"}),
]


def select_pose(text: str) -> str:
    words = set(re.sub(r"[^a-zA-Z\s]", "", text).lower().split())
    for pose, keys in POSE_MAP:
        if words & keys:
            return pose
    return "idle"


def new_canvas() -> Image.Image:
    return Image.new("RGB", (W, H), BG_COLOR)


def draw_head(draw: ImageDraw.ImageDraw, cx: int, cy: int, tilt: int = 0) -> None:
    draw.ellipse([cx - HEAD_R, cy - HEAD_R, cx + HEAD_R, cy + HEAD_R], outline=INK, width=STROKE)
    eye_y = cy - 15
    draw.ellipse([cx - 55, eye_y - 12, cx - 35, eye_y + 12], fill=INK)
    draw.ellipse([cx + 20, eye_y - 12 + tilt, cx + 40, eye_y + 12 + tilt], fill=INK)


def draw_body(draw: ImageDraw.ImageDraw, cx: int, hip_y: int, lean: int = 0) -> None:
    neck_y = HEAD_CY + HEAD_R
    draw.line([(cx, neck_y), (cx + lean, hip_y)], fill=INK, width=STROKE)


def pose_idle(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, HEAD_CX, hip_y)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 60), (HEAD_CX - 140, HEAD_CY + HEAD_R + 160)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 60), (HEAD_CX + 140, HEAD_CY + HEAD_R + 160)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX - 90, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX + 90, hip_y + 260)], fill=INK, width=STROKE)


def pose_think(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY, tilt=-6)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, HEAD_CX, hip_y, lean=20)
    draw.line([(HEAD_CX + 20, HEAD_CY + HEAD_R + 40), (HEAD_CX + 100, HEAD_CY - 20)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX + 100, HEAD_CY - 20), (HEAD_CX + 60, HEAD_CY - 40)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 60), (HEAD_CX - 130, HEAD_CY + HEAD_R + 180)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX + 20, hip_y), (HEAD_CX - 80, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX + 20, hip_y), (HEAD_CX + 100, hip_y + 260)], fill=INK, width=STROKE)
    for i, r in enumerate([18, 26, 34]):
        bx = HEAD_CX + 150 + i * 55
        by = HEAD_CY - 160 - i * 20
        draw.ellipse([bx - r, by - r, bx + r, by + r], outline=ACCENT, width=8)


def pose_run(draw: ImageDraw.ImageDraw) -> None:
    cx = HEAD_CX + 40
    draw_head(draw, cx, HEAD_CY)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, cx, hip_y, lean=-20)
    draw.line([(cx, HEAD_CY + HEAD_R + 50), (cx + 150, HEAD_CY + HEAD_R - 10)], fill=INK, width=STROKE)
    draw.line([(cx, HEAD_CY + HEAD_R + 60), (cx - 160, HEAD_CY + HEAD_R + 140)], fill=INK, width=STROKE)
    draw.line([(cx - 20, hip_y), (cx + 120, hip_y + 150)], fill=INK, width=STROKE)
    draw.line([(cx + 120, hip_y + 150), (cx + 60, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(cx - 20, hip_y), (cx - 140, hip_y + 120)], fill=INK, width=STROKE)
    draw.line([(cx - 140, hip_y + 120), (cx - 180, hip_y + 250)], fill=INK, width=STROKE)
    for i in range(3):
        y = HEAD_CY - 40 + i * 50
        draw.line([(cx - 260 - i * 30, y), (cx - 190 - i * 30, y)], fill=ACCENT, width=10)


def pose_shock(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY)
    r = 10
    eye_y = HEAD_CY - 15
    draw.ellipse([HEAD_CX - 55 - r, eye_y - r, HEAD_CX - 55 + r, eye_y + r], fill=BG_COLOR, outline=INK, width=5)
    draw.ellipse([HEAD_CX + 30 - r, eye_y - r, HEAD_CX + 30 + r, eye_y + r], fill=BG_COLOR, outline=INK, width=5)
    draw.ellipse([HEAD_CX - 25, HEAD_CY + 35, HEAD_CX + 25, HEAD_CY + 75], outline=INK, width=8)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, HEAD_CX, hip_y)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 40), (HEAD_CX - 170, HEAD_CY + HEAD_R - 40)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 40), (HEAD_CX + 170, HEAD_CY + HEAD_R - 40)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX - 90, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX + 90, hip_y + 260)], fill=INK, width=STROKE)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = HEAD_CX + (HEAD_R + 40) * math.cos(rad)
        y1 = HEAD_CY + (HEAD_R + 40) * math.sin(rad)
        x2 = HEAD_CX + (HEAD_R + 75) * math.cos(rad)
        y2 = HEAD_CY + (HEAD_R + 75) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=ACCENT, width=8)


def pose_power(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, HEAD_CX, hip_y)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 50), (HEAD_CX - 140, HEAD_CY + HEAD_R + 10)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX - 140, HEAD_CY + HEAD_R + 10), (HEAD_CX - 150, HEAD_CY + HEAD_R - 90)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 50), (HEAD_CX + 140, HEAD_CY + HEAD_R + 10)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX + 140, HEAD_CY + HEAD_R + 10), (HEAD_CX + 150, HEAD_CY + HEAD_R - 90)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX - 100, hip_y + 250)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX + 100, hip_y + 250)], fill=INK, width=STROKE)
    draw.arc([HEAD_CX - HEAD_R - 60, HEAD_CY - HEAD_R - 60, HEAD_CX + HEAD_R + 60, HEAD_CY + HEAD_R + 60],
             start=200, end=340, fill=ACCENT, width=10)


def pose_focus(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY)
    hip_y = HEAD_CY + HEAD_R + 320
    draw_body(draw, HEAD_CX, hip_y)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 50), (HEAD_CX - 130, HEAD_CY + HEAD_R + 170)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 50), (HEAD_CX + 130, HEAD_CY + HEAD_R + 170)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX - 90, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX + 90, hip_y + 260)], fill=INK, width=STROKE)
    for r in (70, 110, 150):
        draw.ellipse([HEAD_CX - r, HEAD_CY - r, HEAD_CX + r, HEAD_CY + r], outline=ACCENT, width=4)


def pose_win(draw: ImageDraw.ImageDraw) -> None:
    draw_head(draw, HEAD_CX, HEAD_CY)
    hip_y = HEAD_CY + HEAD_R + 300
    draw_body(draw, HEAD_CX, hip_y)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 40), (HEAD_CX - 150, HEAD_CY - 100)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, HEAD_CY + HEAD_R + 40), (HEAD_CX + 150, HEAD_CY - 100)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX - 90, hip_y + 260)], fill=INK, width=STROKE)
    draw.line([(HEAD_CX, hip_y), (HEAD_CX + 90, hip_y + 260)], fill=INK, width=STROKE)
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1 = HEAD_CX + (HEAD_R + 90) * math.cos(rad)
        y1 = (HEAD_CY - 220) + (HEAD_R + 90) * math.sin(rad)
        x2 = HEAD_CX + (HEAD_R + 130) * math.cos(rad)
        y2 = (HEAD_CY - 220) + (HEAD_R + 130) * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=ACCENT, width=8)


POSE_DRAWERS = {
    "idle": pose_idle, "think": pose_think, "run": pose_run,
    "shock": pose_shock, "power": pose_power, "focus": pose_focus, "win": pose_win,
}


def get_or_render_pose(pose: str) -> Path:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DIR / f"pose_{pose}.png"
    if path.exists():
        return path
    img = new_canvas()
    draw = ImageDraw.Draw(img)
    POSE_DRAWERS.get(pose, pose_idle)(draw)
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


def build_pose_timeline(cues: list[tuple[float, float, str]], total_duration: float) -> list[tuple[float, str]]:
    timeline: list[tuple[float, str]] = []
    cursor = 0.0
    last_pose = "idle"
    for start, end, text in cues:
        if start > cursor + 0.05:
            timeline.append((start - cursor, last_pose))
            cursor = start
        pose = select_pose(text)
        seg_dur = max(0.12, end - cursor)
        timeline.append((seg_dur, pose))
        cursor = end
        last_pose = pose
    if cursor < total_duration - 0.05:
        timeline.append((total_duration - cursor, last_pose))
    if not timeline:
        timeline = [(total_duration, "idle")]
    return timeline


def build_base_video(idea_id: int, timeline: list[tuple[float, str]], total_duration: float) -> Path:
    base_video = OUTPUT_DIR / f"tmp_base_{idea_id}.mp4"
    seg_files: list[Path] = []

    for i, (seg_dur, pose) in enumerate(timeline):
        pose_path = get_or_render_pose(pose)
        seg_path = OUTPUT_DIR / f"tmp_poseseg_{idea_id}_{i}.mp4"
        frames = max(1, int(seg_dur * 24))
        vf = f"scale={W}:{H},format=yuv420p"
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(pose_path),
            "-vf", vf, "-r", "24", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-t", f"{seg_dur:.3f}", str(seg_path),
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    concat_list = OUTPUT_DIR / f"tmp_poseconcat_{idea_id}.txt"
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
    timeline = build_pose_timeline(cues, duration)
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
        "-crf", "23",
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
