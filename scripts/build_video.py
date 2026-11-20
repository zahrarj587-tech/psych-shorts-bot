import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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
        "ffprobe",
        "-v", "error",
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
            start_s, end_s = [part.strip() for part in lines[1].split("-->")]
            start_sec = parse_srt_time(start_s)
            end_sec = parse_srt_time(end_s)
            text = " ".join(lines[2:])
            items.append((start_sec, end_sec, text))
    return items


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/system/fonts/Roboto-Bold.ttf",
        "/system/fonts/DroidSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


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


def render_single_line_image(
    line_words: list[str],
    out_path: Path,
    cue_idx: int,
    base_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    hi_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    # Compact transparent strip centered horizontally (1080x140)
    canvas = Image.new("RGBA", (1080, 140), (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", (1080, 140), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    draw = ImageDraw.Draw(canvas)

    line_items = []
    for w_i, word in enumerate(line_words):
        clean = re.sub(r"[^a-zA-Z]", "", word).lower()
        is_hi = (clean in KEYWORDS_HIGHLIGHT) or (w_i == (cue_idx % max(1, len(line_words))) and len(clean) >= 4)
        f_use = hi_font if is_hi else base_font
        wb = draw.textbbox((0, 0), word + " ", font=f_use)
        line_items.append((word, f_use, is_hi, wb[2] - wb[0]))

    total_w = sum(item[3] for item in line_items)
    x_start = max(90, (1080 - total_w) // 2)
    y_base = 34

    cursor_x = x_start
    for word, f_use, is_hi, adv in line_items:
        y_off = -3 if is_hi else 0
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (3, 3)]:
            sdraw.text((cursor_x + ox, y_base + y_off + oy), word, font=f_use, fill=(0, 0, 0, 245))

        color = (56, 189, 248, 255) if is_hi else (248, 250, 252, 255)
        draw.text((cursor_x, y_base + y_off), word, font=f_use, fill=color)
        cursor_x += adv

    blurred_shadow = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    final_img = Image.alpha_composite(blurred_shadow, canvas)
    final_img.save(out_path, "PNG")


def render_brand_header(idea_id: int) -> Path:
    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    header_path = CAPTIONS_DIR / f"idea_{idea_id}_brand.png"
    canvas = Image.new("RGBA", (1080, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    brand_font = load_font(26)
    brand_text = "BEHAVIOR LAB"
    bb = draw.textbbox((0, 0), brand_text, font=brand_font)
    bx = (1080 - (bb[2] - bb[0])) // 2
    draw.text((bx + 2, 42), brand_text, font=brand_font, fill=(0, 0, 0, 180))
    draw.text((bx, 40), brand_text, font=brand_font, fill=(148, 163, 184, 175))
    canvas.save(header_path, "PNG")
    return header_path


def render_stacked_caption_layers(srt_path: Path, idea_id: int) -> list[dict]:
    """
    Splits each cue into short stacked lines (max 2 words per line)
    and returns timed layer entries so lines animate sequentially from top to bottom.
    """
    CAPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    cues = parse_srt(srt_path)
    base_font = load_font(54)
    hi_font = load_font(60)
    layers: list[dict] = []

    max_line_width = 780

    for c_idx, (start_sec, end_sec, text) in enumerate(cues, start=1):
        cue_dur = max(0.35, end_sec - start_sec)
        words = text.split()

        # Group into compact stacked lines (up to 2 words per line for punchy vertical rhythm)
        lines: list[list[str]] = []
        current: list[str] = []
        for w in words:
            trial_list = current + [w]
            trial_str = " ".join(trial_list)
            bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), trial_str, font=hi_font)
            if len(current) < 2 and (bbox[2] - bbox[0]) <= max_line_width:
                current.append(w)
            else:
                if current:
                    lines.append(current)
                current = [w]
        if current:
            lines.append(current)

        # Merge tiny trailing single word into previous line if there are > 2 lines
        if len(lines) > 2 and len(lines[-1]) == 1:
            lines[-2].append(lines[-1][0])
            lines.pop()

        num_lines = len(lines)
        row_step = 112
        total_stack_h = num_lines * row_step
        center_y = 950
        first_line_y = center_y - (total_stack_h // 2)

        stagger = min(0.14, cue_dur / max(1, num_lines * 2.5))

        for l_idx, line_words in enumerate(lines):
            line_start = start_sec + (l_idx * stagger)
            if line_start >= end_sec - 0.05:
                line_start = max(start_sec, end_sec - 0.12)

            line_img_path = CAPTIONS_DIR / f"idea_{idea_id}_c{c_idx}_l{l_idx + 1}.png"
            render_single_line_image(
                line_words=line_words,
                out_path=line_img_path,
                cue_idx=c_idx + l_idx,
                base_font=base_font,
                hi_font=hi_font,
            )

            target_y = int(first_line_y + l_idx * row_step)
            layers.append({
                "path": line_img_path,
                "start": line_start,
                "end": end_sec,
                "target_y": target_y,
            })

    return layers


def build_base_video(idea: dict, duration: float) -> Path:
    idea_id = idea.get("id", 1)
    base_video = OUTPUT_DIR / f"tmp_base_{idea_id}.mp4"
    nature_imgs = download_nature_images(idea, count=4)

    if not nature_imgs:
        fallback = ASSETS_DIR / f"fallback_dark_{idea_id}.jpg"
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1080, 1920), (8, 12, 24))
        img.save(fallback, "JPEG")
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
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-t", f"{seg_dur:.2f}",
            str(seg_path),
        ]
        subprocess.run(cmd, check=True)
        seg_files.append(seg_path)

    concat_list = OUTPUT_DIR / f"tmp_natconcat_{idea_id}.txt"
    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in seg_files) + "\n", encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", "-t", f"{duration:.2f}", str(base_video)],
        check=True,
    )
    for p in [*seg_files, concat_list]:
        if p.exists():
            p.unlink()

    return base_video


