import shutil
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_WAV = OUTPUT_DIR / "voice.wav"
VOICE_MP3 = OUTPUT_DIR / "voice.mp3"

NARRATION_WAV = OUTPUT_DIR / "narration.wav"
CHANT_WAV = OUTPUT_DIR / "chant.wav"

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


def create_chant_audio():
    print("Generating clean devotional chant...")

    chant_source = (
        OUTPUT_DIR /
        "chant_source.wav"
    )

    # Deliberately no echo/reverb.
    # Clean repeated mantra with slower timing.
    mantra = (
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ."
    )

    create_piper_audio(
        mantra,
        chant_source
    )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(chant_source),

            "-filter_complex",
            (
                "[0:a]"
                "asetrate=22050*0.93,"
                "aresample=48000,"
                "atempo=0.93,"
                "highpass=f=70,"
                "lowpass=f=6000,"
                "volume=0.38"
                "[chant]"
            ),

            "-map",
            "[chant]",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(CHANT_WAV),
        ],
        "CHANT_PROCESSING_FAILED",
    )

    validate_audio(
        CHANT_WAV,
        10000
    )

    return CHANT_WAV


def get_duration(audio_path):
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


def create_final_audio(
    narration,
    chant
):
    print("Mixing clean devotional audio...")

    narration_duration = get_duration(
        narration
    )

    chant_duration = get_duration(
        chant
    )

    total_duration = max(
        narration_duration,
        chant_duration
    )

    # No synthetic background noise/music.
    # Only clean Telugu narration + low-volume chant.
    run_command(
        [
            "ffmpeg",
            "-y",

            "-i",
            str(narration),

            "-i",
            str(chant),

            "-filter_complex",
            (
                "[0:a]"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=1.0"
                "[n];"

                "[1:a]"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=0.32"
                "[c];"

                "[n][c]"
                "amix="
                "inputs=2:"
                "duration=first:"
                "dropout_transition=1,"
                "loudnorm="
                "I=-16:"
                "TP=-1.5:"
                "LRA=7"
                "[out]"
            ),

            "-map",
            "[out]",

            "-ar",
            "48000",
            "-ac",
            "2",

            "-t",
            str(total_duration),

            str(VOICE_WAV),
        ],
        "AUDIO_MIX_FAILED",
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

    print("Clean devotional audio created.")

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

    chant = create_chant_audio()

    return create_final_audio(
        narration,
        chant
    )
