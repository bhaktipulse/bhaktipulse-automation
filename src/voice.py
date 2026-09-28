from pathlib import Path

from gtts import gTTS
from pydub import AudioSegment


OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_MP3 = OUTPUT_DIR / "voice.mp3"
VOICE_WAV = OUTPUT_DIR / "voice.wav"


def generate_voice(text: str):

    text = " ".join(
        text.strip().split()
    )

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: "
            "voice script is empty"
        )

    print(
        "Generating Telugu voice with Google TTS..."
    )

    try:

        tts = gTTS(
            text=text,
            lang="te",
            slow=False,
        )

        tts.save(
            str(VOICE_MP3)
        )

    except Exception as error:

        raise RuntimeError(
            "VOICE_GENERATION_FAILED: "
            + str(error)
        )

    if not VOICE_MP3.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "MP3 was not created"
        )

    if VOICE_MP3.stat().st_size < 5_000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "MP3 file is too small"
        )

    try:

        audio = AudioSegment.from_mp3(
            VOICE_MP3
        )

        audio = (
            audio
            .set_frame_rate(48000)
            .set_channels(1)
        )

        audio.export(
            VOICE_WAV,
            format="wav"
        )

    except Exception as error:

        raise RuntimeError(
            "VOICE_CONVERSION_FAILED: "
            + str(error)
        )

    if not VOICE_WAV.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "WAV was not created"
        )

    if VOICE_WAV.stat().st_size < 10_000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "WAV file is too small"
        )

    duration = (
        len(audio) / 1000.0
    )

    print(
        f"Telugu voice created successfully: "
        f"{VOICE_WAV}"
    )

    print(
        f"Voice duration: "
        f"{duration:.2f} seconds"
    )

    return str(VOICE_WAV)
