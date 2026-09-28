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
        "/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf",
    ]

    for path in candidates:

        if Path(path).exists():
            return path

    if shutil.which("fc-match"):

        commands = [
            [
                "fc-match",
                "-f",
                "%{file}\n",
                "Noto Sans Telugu",
            ],
            [
                "fc-match",
                "-f",
                "%{file}\n",
                ":lang=te",
            ],
        ]

        for command in commands:

            try:

                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                )

                path = result.stdout.strip()

                if path and Path(path).exists():
                    return path

            except Exception:
                pass

    raise RuntimeError(
        "VIDEO_CREATION_FAILED: "
        "Telugu font not found on runner"
    )


def get_audio_duration(audio_path):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "could not read audio duration"
        )

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "invalid audio duration"
        )

    if duration <= 0:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "audio duration is zero"
        )

    return duration


def prepare_text(text):

    text = " ".join(
        str(text).strip().split()
    )

    if not text:
        return ""

    lines = textwrap.wrap(
        text,
        width=24,
        break_long_words=False,
        break_on_hyphens=False,
    )

    return "\n".join(lines)


def create_text_files(text_cards, temp_dir):

    paths = []

    for index, card in enumerate(text_cards):

        prepared = prepare_text(card)

        if not prepared:
            continue

        path = Path(temp_dir) / (
            f"card_{index}.txt"
        )

        path.write_text(
            prepared,
            encoding="utf-8",
        )

        paths.append(path)

    return paths


def escape_filter_path(path):

    value = str(path)

    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")

    return value


def create_video(
    image_path: str,
    voice_path: str,
    text_cards=None,
):

    image = Path(image_path)
    voice = Path(voice_path)

    if not image.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "image file not found"
        )

    if not voice.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "voice file not found"
        )

    if not text_cards:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "text cards are missing"
        )

    if not 3 <= len(text_cards) <= 5:
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: "
            "expected 3–5 text cards"
        )

    font_path = find_telugu_font()

    duration = get_audio_duration(
        voice
    )

    print(
        f"Voice duration: {duration:.2f} seconds"
    )

    print(
        f"Telugu font: {font_path}"
    )

    with tempfile.TemporaryDirectory(
        prefix="bhaktipulse_cards_"
    ) as temp_dir:

        text_files = create_text_files(
            text_cards,
            temp_dir,
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

        filters.append(
            "[0:v]"
            "scale="
            "1200:2134:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00035,1.07)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=1:"
            "s=1080x1920:"
            "fps=30,"
            "eq="
            "brightness=0.015:"
            "contrast=1.04:"
            "saturation=1.08,"
            "vignette=PI/5"
            "[base]"
        )

        filters.append(
            "[base]"
            "split=2"
            "[main][blur]"
        )

        filters.append(
            "[blur]"
            "gblur=sigma=18,"
            "format=rgba,"
            "colorchannelmixer=aa=0.10"
            "[glow]"
        )

        filters.append(
            "[main][glow]"
            "overlay=0:0:format=auto"
            "[motion]"
        )

        current = "[motion]"

        for index, path in enumerate(
            text_files
        ):

            start = (
                index * card_duration
            )

            end = (
                (index + 1)
                * card_duration
            )

            if index == len(text_files) - 1:
                end = duration

            textfile = escape_filter_path(
                path
            )

            next_label = (
                f"[text{index}]"
            )

            drawtext = (
                f"drawtext="
                f"fontfile='{font_path}':"
                f"textfile='{textfile}':"
                "fontcolor=white:"
                "fontsize=52:"
                "line_spacing=12:"
                "box=1:"
                "boxcolor=black@0.58:"
                "boxborderw=24:"
                "x=(w-text_w)/2:"
                "y=h*0.73:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )

            filters.append(
                f"{current}{drawtext}"
                f"{next_label}"
            )

            current = next_label

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

            "-loop",
            "1",

            "-framerate",
            "30",

            "-i",
            str(image),

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
            "160k",

            "-ar",
            "48000",

            "-shortest",

            "-movflags",
            "+faststart",

            str(VIDEO_PATH),
        ]

        print(
            "Creating devotional motion video "
            "with Telugu/English text cards..."
        )

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                "VIDEO_CREATION_FAILED:\n"
                + result.stderr[-8000:]
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
        f"Devotional motion video created: "
        f"{VIDEO_PATH}"
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
        "width,"
        "height,"
        "codec_name,"
        "r_frame_rate",

        "-of",
        "default=noprint_wrappers=1",

        str(VIDEO_PATH),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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
    ]

    for value in required:

        if value not in output:

            raise RuntimeError(
                "VIDEO_VALIDATION_FAILED: "
                f"{value} missing"
            )

    print(
        "Video validation passed:"
    )

    print(
        output.strip()
    )
