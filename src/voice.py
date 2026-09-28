import shutil
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_WAV = OUTPUT_DIR / "voice.wav"
VOICE_MP3 = OUTPUT_DIR / "voice.mp3"

NARRATION_WAV = OUTPUT_DIR / "narration.wav"

PIPER_MODEL = "piper_voices/te_IN-maya-medium.onnx"


def validate_audio(path, minimum_size=10000):
    path = Path(path)

    if not path.exists():
        raise RuntimeError(
            f"VOICE_VALIDATION_FAILED: missing {path}"
        )

    if path.stat().st_size < minimum_size:
        raise RuntimeError(
            f"VOICE_VALIDATION_FAILED: audio file too small: {path}"
        )


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


def clean_text(text):
    return " ".join(
        str(text).strip().split()
    )


def create_piper_audio(text, output_path):
    text = clean_text(text)

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: empty text"
        )

    piper = shutil.which("piper")

    if not piper:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: piper not found"
        )

    model_path = Path(PIPER_MODEL)

    if not model_path.exists():
        raise RuntimeError(
            f"PIPER_MODEL_FAILED: model not found: {model_path}"
        )

    output_path = Path(output_path)

    result = subprocess.run(
        [
            piper,
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ],
        input=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)

        raise RuntimeError(
            "PIPER_TTS_FAILED: " +
            result.stderr[-2000:]
        )

    validate_audio(
        output_path,
        10000
    )

    return output_path


def create_narration(text):
    print("Generating Telugu neural narration...")

    create_piper_audio(
        text,
        NARRATION_WAV
    )

    return NARRATION_WAV


def create_final_audio(narration):
    print("Using clean Telugu narration only...")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(narration),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(VOICE_WAV),
        ],
        "AUDIO_PROCESSING_FAILED",
    )

    validate_audio(
        VOICE_WAV,
        20000
    )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(VOICE_WAV),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(VOICE_MP3),
        ],
        "VOICE_MP3_FAILED",
    )

    validate_audio(
        VOICE_MP3,
        5000
    )

    print("Clean Telugu narration created.")

    return str(VOICE_WAV)


def generate_voice(text):
    text = clean_text(text)

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: empty voice script"
        )

    narration = create_narration(
        text
    )

    return create_final_audio(
        narration
    )