def build_short_video(idea: dict) -> None:
    idea_id = idea.get("id", 1)
    audio_path = OUTPUT_DIR / f"idea_{idea_id}.mp3"
    srt_path = OUTPUT_DIR / f"idea_{idea_id}.srt"
    video_path = OUTPUT_DIR / f"idea_{idea_id}.mp4"

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    duration = get_audio_duration(audio_path)
    base_video = build_base_video(idea, duration)
    brand_img = render_brand_header(idea_id)
    layers = render_stacked_caption_layers(srt_path, idea_id)

    cmd = ["ffmpeg", "-y", "-i", str(base_video), "-i", str(brand_img)]
    for item in layers:
        cmd.extend(["-i", str(item["path"])])
    cmd.extend(["-i", str(audio_path)])

    filter_parts: list[str] = []
    # Overlay brand header at top
    filter_parts.append("[0:v][1:v]overlay=0:140[vbrand]")
    current_label = "[vbrand]"

    # Animate each stacked line: smooth slide-up + gentle pop over first 0.14s without clipping edges
    for idx, item in enumerate(layers):
        inp_idx = idx + 2
        t0 = item["start"]
        t1 = item["end"]
        anim_end = t0 + 0.14
        ty = item["target_y"]
        scaled_lbl = f"[ls{idx}]"
        out_lbl = f"[vl{idx}]"

        filter_parts.append(
            f"[{inp_idx}:v]scale=w='if(lt(t,{anim_end:.3f}),1080*(1.05-0.05*((t-{t0:.3f})/0.14)),1080)':h=-1:eval=frame{scaled_lbl}"
        )
        y_expr = f"if(lt(t,{anim_end:.3f}),{ty + 28}-28*((t-{t0:.3f})/0.14),{ty})"
        filter_parts.append(
            f"{current_label}{scaled_lbl}overlay=(W-w)/2:{y_expr}:enable='between(t,{t0:.3f},{t1:.3f})'{out_lbl}"
        )
        current_label = out_lbl

    audio_input_idx = len(layers) + 2
    filter_complex = ";".join(filter_parts)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", current_label,
        "-map", f"{audio_input_idx}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.2f}",
        str(video_path),
    ])

    subprocess.run(cmd, check=True)
    if base_video.exists():
        base_video.unlink()
    print(f"Saved stacked animated video: {video_path}")


def main() -> None:
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        build_short_video(idea)


if __name__ == "__main__":
    main()
