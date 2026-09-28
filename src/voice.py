import asyncio
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_PATH = OUTPUT_DIR / "voice.wav"

VOICE = "te-IN-ShrikantNeural"


async def _tts(text: str):
    mp3 = OUTPUT_DIR / "voice.mp3"

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="-8%",
        pitch="+0Hz",
    )

    await communicate.save(str(mp3))

    return mp3


def generate_voice(text: str):

    print("Generating Telugu voice with Edge Neural...")

    mp3 = asyncio.run(_tts(text))

    from pydub import AudioSegment

    audio = AudioSegment.from_mp3(mp3)
    audio = audio.set_frame_rate(48000).set_channels(1)

    audio.export(
        VOICE_PATH,
        format="wav",
    )

    print(f"Voice created: {VOICE_PATH}")

    return str(VOICE_PATH)
