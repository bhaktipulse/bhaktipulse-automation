import os
from pathlib import Path

from huggingface_hub import InferenceClient


HF_TOKEN = os.environ["HF_TOKEN"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGE_PATH = OUTPUT_DIR / "devotional.png"

MODEL = "black-forest-labs/FLUX.1-schnell"


def generate_image(image_prompt: str):

    if not image_prompt.strip():
        raise RuntimeError(
            "IMAGE_GENERATION_FAILED: image prompt is empty"
        )

    prompt = f"""
Create a high-quality Indian devotional artwork.

IMPORTANT:
Follow the requested deity or devotional subject EXACTLY.

Requirements:
- Exact requested deity/topic.
- Traditional Indian devotional appearance.
- Respectful spiritual presentation.
- Detailed face, hands, ornaments and clothing.
- Beautiful devotional lighting.
- Rich but natural colors.
- Cinematic devotional artwork.
- Clean composition.
- Designed for a vertical YouTube Short.
- 9:16 portrait composition.
- No text.
- No letters.
- No captions.
- No watermark.
- No logo.
- No border.
- No extra deity.
- No unrelated objects.

Requested subject:
{image_prompt}
"""

    print(
        f"Generating image with Hugging Face: {MODEL}"
    )

    try:

        client = InferenceClient(
            api_key=HF_TOKEN
        )

        image = client.text_to_image(
            prompt=prompt,
            model=MODEL
        )

        if image is None:
            raise RuntimeError(
                "IMAGE_GENERATION_FAILED: "
                "no image returned"
            )

        image.save(IMAGE_PATH)

    except Exception as error:

        raise RuntimeError(
            "IMAGE_GENERATION_FAILED: "
            + str(error)
        )

    if not IMAGE_PATH.exists():
        raise RuntimeError(
            "IMAGE_VALIDATION_FAILED: "
            "image file was not created"
        )

    if IMAGE_PATH.stat().st_size < 10_000:
        raise RuntimeError(
            "IMAGE_VALIDATION_FAILED: "
            "image file is too small"
        )

    print(
        f"Image generated successfully: {IMAGE_PATH}"
    )

    return str(IMAGE_PATH)
