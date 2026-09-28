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
            "scale=1200:2134:force_original_aspect_ratio=increase,"
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
            "[base];"

            "[base]"
            "split=2"
            "[a][b];"

            "[b]"
            "scale=1080:1920,"
            "gblur=sigma=18,"
            "format=rgba,"
            "colorchannelmixer=aa=0.10"
            "[glow];"

            "[a][glow]"
            "overlay=0:0:format=auto,"
            "format=yuv420p"
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
        "Creating devotional motion video..."
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
            + result.stderr[-5000:]
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
