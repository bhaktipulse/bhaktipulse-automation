import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_PATH = OUTPUT_DIR / "devotional.mp4"
TEXT_DIR = OUTPUT_DIR / "text_cards"
TEXT_DIR.mkdir(exist_ok=True)


def run_command(command, error_name):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"{error_name}: command failed")

    return result


def get_telugu_font():
    result = subprocess.run(
        ["fc-match", "-f", "%{file}", "Noto Sans Telugu"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    font_path = result.stdout.strip()

    if not font_path or not Path(font_path).exists():
        raise RuntimeError(
            "TELUGU_FONT_FAILED: Noto Sans Telugu not found"
        )

    return font_path


def create_text_card(text, index):
    font_path = get_telugu_font()

    canvas = Image.new(
        "RGBA",
        (1000, 300),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(canvas)

    font = ImageFont.truetype(
        font_path,
        52,
    )

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=8,
        align="center",
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (1000 - text_width) // 2
    y = (300 - text_height) // 2

    draw.rounded_rectangle(
        (25, 30, 975, 270),
        radius=32,
        fill=(0, 0, 0, 165),
        outline=(255, 215, 120, 220),
        width=3,
    )

    draw.multiline_text(
        (x + 3, y + 4),
        text,
        font=font,
        fill=(0, 0, 0, 230),
        spacing=8,
        align="center",
    )

    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=(255, 248, 225, 255),
        spacing=8,
        align="center",
    )

    path = TEXT_DIR / f"card_{index}.png"
    canvas.save(path)

    return path


def prepare_text_cards(text_cards):
    cards = []

    for index, text in enumerate(text_cards, start=1):
        text = str(text).strip()

        if text:
            cards.append(
                create_text_card(text, index)
            )

    if not cards:
        raise RuntimeError(
            "VIDEO_TEXT_FAILED: no text cards"
        )

    return cards


def get_audio_duration(audio_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        return float(result.stdout.strip())
    except Exception:
        return 20.0


def create_visual_base(image_path, duration):
    scene1 = duration * 0.34
    scene2 = duration * 0.33
    scene3 = duration - scene1 - scene2

    output = OUTPUT_DIR / "visual_base.mp4"

    filter_complex = f"""
[0:v]
scale=1080:1920:force_original_aspect_ratio=increase,
crop=1080:1920,
zoompan=
z='min(zoom+0.0007,1.16)':
x='iw/2-(iw/zoom/2)':
y='ih/2-(ih/zoom/2)':
d=1:
s=1080x1920:
fps=30,
trim=duration={scene1},
setpts=PTS-STARTPTS
[s1];

[0:v]
scale=1080:1920:force_original_aspect_ratio=increase,
crop=1080:1920,
zoompan=
z='min(zoom+0.0005,1.10)':
x='iw/2-(iw/zoom/2)':
y='ih/2-(ih/zoom/2)+30*sin(on/80)':
d=1:
s=1080x1920:
fps=30,
trim=duration={scene2},
setpts=PTS-STARTPTS
[s2];

[0:v]
scale=1080:1920:force_original_aspect_ratio=increase,
crop=1080:1920,
zoompan=
z='1.12-0.00045*on':
x='iw/2-(iw/zoom/2)+35*sin(on/90)':
y='ih/2-(ih/zoom/2)-20*cos(on/100)':
d=1:
s=1080x1920:
fps=30,
trim=duration={scene3},
setpts=PTS-STARTPTS
[s3];

[s1][s2][s3]
concat=n=3:v=1:a=0,
format=yuv420p,
fade=t=in:st=0:d=0.7,
fade=t=out:st={max(0.8, duration - 0.7)}:d=0.7
[v]
""".strip()

    run_command(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-t",
            str(duration),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            str(output),
        ],
        "VIDEO_SCENE_FAILED",
    )

    return output


def create_video(image_path, voice_path, text_cards):
    image_path = Path(image_path)
    voice_path = Path(voice_path)

    if not image_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: image missing"
        )

    if not voice_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: voice missing"
        )

    duration = get_audio_duration(voice_path)
    duration = max(12.0, min(duration, 60.0))

    cards = prepare_text_cards(text_cards)

    visual_base = create_visual_base(
        image_path,
        duration,
    )

    inputs = [
        "-i",
        str(visual_base),
    ]

    for card in cards:
        inputs.extend(
            ["-i", str(card)]
        )

    inputs.extend(
        ["-i", str(voice_path)]
    )

    filters = []
    current = "[0:v]"

    card_duration = duration / len(cards)

    for index, _ in enumerate(cards):
        input_index = index + 1

        start = index * card_duration
        end = min(
            duration,
            (index + 1) * card_duration
        )

        filters.append(
            f"[{input_index}:v]"
            "format=rgba"
            f"[card{index}]"
        )

        next_label = f"[v{index + 1}]"

        filters.append(
            f"{current}[card{index}]"
            "overlay="
            "(main_w-overlay_w)/2:"
            "main_h-overlay_h-170:"
            f"enable='between(t,{start},{end})'"
            f"{next_label}"
        )

        current = next_label

    filters.append(
        f"{current}format=yuv420p[vout]"
    )

    filter_complex = ";".join(filters)

    run_command(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            f"{len(cards) + 1}:a:0",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(VIDEO_PATH),
        ],
        "VIDEO_FINAL_FAILED",
    )

    if not VIDEO_PATH.exists():
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: MP4 missing"
        )

    if VIDEO_PATH.stat().st_size < 100000:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: MP4 too small"
        )

    print("Video created:", VIDEO_PATH)

    return str(VIDEO_PATH)
