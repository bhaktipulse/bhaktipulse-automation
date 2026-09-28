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
    infer_process,
    preprocess_ref_audio_text,
)

from vocos import Vocos


MODEL_REPO = "ai4bharat/IndicF5"
VOCOS_REPO = "charactr/vocos-mel-24khz"

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


def load_vocos_fixed(device):

    print("Loading Vocos vocoder with meta-tensor fix...")

    config_path = hf_hub_download(
        repo_id=VOCOS_REPO,
        filename="config.yaml",
        token=HF_TOKEN
    )

    model_path = hf_hub_download(
        repo_id=VOCOS_REPO,
        filename="pytorch_model.bin",
        token=HF_TOKEN
    )

    vocoder = Vocos.from_hparams(
        config_path
    )

    # IndicF5 / Vocos can initialize parameters
    # on the meta device. Materialize them before
    # loading the actual weights.
    if any(
        parameter.is_meta
        for parameter in vocoder.parameters()
    ):
        print(
            "Vocos contains meta tensors. "
            "Materializing on CPU..."
        )

        vocoder = vocoder.to_empty(
            device="cpu"
        )

    state_dict = torch.load(
        model_path,
        map_location="cpu",
        weights_only=True
    )

    vocoder.load_state_dict(
        state_dict
    )

    vocoder = vocoder.to(
        device
    )

    vocoder.eval()

    print(
        "Vocos loaded successfully"
    )

    return vocoder


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

    # -------------------------------------------------
    # Vocos
    # -------------------------------------------------

    _vocoder = load_vocos_fixed(
        device
    )

    # -------------------------------------------------
    # IndicF5 model
    # -------------------------------------------------

    print(
        "Loading IndicF5 model architecture..."
    )

    model_config = {
        "dim": 1024,
        "depth": 22,
        "heads": 16,
        "ff_mult": 2,
        "text_dim": 512,
        "conv_layers": 4
    }

    print(
        "Loading IndicF5 checkpoint..."
    )

    # Current F5-TTS load_model() requires
    # ckpt_path as the third positional argument.
    _model = load_model(
        DiT,
        model_config,
        ckpt_path,
        mel_spec_type="vocos",
        vocab_file=vocab_path,
        device=device
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

    ref_audio, ref_text = (
        preprocess_ref_audio_text(
            str(REF_AUDIO),
            REF_TEXT
        )
    )

    print(
        "Generating Telugu voice..."
    )

    with torch.inference_mode():

        audio, sample_rate, _ = infer_process(
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

    if sample_rate is None:
        sample_rate = 24000

    sf.write(
        VOICE_PATH,
        audio,
        samplerate=sample_rate
    )

    if not VOICE_PATH.exists():
        raise RuntimeError(
            "VOICE_VALIDATION_FAILED: "
            "voice.wav was not created"
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
