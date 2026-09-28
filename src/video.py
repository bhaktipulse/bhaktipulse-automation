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

        raise RuntimeError(
            f"{error_name}: command failed"
        )

    return result


def get_telugu_font():
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

    font_path = result.stdout.strip()

    if (
        not font_path
        or not Path(font_path).exists()
    ):
        raise RuntimeError(
            "TELUGU_FONT_FAILED: Noto Sans Telugu not found"
        )

    return font_path


def clean_text(text):
    return str(text).strip()


def create_text_card(text, index):
    font_path = get_telugu_font()

    canvas = Image.new(
        "RGBA",
        (1080, 420),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(canvas)

    font = ImageFont.truetype(
        font_path,
        52,
    )

    text = clean_text(text)

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=12,
        align="center",
    )

    text_width = (
        bbox[2] - bbox[0]
    )

    text_height = (
        bbox[3] - bbox[1]
    )

    x = (
        1080 - text_width
    ) // 2

    y = (
        420 - text_height
    ) // 2

    # Dark translucent panel
    draw.rounded_rectangle(
        (35, 35, 1045, 385),
        radius=34,
        fill=(8, 8, 8, 190),
    )

    # Gold border
    draw.rounded_rectangle(
        (35, 35, 1045, 385),
        radius=34,
        outline=(236, 190, 92, 240),
        width=3,
    )

    # Shadow
    draw.multiline_text(
        (x + 3, y + 4),
        text,
        font=font,
        fill=(0, 0, 0, 230),
        spacing=12,
        align="center",
    )

    # Telugu text
    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=(255, 248, 225, 255),
        spacing=12,
        align="center",
    )

    path = (
        TEXT_DIR /
        f"card_{index}.png"
    )

    canvas.save(
        path,
        format="PNG"
    )

    return path


