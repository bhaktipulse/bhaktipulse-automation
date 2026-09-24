import os
from pathlib import Path

import numpy as np
import soundfile as sf
from transformers import AutoModel


MODEL_ID = "ai4bharat/IndicF5"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_PATH = OUTPUT_DIR / "voice.wav"

REF_AUDIO = os.environ["INDICF5_REF_AUDIO"]
REF_TEXT = os.environ["INDICF5_REF_TEXT"]


_model = None


def get_model():
    global _model

    if _model is None:
        _model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True
        )

    return _model


def generate_voice(voice_script: str):
    if not voice_script.strip():
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: voice script is empty"
        )

    if not Path(REF_AUDIO).exists():
        raise RuntimeError(
            f"VOICE_GENERATION_FAILED: reference audio not found: {REF_AUDIO}"
        )

    model = get_model()

    audio = model(
        voice_script,
        ref_audio_path=REF_AUDIO,
        ref_text=REF_TEXT
    )

    if audio is None:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: model returned no audio"
        )

    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = np.asarray(audio, dtype=np.float32)

    if audio.size == 0:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: generated audio is empty"
        )

    sf.write(
        VOICE_PATH,
        audio,
        samplerate=24000
    )

    if VOICE_PATH.stat().st_size < 10_000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: audio file too small"
        )

    return str(VOICE_PATH)
