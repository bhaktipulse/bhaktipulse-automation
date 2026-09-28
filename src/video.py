import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_PATH = OUTPUT_DIR / "devotional.mp4"
TEXT_DIR = OUTPUT_DIR / "text_cards"
TEXT_DIR.mkdir(exist_ok=True)


def run(cmd, error_name):
    print("RUN:", " ".join(str(x) for x in cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"{error_name}: command failed with exit code {result.returncode}"
        )

    return result


def get_telugu_font():
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTelugu-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            return path

    result = subprocess.run(
        [
            "fc-match",
            "-f",
            "%{file}",
            "Noto Sans Telugu",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    path = result.stdout.strip()

    if path and Path(path).exists():
        return path

    raise RuntimeError(
        "TELUGU_FONT_FAILED: Noto Sans Telugu font not found"
    )


def create_text_card(text, index):
    font_path = get_telugu_font()

    image = Image.new(
        "RGBA",
        (1000, 300),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(
        font_path,
        54,
    )

    # Measure text.
    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=8,
        align="center",
    )

    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    x = (1000 - width) // 2
    y = (300 - height) // 2

    # Dark translucent background.
    draw.rounded_rectangle(
        (30, 35, 970, 265),
        radius=35,
        fill=(0, 0, 0, 150),
        outline=(255, 215, 120, 210),
        width=3,
    )

    # Shadow.
    draw.multiline_text(
        (x + 3, y + 4),
        text,
        font=font,
        fill=(0, 0, 0, 230),
        spacing=8,
        align="center",
    )

    # Main text.
    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=(255, 248, 225, 255),
        spacing=8,
        align="center",
    )

    path = TEXT_DIR / f"card_{index}.png"
    image.save(path)

    return path


def prepare_text_cards(text_cards):
    cards = []

    for index, text in enumerate(text_cards, start=1):
        text = str(text).strip()

        if not text:
            continue

        cards.append(
            create_text_card(text, index)
        )

    if not cards:
        raise RuntimeError(
            "VIDEO_TEXT_FAILED: no valid text cards"
        )

    return cards


def create_video(image_path, voice_path, text_cards):
    image_path = Path(image_path)
    voice_path = Path(voice_path)

    if not image_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: devotional image missing"
        )

    if not voice_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: voice audio missing"
        )

    print("")
    print("Preparing Telugu text cards...")
    cards = prepare_text_cards(text_cards)

    print(f"Text cards created: {len(cards)}")

    # Determine audio duration.
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(voice_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        duration = float(probe.stdout.strip())
    except Exception:
        duration = 25.0

    duration = max(12.0, min(duration, 60.0))

    # Same exact deity image, but three different camera movements.
    # This gives visual movement without generating inconsistent deity images.
    scene1 = max(3.0, duration * 0.34)
    scene2 = max(3.0, duration * 0.33)
    scene3 = max(3.0, duration - scene1 - scene2)

    # Ensure final duration is positive.
    scene3 = max(3.0, scene3)

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
z='min(zoom+0.00045,1.10)':
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
fade=t=out:st={max(0.8, duration-0.7)}:d=0.7
[base];

color=c=black@0.0:
s=1080x1920:
r=30,
d={duration}
[transparent];

[base][transparent]
overlay=shortest=1
[video]
""".strip()

    scene_file = OUTPUT_DIR / "visual_base.mp4"

    run(
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
            "[video]",
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
            str(scene_file),
        ],
        "VIDEO_SCENE_CREATION_FAILED",
    )

    # Add Telugu cards as timed overlays.
    #
    # Cards are distributed across the full video.
    inputs = [
        "-i",
        str(scene_file),
    ]

    for card in cards:
        inputs.extend(["-i", str(card)])

    inputs.extend(["-i", str(voice_path)])

    overlay_chain = "[0:v]"

    card_duration = duration / len(cards)

    filters = []

    for i, _card in enumerate(cards):
        input_index = i + 1
        start = i * card_duration
        end = min(duration, (i + 1) * card_duration)

        next_label = f"[v{i+1}]"

        filters.append(
            f"[{input_index}:v]"
            f"format=rgba,"
            f"fade=t=in:st=0:d=0.35:alpha=1,"
            f"fade=t=out:st={max(0.1, card_duration-0.35)}:d=0.35:alpha=1"
            f"[card{i}]"
        )

        filters.append(
            f"{overlay_chain}[card{i}]"
            f"overlay="
            f"(main_w-overlay_w)/2:"
            f"main_h-overlay_h-180:"
            f"enable='between(t,{start},{end})'"
            f"{next_label}"
        )

        overlay_chain = next_label

    filters.append(
        f"{overlay_chain}format=yuv420p[vout]"
    )

    filter_complex_cards = ";".join(filters)

    run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex_cards,
            "-map",
            "[vout]",
            "-map",
            f"{len(cards)+1}:a:0",
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
        "VIDEO_FINAL_CREATION_FAILED",
    )

    if not VIDEO_PATH.exists():
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: final MP4 missing"
        )

    if VIDEO_PATH.stat().st_size < 100_000:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: final MP4 too small"
        )

    print("")
    print("====================================")
    print("DEVOTIONAL VIDEO READY")
    print("====================================")
    print(f"Video: {VIDEO_PATH}")
    print(f"Duration: {duration:.2f}s")
    print(f"Resolution: 1080x1920")
    print(f"FPS: 30")
    print(f"Text cards: {len(cards)}")
    print("Telugu text: Pillow + Noto Sans Telugu")
    print("Visual treatment: 3 camera movements")
    print("====================================")

    return str(VIDEO_PATH)