def prepare_text_cards(text_cards):
    cards = []

    for index, text in enumerate(
        text_cards,
        start=1
    ):
        text = clean_text(text)

        if text:
            cards.append(
                create_text_card(
                    text,
                    index
                )
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
        duration = float(
            result.stdout.strip()
        )

        if duration > 0:
            return duration

    except Exception:
        pass

    return 20.0


def create_visual_base(
    image_path,
    duration
):
    output = (
        OUTPUT_DIR /
        "visual_base.mp4"
    )

    scene1 = duration * 0.25
    scene2 = duration * 0.25
    scene3 = duration * 0.25
    scene4 = (
        duration -
        scene1 -
        scene2 -
        scene3
    )

    filter_complex = f"""
[0:v]
scale=1350:2400:
force_original_aspect_ratio=increase,
crop=1080:1920:
x='(iw-1080)/2':
y='(ih-1920)/2',
zoompan=
z='min(zoom+0.0010,1.20)':
x='iw/2-(iw/zoom/2)':
y='ih/2-(ih/zoom/2)':
d=1:
s=1080x1920:
fps=30,
eq=
brightness=0.02:
contrast=1.06:
saturation=1.10,
trim=duration={scene1},
setpts=PTS-STARTPTS
[s1];

[0:v]
scale=1350:2400:
force_original_aspect_ratio=increase,
crop=1080:1920:
x='(iw-1080)/2':
y='(ih-1920)/2',
zoompan=
z='min(zoom+0.0007,1.14)':
x='iw/2-(iw/zoom/2)+35*sin(on/70)':
y='ih/2-(ih/zoom/2)':
d=1:
s=1080x1920:
fps=30,
eq=
brightness=0.00:
contrast=1.10:
saturation=1.08,
trim=duration={scene2},
setpts=PTS-STARTPTS
[s2];

[0:v]
scale=1350:2400:
force_original_aspect_ratio=increase,
crop=1080:1920:
x='(iw-1080)/2':
y='(ih-1920)/2',
zoompan=
z='1.16-0.00065*on':
x='iw/2-(iw/zoom/2)-30*sin(on/90)':
y='ih/2-(ih/zoom/2)+25*cos(on/85)':
d=1:
s=1080x1920:
fps=30,
eq=
brightness=-0.01:
contrast=1.08:
saturation=1.12,
trim=duration={scene3},
setpts=PTS-STARTPTS
[s3];

[0:v]
scale=1350:2400:
force_original_aspect_ratio=increase,
crop=1080:1920:
x='(iw-1080)/2':
y='(ih-1920)/2',
zoompan=
z='min(zoom+0.00045,1.10)':
x='iw/2-(iw/zoom/2)':
y='ih/2-(ih/zoom/2)-35*sin(on/100)':
d=1:
s=1080x1920:
fps=30,
eq=
brightness=0.01:
contrast=1.05:
saturation=1.06,
trim=duration={scene4},
setpts=PTS-STARTPTS
[s4];

[s1][s2][s3][s4]
concat=n=4:v=1:a=0,
format=yuv420p,
fade=t=in:st=0:d=0.8,
fade=t=out:
st={max(0.8, duration - 0.8)}:
d=0.8
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


def create_text_overlay_ass(
    text_cards,
    duration
):
    ass_path = (
        OUTPUT_DIR /
        "telugu_overlay.ass"
    )

    # ASS uses libass for proper complex-script
    # shaping, including Telugu.
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Devotional,Noto Sans Telugu,48,&H00FFF8E1,&H00FFF8E1,&H00101010,&H99000000,-1,0,0,0,100,100,0,0,1,3,1,2,55,55,210,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    card_count = len(text_cards)

    if card_count == 0:
        raise RuntimeError(
            "VIDEO_TEXT_FAILED: no text cards"
        )

    card_duration = (
        duration /
        card_count
    )

    def ass_time(seconds):
        seconds = max(
            0.0,
            float(seconds)
        )

        hours = int(
            seconds // 3600
        )

        minutes = int(
            (seconds % 3600) // 60
        )

        secs = (
            seconds %
            60
        )

        whole = int(secs)
        centis = int(
            round(
                (secs - whole) * 100
            )
        )

        if centis >= 100:
            whole += 1
            centis = 0

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{whole:02d}."
            f"{centis:02d}"
        )

    events = []

    for index, text in enumerate(
        text_cards
    ):
        start = (
            index *
            card_duration
        )

        end = min(
            duration,
            (index + 1) *
            card_duration
        )

        # ASS line breaks
        # remain Telugu-safe.
        safe_text = (
            str(text)
            .strip()
            .replace(
                "\n",
                "\\N"
            )
        )

        events.append(
            "Dialogue: "
            f"0,"
            f"{ass_time(start)},"
            f"{ass_time(end)},"
            f"Devotional,,"
            f"0,0,0,,"
            f"{safe_text}"
        )

    ass_path.write_text(
        header +
        "\n".join(events) +
        "\n",
        encoding="utf-8"
    )

    return ass_path


def create_video(
    image_path,
    voice_path,
    text_cards
):
    image_path = Path(
        image_path
    )

    voice_path = Path(
        voice_path
    )

    if not image_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: image missing"
        )

    if not voice_path.exists():
        raise RuntimeError(
            "VIDEO_INPUT_FAILED: voice missing"
        )

    duration = get_audio_duration(
        voice_path
    )

    duration = max(
        12.0,
        min(duration, 60.0)
    )

    if not text_cards:
        raise RuntimeError(
            "VIDEO_TEXT_FAILED: no text cards"
        )

    visual_base = create_visual_base(
        image_path,
        duration
    )

    ass_file = create_text_overlay_ass(
        text_cards,
        duration
    )

    # FFmpeg/libass renders Telugu text.
    # No Pillow text image is placed over the video.
    run_command(
        [
            "ffmpeg",
            "-y",

            "-i",
            str(visual_base),

            "-i",
            str(voice_path),

            "-vf",
            f"ass={ass_file}",

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

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

    print(
        "Final devotional video created:",
        VIDEO_PATH
    )

    return str(VIDEO_PATH)
