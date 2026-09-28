import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_model,
    load_vocoder,
    infer_process,
    preprocess_ref_audio_text,
)


MODEL_REPO = "ai4bharat/IndicF5"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE_PATH = OUTPUT_DIR / "voice.wav"

REF_AUDIO = Path(
    "assets/voice/telugu_reference.wav"
)

REF_TEXT = os.environ["INDICF5_REF_TEXT"]

HF_TOKEN = os.environ["HF_TOKEN"]

_model = None
_vocoder = None


def get_device():
    if torch.cuda.is_available():
        return "cuda"

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    return "cpu"


def load_indicf5():

    global _model
    global _vocoder

    if _model is not None:
        return _model, _vocoder

    device = get_device()

    print(
        f"IndicF5 device: {device}"
    )

    print(
        "Downloading IndicF5 model files..."
    )

    vocab_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename="checkpoints/vocab.txt",
        token=HF_TOKEN
    )

    ckpt_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename="model.safetensors",
        token=HF_TOKEN
    )

    print(
        "Loading Vocos vocoder..."
    )

    _vocoder = load_vocoder(
        vocoder_name="vocos",
        is_local=False,
        device=device
    )

    print(
        "Loading IndicF5 model architecture..."
    )

    _model = load_model(
        DiT,
        dict(
            dim=1024,
            depth=22,
            heads=16,
            ff_mult=2,
            text_dim=512,
            conv_layers=4
        ),
        mel_spec_type="vocos",
        vocab_file=vocab_path,
        device=device
    )

    print(
        "Loading IndicF5 checkpoint weights..."
    )

    state_dict = load_file(
        ckpt_path,
        device=device
    )

    state_dict = {
        key.replace(
            "ema_model._orig_mod.",
            ""
        ): value
        for key, value in state_dict.items()
        if key.startswith("ema_model.")
    }

    if not state_dict:
        raise RuntimeError(
            "VOICE_MODEL_LOAD_FAILED: "
            "No ema_model weights found in checkpoint"
        )

    _model.load_state_dict(
        state_dict
    )

    _model.eval()

    print(
        "IndicF5 model loaded successfully"
    )

    return _model, _vocoder


def generate_voice(voice_script: str):

    if not voice_script.strip():
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: "
            "voice script is empty"
        )

    if not REF_AUDIO.exists():
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: "
            f"reference audio not found: {REF_AUDIO}"
        )

    model, vocoder = load_indicf5()

    device = get_device()

    print(
        "Preparing Telugu reference audio..."
    )

    ref_audio, ref_text = preprocess_ref_audio_text(
        str(REF_AUDIO),
        REF_TEXT
    )

    print(
        "Generating Telugu voice..."
    )

    with torch.inference_mode():

        audio, _, _ = infer_process(
            ref_audio,
            ref_text,
            voice_script,
            model,
            vocoder,
            mel_spec_type="vocos",
            device=device
        )

    if audio is None:
        raise RuntimeError(
            "VOICE_GENERATION_FAILED: "
            "no audio returned"
        )

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    if audio.size == 0:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "generated audio is empty"
        )

    sf.write(
        VOICE_PATH,
        audio,
        samplerate=24000
    )

    if VOICE_PATH.stat().st_size < 10_000:
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "audio file too small"
        )

    print(
        "Telugu voice generated successfully: "
        f"{VOICE_PATH}"
    )

    return str(VOICE_PATH)
