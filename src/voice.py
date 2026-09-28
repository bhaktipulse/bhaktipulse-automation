from pathlib import Path
from gtts import gTTS
from pydub import AudioSegment

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_MP3 = OUTPUT_DIR / "voice.mp3"
VOICE_WAV = OUTPUT_DIR / "voice.wav"

NARRATION_MP3 = OUTPUT_DIR / "narration.mp3"
NARRATION_WAV = OUTPUT_DIR / "narration.wav"

CHANT_MP3 = OUTPUT_DIR / "chant.mp3"
CHANT_WAV = OUTPUT_DIR / "chant.wav"

FINAL_AUDIO_WAV = OUTPUT_DIR / "final_voice.wav"


def clean_text(text):
    return " ".join(str(text).strip().split())


def create_tts(text, output_path):
    text = clean_text(text)

    if not text:
        raise RuntimeError("VOICE_GENERATION_FAILED: empty text")

    try:
        tts = gTTS(
            text=text,
            lang="te",
            slow=False
        )
        tts.save(str(output_path))
    except Exception as error:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: " + str(error)
        )

    if not output_path.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: audio was not created"
        )

    if output_path.stat().st_size < 3000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: audio file is too small"
        )


def convert_to_wav(mp3_path, wav_path):
    try:
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_frame_rate(48000).set_channels(1)
        audio.export(wav_path, format="wav")
    except Exception as error:
        raise RuntimeError(
            "VOICE_CONVERSION_FAILED: " + str(error)
        )

    if not wav_path.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: WAV was not created"
        )

    if wav_path.stat().st_size < 10000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: WAV file is too small"
        )

    return audio


def create_chant_audio():
    """
    Creates a separate mantra track.
    The mantra is intentionally short so it can be mixed
    naturally into a devotional Short.
    """

    chant_text = (
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ. "
        "ఓం నమః శివాయ."
    )

    print("Generating separate Shiva mantra chanting...")

    create_tts(
        chant_text,
        CHANT_MP3
    )

    convert_to_wav(
        CHANT_MP3,
        CHANT_WAV
    )

    chant = AudioSegment.from_wav(CHANT_WAV)

    # Small fade-in/out makes the chanting transition smoother.
    chant = chant.fade_in(250).fade_out(500)

    # Keep chanting slightly shorter if unexpectedly long.
    if len(chant) > 9000:
        chant = chant[:9000].fade_out(700)

    chant.export(
        CHANT_WAV,
        format="wav"
    )

    print(
        f"Mantra chanting created: {CHANT_WAV} "
        f"({len(chant) / 1000:.2f}s)"
    )

    return chant


def create_final_audio(narration, chant):
    """
    Structure:

    narration
    ↓
    short pause
    ↓
    mantra chanting
    ↓
    short pause

    The chant is intentionally lower than narration.
    """

    pause_before = AudioSegment.silent(
        duration=500
    )

    pause_after = AudioSegment.silent(
        duration=350
    )

    # Slightly reduce chant loudness so it does not sound harsh.
    chant = chant - 2

    final_audio = (
        narration
        + pause_before
        + chant
        + pause_after
    )

    final_audio = (
        final_audio
        .set_frame_rate(48000)
        .set_channels(1)
    )

    final_audio.export(
        FINAL_AUDIO_WAV,
        format="wav"
    )

    if not FINAL_AUDIO_WAV.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: final audio missing"
        )

    if FINAL_AUDIO_WAV.stat().st_size < 20000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: final audio too small"
        )

    duration = len(final_audio) / 1000.0

    print(
        f"Final devotional audio created: "
        f"{FINAL_AUDIO_WAV}"
    )
    print(
        f"Final audio duration: {duration:.2f} seconds"
    )

    return str(FINAL_AUDIO_WAV)


def generate_voice(text: str):
    text = clean_text(text)

    if not text:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: voice script is empty"
        )

    print("Generating Telugu narration with Google TTS...")

    # -------------------------------------------------
    # 1. Narration
    # -------------------------------------------------

    create_tts(
        text,
        NARRATION_MP3
    )

    narration = convert_to_wav(
        NARRATION_MP3,
        NARRATION_WAV
    )

    print(
        f"Narration duration: "
        f"{len(narration) / 1000:.2f}s"
    )

    # -------------------------------------------------
    # 2. Separate mantra chanting
    # -------------------------------------------------

    chant = create_chant_audio()

    # -------------------------------------------------
    # 3. Combine narration + chanting
    # -------------------------------------------------

    final_audio = create_final_audio(
        narration,
        chant
    )

    # -------------------------------------------------
    # 4. Keep compatibility with existing pipeline
    # -------------------------------------------------

    # Existing video.py expects output/voice.wav.
    final_path = Path(final_audio)

    final_path.replace(VOICE_WAV)

    if not VOICE_WAV.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: voice.wav missing"
        )

    # Re-create a compatibility MP3 from final WAV.
    try:
        final_audio_segment = AudioSegment.from_wav(
            VOICE_WAV
        )
        final_audio_segment.export(
            VOICE_MP3,
            format="mp3",
            bitrate="192k"
        )
    except Exception as error:
        raise RuntimeError(
            "VOICE_MP3_CREATION_FAILED: " + str(error)
        )

    print("")
    print("====================================")
    print("Telugu narration + mantra audio ready")
    print("====================================")
    print(f"Narration: {NARRATION_WAV}")
    print(f"Chanting:  {CHANT_WAV}")
    print(f"Final:     {VOICE_WAV}")
    print("====================================")

    return str(VOICE_WAV)
