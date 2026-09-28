import re
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
        text=True
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)

        raise RuntimeError(
            f"{error_name}: command failed"
        )

    return result


def prepare_telugu_text(text):
    """
    Prepare Telugu narration for natural sentence flow.

    Important:
    - Do not break words with artificial punctuation.
    - Keep words that belong together in the same phrase.
    - Use commas only for natural short pauses.
    - Use full stops only for real sentence boundaries.
    """

    text = str(text).strip()

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: empty text"
        )

    # Normalize line breaks/tabs to spaces.
    text = re.sub(r"[\r\n\t]+", " ", text)

    # Collapse repeated spaces.
    text = re.sub(r"\s+", " ", text)

    # Remove accidental spaces before punctuation.
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # Remove repeated punctuation.
    text = re.sub(r"[.]{2,}", ".", text)
    text = re.sub(r"[,]{2,}", ",", text)

    # Do NOT allow commas to split very short joined Telugu phrases.
    text = re.sub(
        r"([అ-హా-ౌ])\s*,\s*([అ-హా-ౌ])",
        r"\1 \2",
        text
    )

    # Remove unnecessary punctuation between Telugu words.
    text = re.sub(
        r"([ఀ-౿])\s*[-–—]\s*([ఀ-౿])",
        r"\1 \2",
        text
    )

    # Keep one clean space between words.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def create_piper_audio(text, output_path):
    text = prepare_telugu_text(text)

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

    print("Piper narration text:")
    print(text)

    result = subprocess.run(
        [
            piper,
            "--model",
            str(model_path),

            # Slightly faster and more natural flow.
            "--length_scale",
            "0.92",

            # Reduce excessive phoneme-duration variation.
            "--noise_w",
            "0.35",

            "--noise_scale",
            "0.667",

            # Do not add an artificial sentence gap.
            "--sentence_silence",
            "0",

            "--output_file",
            str(output_path),
        ],
        input=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
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
    print("Generating clean Telugu narration...")

    create_piper_audio(
        text,
        NARRATION_WAV
    )

    return NARRATION_WAV


def create_final_audio(narration):
    print("Processing clean Telugu narration...")

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
        "AUDIO_PROCESSING_FAILED"
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
        "VOICE_MP3_FAILED"
    )

    validate_audio(
        VOICE_MP3,
        5000
    )

    print("Clean Telugu narration created.")

    return str(VOICE_WAV)


def generate_voice(text):
    text = prepare_telugu_text(text)

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
