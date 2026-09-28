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

PIPER_MODEL = "te_IN-maya-medium"


def run(cmd, error_name):
    print("RUN:", " ".join(str(x) for x in cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"{error_name}: command failed with exit code {result.returncode}"
        )

    return result


def clean_text(text):
    return " ".join(str(text).strip().split())


def validate_audio(path, minimum_size=10000):
    path = Path(path)

    if not path.exists():
        raise RuntimeError(f"VOICE_VALIDATION_FAILED: missing {path}")

    if path.stat().st_size < minimum_size:
        raise RuntimeError(
            f"VOICE_VALIDATION_FAILED: audio file too small: {path}"
        )


def create_piper_audio(text, output_path):
    text = clean_text(text)

    if not text:
        raise RuntimeError("VOICE_GENERATION_FAILED: empty text")

    piper = shutil.which("piper")

    if not piper:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: piper executable not found"
        )

    output_path = Path(output_path)

    # Piper automatically downloads the requested voice model
    # when the model name is supplied.
    run(
        [
            piper,
            "--model",
            PIPER_MODEL,
            "--output_file",
            str(output_path),
        ],
        "PIPER_TTS_FAILED",
    ) if False else None

    # Feed Telugu text through stdin.
    result = subprocess.run(
        [
            piper,
            "--model",
            PIPER_MODEL,
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
            "PIPER_TTS_FAILED: " + result.stderr[-2000:]
        )

    validate_audio(output_path)

    return output_path


def create_narration(text):
    print("")
    print("Generating Telugu neural narration with Piper...")
    print(f"Voice model: {PIPER_MODEL}")

    create_piper_audio(text, NARRATION_WAV)

    validate_audio(NARRATION_WAV)

    return NARRATION_WAV


def create_chant_audio():
    """
    Creates a separate mantra track.

    This is deliberately treated differently from narration:
    - slower tempo
    - lower pitch
    - repeated mantra
    - pauses
    - echo/reverb
    """

    print("")
    print("Generating devotional mantra track...")

    source = OUTPUT_DIR / "chant_source.wav"

    mantra = (
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ."
    )

    create_piper_audio(mantra, source)

    # Slow down + slightly lower pitch + echo/reverb.
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            (
                "[0:a]"
                "asetrate=22050*0.94,"
                "aresample=48000,"
                "atempo=0.86,"
                "aecho=0.8:0.75:90|180:0.28|0.14,"
                "volume=0.72"
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

    validate_audio(CHANT_WAV)

    return CHANT_WAV


def create_devotional_music(duration_seconds):
    """
    Copyright-safe procedural devotional ambience.

    It is intentionally subtle so it supports the voice instead
    of competing with the narration.
    """

    print("")
    print("Generating devotional background ambience...")

    duration_seconds = max(15, min(int(duration_seconds) + 5, 120))

    # Layered sustained tones create a soft drone/pad.
    filter_complex = (
        "[0:a]volume=0.055[a];"
        "[1:a]volume=0.035[b];"
        "[2:a]volume=0.025[c];"
        "[a][b][c]"
        "amix=inputs=3:duration=longest:normalize=0,"
        "lowpass=f=1200,"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"afade=t=in:st=0:d=2,"
        f"afade=t=out:st={max(2, duration_seconds - 3)}:d=3"
        "[music]"
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-t",
            str(duration_seconds),
            "-i",
            "sine=frequency=110:sample_rate=48000",
            "-f",
            "lavfi",
            "-t",
            str(duration_seconds),
            "-i",
            "sine=frequency=220:sample_rate=48000",
            "-f",
            "lavfi",
            "-t",
            str(duration_seconds),
            "-i",
            "sine=frequency=330:sample_rate=48000",
            "-filter_complex",
            filter_complex,
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

    validate_audio(MUSIC_WAV)

    return MUSIC_WAV


def create_final_audio(narration_path, chant_path):
    print("")
    print("Mixing narration + chant + devotional ambience...")

    narration_path = Path(narration_path)
    chant_path = Path(chant_path)

    narration_probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(narration_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        narration_duration = float(narration_probe.stdout.strip())
    except Exception:
        narration_duration = 20.0

    music_path = create_devotional_music(narration_duration + 12)

    # Chant starts after narration.
    # Music runs underneath the whole track.
    #
    # Voice is kept dominant.
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(narration_path),
            "-i",
            str(chant_path),
            "-i",
            str(music_path),
            "-filter_complex",
            (
                "[0:a]"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                "volume=1.0"
                "[n];"

                "[1:a]"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                "volume=0.70"
                "[c];"

                "[2:a]"
                "aformat=sample_rates=48000:channel_layouts=stereo,"
                "volume=0.55"
                "[m];"

                "[n][c][m]"
                "amix=inputs=3:duration=longest:dropout_transition=2,"
                "loudnorm=I=-16:TP=-1.5:LRA=7"
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

    validate_audio(VOICE_WAV, 20000)

    run(
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
        "VOICE_MP3_CREATION_FAILED",
    )

    validate_audio(VOICE_MP3, 5000)

    print("")
    print("====================================")
    print("DEVOTIONAL AUDIO READY")
    print("====================================")
    print(f"Narration : {narration_path}")
    print(f"Chant     : {chant_path}")
    print(f"Music     : {music_path}")
    print(f"Final WAV : {VOICE_WAV}")
    print(f"Final MP3 : {VOICE_MP3}")
    print("====================================")

    return VOICE_WAV


def generate_voice(text: str):
    text = clean_text(text)

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: voice script is empty"
        )

    narration = create_narration(text)
    chant = create_chant_audio()

    return str(create_final_audio(narration, chant))
