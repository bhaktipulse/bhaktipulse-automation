import os
import base64
import time
import requests
from pathlib import Path


GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGE_PATH = OUTPUT_DIR / "devotional.png"


IMAGE_MODEL = "gemini-3.1-flash-image"


def generate_image(image_prompt: str):

    prompt = f"""
Create a high-quality devotional image for BhaktiPulse.

Follow the requested subject EXACTLY.

Requirements:
- Exact deity, festival or devotional subject requested.
- Do not substitute another deity.
- Traditional Indian devotional appearance.
- Respectful and spiritually appropriate.
- High-quality cinematic devotional artwork.
- Detailed face, hands, ornaments and clothing.
- Natural lighting.
- Beautiful devotional atmosphere.
- Clean composition suitable for YouTube Shorts.
- Vertical 9:16 composition.
- No text.
- No captions.
- No watermark.
- No logo.
- No border.

Requested subject:
{image_prompt}
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1/models/{IMAGE_MODEL}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": [
                "IMAGE"
            ],
            "responseFormat": {
                "image": {
                    "aspectRatio": "9:16",
                    "imageSize": "1K"
                }
            }
        }
    }

    last_error = None

    for attempt in range(3):

        print(
            f"Image generation attempt {attempt + 1}/3"
        )

        try:

            response = requests.post(
                url,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=180
            )

            if response.status_code == 429:

                print(
                    "Image API returned HTTP 429. "
                    "Waiting before retry..."
                )

                last_error = (
                    "HTTP 429: Too Many Requests"
                )

                if attempt < 2:
                    time.sleep(
                        20 * (attempt + 1)
                    )

                continue

            response.raise_for_status()

            data = response.json()

            candidates = data.get(
                "candidates",
                []
            )

            if not candidates:
                raise RuntimeError(
                    "IMAGE_GENERATION_FAILED: "
                    "no candidates returned"
                )

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            image_data = None

            for part in parts:

                inline_data = part.get(
                    "inlineData"
                )

                if inline_data:

                    image_data = inline_data.get(
                        "data"
                    )

                    if image_data:
                        break

            if not image_data:

                raise RuntimeError(
                    "IMAGE_GENERATION_FAILED: "
                    "no image data returned"
                )

            image_bytes = base64.b64decode(
                image_data
            )

            IMAGE_PATH.write_bytes(
                image_bytes
            )

            if IMAGE_PATH.stat().st_size < 10_000:

                raise RuntimeError(
                    "IMAGE_VALIDATION_FAILED: "
                    "image file too small"
                )

            print(
                "Gemini image generation succeeded"
            )

            print(
                f"Image saved: {IMAGE_PATH}"
            )

            return str(IMAGE_PATH)

        except Exception as error:

            last_error = str(error)

            print(
                f"Image generation failed: {error}"
            )

            if attempt < 2:
                time.sleep(
                    20 * (attempt + 1)
                )

    raise RuntimeError(
        "IMAGE_GENERATION_FAILED: "
        + str(last_error)
    )
