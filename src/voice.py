import shutil
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_WAV = OUTPUT_DIR / "voice.wav"
VOICE_MP3 = OUTPUT_DIR / "voice.mp3"

NARRATION_WAV = OUTPUT_DIR / "narration.wav"
CHANT_WAV = OUTPUT_DIR / "chant.wav"
MUSIC_WAV = OUTPUT_DIR / "devotional_music.wav"

# Piper voice downloaded by GitHub Actions
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
    print(
        "Generating Telugu neural narration..."
    )

    create_piper_audio(
        text,
        NARRATION_WAV
    )

    return NARRATION_WAV


def create_chant_audio():
    print(
        "Generating devotional mantra track..."
    )

    chant_source = (
        OUTPUT_DIR /
        "chant_source.wav"
    )

    mantra = (
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ."
    )

    create_piper_audio(
        mantra,
        chant_source
    )

    # Slow down slightly, add reverb/echo and lower
    # the volume so it behaves more like a background
    # devotional chant instead of normal narration.
    run_command(
        [
            "ffmpeg",
            "-y",

            "-i",
            str(chant_source),

            "-filter_complex",
            (
                "[0:a]"
                "asetrate=22050*0.94,"
                "aresample=48000,"
                "atempo=0.86,"
                "aecho=0.8:0.75:120|240:0.32|0.18,"
                "highpass=f=80,"
                "lowpass=f=5000,"
                "volume=0.62"
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


def create_devotional_music(duration):
    print(
        "Generating devotional background ambience..."
    )

    duration = max(
        15,
        min(int(duration) + 8, 120)
    )

    run_command(
        [
            "ffmpeg",
            "-y",

            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "sine=frequency=110:sample_rate=48000",

            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "sine=frequency=220:sample_rate=48000",

            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "sine=frequency=330:sample_rate=48000",

            "-filter_complex",
            (
                "[0:a]"
                "volume=0.045"
                "[a];"

                "[1:a]"
                "volume=0.028"
                "[b];"

                "[2:a]"
                "volume=0.018"
                "[c];"

                "[a][b][c]"
                "amix=inputs=3:"
                "duration=longest:"
                "normalize=0,"
                "lowpass=f=1200,"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "afade=t=in:st=0:d=2,"
                f"afade=t=out:"
                f"st={max(2, duration - 3)}:"
                "d=3"
                "[music]"
            ),

            "-map",
            "[music]",

            "-ar",
            "48000",

            "-ac",
            "2",

            str(MUSIC_WAV),
        ],
        "MUSIC_GENERATION_FAILED",
    )

    validate_audio(
        MUSIC_WAV,
        10000
    )

    return MUSIC_WAV


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

        if duration <= 0:
            raise ValueError

        return duration

    except Exception:
        return 20.0


def create_final_audio(
    narration,
    chant
):
    print(
        "Mixing narration + mantra + background music..."
    )

    duration = get_duration(
        narration
    )

    music = create_devotional_music(
        duration + 12
    )

    run_command(
        [
            "ffmpeg",
            "-y",

            "-i",
            str(narration),

            "-i",
            str(chant),

            "-i",
            str(music),

            "-filter_complex",
            (
                # Main Telugu narration
                "[0:a]"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=1.0"
                "[n];"

                # Chant kept clearly below narration
                "[1:a]"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=0.52"
                "[c];"

                # Very low devotional ambience
                "[2:a]"
                "aformat="
                "sample_rates=48000:"
                "channel_layouts=stereo,"
                "volume=0.42"
                "[m];"

                "[n][c][m]"
                "amix="
                "inputs=3:"
                "duration=longest:"
                "dropout_transition=2,"
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

    print(
        "Audio creation completed."
    )

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
