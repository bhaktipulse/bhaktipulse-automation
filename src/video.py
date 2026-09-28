import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_PATH = OUTPUT_DIR / "devotional.mp4"


def find_telugu_font():
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTelugu-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTeluguUI-Regular.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            return path

    if shutil.which("fc-match"):
        commands = [
            ["fc-match", "-f", "%{file}\n", "Noto Sans Telugu"],
            ["fc-match", "-f", "%{file}\n", ":lang=te"],
        ]

        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )

                path = result.stdout.strip()

                if path and Path(path).exists():
                    return path

            except Exception:
                pass

    raise RuntimeError(
        "VIDEO_CREATION_FAILED: Telugu font not found"
    )


def get_duration(path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: duration detection failed"
        )

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: invalid duration"
        )

    if duration <= 0:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: zero duration"
        )

    return duration


def prepare_text(text):
    text = " ".join(
        str(text).strip().split()
    )

    if not text:
        return ""

    # Short mobile-friendly lines.
    lines = textwrap.wrap(
        text,
        width=22,
        break_long_words=False,
        break_on_hyphens=False
    )

    return "\n".join(lines)


def create_text_files(text_cards, temp_dir):
    paths = []

    for index, card in enumerate(text_cards):
        prepared = prepare_text(card)

        if not prepared:
            continue

        path = Path(temp_dir) / f"card_{index}.txt"

        path.write_text(
            prepared,
            encoding="utf-8"
        )

        paths.append(path)

    return paths


def escape_filter_path(path):
    value = str(path)

    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")

    return value


def create_video(
    image_path: str,
    voice_path: str,
    text_cards=None
):
    image = Path(image_path)
    voice = Path(voice_path)

    if not image.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: image not found"
        )

    if not voice.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: voice not found"
        )

    if not text_cards:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: text cards missing"
        )

    if not 3 <= len(text_cards) <= 5:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: expected 3–5 text cards"
        )

    font_path = find_telugu_font()

    duration = get_duration(voice)

    print(
        f"Final audio duration: {duration:.2f}s"
    )

    print(
        f"Telugu font: {font_path}"
    )

    with tempfile.TemporaryDirectory(
        prefix="bhaktipulse_video_"
    ) as temp_dir:

        text_files = create_text_files(
            text_cards,
            temp_dir
        )

        if not text_files:
            raise RuntimeError(
                "VIDEO_CREATION_FAILED: "
                "no usable text cards"
            )

        card_duration = (
            duration / len(text_files)
        )

        filters = []

        # ------------------------------------------------
        # BASE IMAGE
        # ------------------------------------------------

        filters.append(
            "[0:v]"
            "scale=1200:2134:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan="
            "z='1.0+0.0007*on':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=1:"
            "s=1080x1920:"
            "fps=30,"
            "eq="
            "brightness=0.015:"
            "contrast=1.05:"
            "saturation=1.08"
            "[base]"
        )

        # ------------------------------------------------
        # SOFT DEVOTIONAL GLOW
        # ------------------------------------------------

        filters.append(
            "[base]"
            "split=2"
            "[main][soft]"
        )

        filters.append(
            "[soft]"
            "gblur=sigma=22,"
            "format=rgba,"
            "colorchannelmixer=aa=0.14"
            "[glow]"
        )

        filters.append(
            "[main][glow]"
            "overlay=0:0:"
            "format=auto"
            "[scene]"
        )

        current = "[scene]"

        # ------------------------------------------------
        # TEXT CARDS
        # ------------------------------------------------

        for index, path in enumerate(text_files):

            start = (
                index * card_duration
            )

            end = (
                (index + 1)
                * card_duration
            )

            if index == len(text_files) - 1:
                end = duration

            textfile = escape_filter_path(path)

            next_label = (
                f"[card{index}]"
            )

            # Fade in/out for every card.
            fade_in_start = start
            fade_in_end = min(
                start + 0.45,
                end
            )

            fade_out_start = max(
                end - 0.45,
                start
            )

            drawtext = (
                "drawtext="
                f"fontfile='{font_path}':"
                f"textfile='{textfile}':"
                "fontcolor=white:"
                "fontsize=50:"
                "line_spacing=14:"
                "borderw=2:"
                "bordercolor=black@0.85:"
                "box=1:"
                "boxcolor=black@0.55:"
                "boxborderw=28:"
                "x=(w-text_w)/2:"
                "y=h*0.70:"
                f"alpha='if(lt(t,{fade_in_end:.3f}),"
                f"(t-{fade_in_start:.3f})/0.45,"
                f"if(gt(t,{fade_out_start:.3f}),"
                f"({end:.3f}-t)/0.45,1))':"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )

            filters.append(
                f"{current}"
                f"{drawtext}"
                f"{next_label}"
            )

            current = next_label

        # ------------------------------------------------
        # FINAL FORMAT
        # ------------------------------------------------

        filters.append(
            f"{current}"
            "format=yuv420p"
            "[v]"
        )

        filter_complex = ";".join(
            filters
        )

        command = [
            "ffmpeg",
            "-y",

            # Image input
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(image),

            # Final audio input
            "-i",
            str(voice),

            "-filter_complex",
            filter_complex,

            "-map",
            "[v]",

            "-map",
            "1:a",

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

            "-shortest",

            "-movflags",
            "+faststart",

            str(VIDEO_PATH),
        ]

        print(
            "Creating cinematic devotional video..."
        )

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                "VIDEO_CREATION_FAILED:\n"
                + result.stderr[-10000:]
            )

    if not VIDEO_PATH.exists():
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: "
            "MP4 was not created"
        )

    if VIDEO_PATH.stat().st_size < 100_000:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: "
            "MP4 file too small"
        )

    validate_video()

    print(
        f"Devotional video created: {VIDEO_PATH}"
    )

    return str(VIDEO_PATH)


def validate_video():

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream="
        "width,height,codec_name,r_frame_rate",
        "-of",
        "default=noprint_wrappers=1",
        str(VIDEO_PATH),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: "
            "ffprobe failed"
        )

    output = result.stdout

    required = [
        "width=1080",
        "height=1920",
        "codec_name=h264",
        "r_frame_rate=30/1",
    ]

    for value in required:
        if value not in output:
            raise RuntimeError(
                "VIDEO_VALIDATION_FAILED: "
                + value
                + " missing"
            )

    print(
        "Video validation passed:"
    )

    print(output.strip())
