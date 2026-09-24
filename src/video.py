import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_PATH = OUTPUT_DIR / "devotional.mp4"


def create_video(image_path: str, voice_path: str):
    image = Path(image_path)
    voice = Path(voice_path)

    if not image.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: image file not found"
        )

    if not voice.exists():
        raise RuntimeError(
            "VIDEO_CREATION_FAILED: voice file not found"
        )

    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image),
        "-i",
        str(voice),

        "-filter_complex",
        (
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan="
            "z='min(zoom+0.0005,1.08)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=1:"
            "s=1080x1920:"
            "fps=30"
            "[v]"
        ),

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

        "-c:a",
        "aac",
        "-b:a",
        "128k",

        "-shortest",

        "-movflags",
        "+faststart",

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
            "VIDEO_CREATION_FAILED:\n"
            + result.stderr[-4000:]
        )

    if not VIDEO_PATH.exists():
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: MP4 was not created"
        )

    if VIDEO_PATH.stat().st_size < 100_000:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: MP4 file too small"
        )

    validate_video()

    return str(VIDEO_PATH)


def validate_video():
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name",
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
            "VIDEO_VALIDATION_FAILED: ffprobe failed"
        )

    output = result.stdout

    if "width=1080" not in output:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: width is not 1080"
        )

    if "height=1920" not in output:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: height is not 1920"
        )

    if "codec_name=h264" not in output:
        raise RuntimeError(
            "VIDEO_VALIDATION_FAILED: video codec is not H.264"
        )
