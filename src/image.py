import os
import requests
from pathlib import Path

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGE_PATH = OUTPUT_DIR / "devotional.png"


def generate_image(image_prompt: str):
    prompt = f"""
Create a high-quality devotional image for BhaktiPulse.

IMPORTANT:
- Follow the requested deity/festival/topic exactly.
- Do NOT substitute another deity.
- Traditional Indian devotional appearance.
- Respectful and spiritually appropriate.
- Photorealistic cinematic devotional artwork.
- Rich natural lighting.
- Detailed face, hands and ornaments.
- Clean composition.
- Vertical 9:16.
- No text.
- No captions.
- No watermark.
- No logo.
- No border.

Subject:
{image_prompt}
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.5-flash-image-preview:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    response = requests.post(
        url,
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        },
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError("IMAGE_GENERATION_FAILED: no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])

    for part in parts:
        inline_data = part.get("inlineData")

        if inline_data and inline_data.get("data"):
            image_bytes = __import__("base64").b64decode(
                inline_data["data"]
            )

            IMAGE_PATH.write_bytes(image_bytes)

            if IMAGE_PATH.stat().st_size < 10_000:
                raise RuntimeError(
                    "IMAGE_VALIDATION_FAILED: image file too small"
                )

            return str(IMAGE_PATH)

    raise RuntimeError(
        "IMAGE_GENERATION_FAILED: no image returned"
    )
