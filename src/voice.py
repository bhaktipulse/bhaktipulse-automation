
import asyncio
from pathlib import Path

import edge_tts
from pydub import AudioSegment

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_MP3 = OUTPUT_DIR / "voice.mp3"
VOICE_WAV = OUTPUT_DIR / "voice.wav"

VOICE = "te-IN-ShrikantNeural"


async def _speak(text: str):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="-8%",
        pitch="+0Hz",
    )
    await communicate.save(str(VOICE_MP3))


def generate_voice(text: str):

    print("Generating Telugu voice with Edge Neural...")

    asyncio.run(_speak(text))

    audio = AudioSegment.from_mp3(VOICE_MP3)
    audio = audio.set_frame_rate(48000).set_channels(1)

    audio.export(VOICE_WAV, format="wav")

    print(f"Voice created: {VOICE_WAV}")

    return str(VOICE_WAV)
