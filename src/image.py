import os
import base64
import time
import requests
from pathlib import Path


GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGE_PATH = OUTPUT_DIR / "devotional.png"


# Try image models in this order.
IMAGE_MODELS = [
    "gemini-3.1-flash-image",
    "gemini-3.0-flash-image",
]


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

    last_error = None

    for model in IMAGE_MODELS:

        print(f"Trying image model: {model}")

        for attempt in range(3):

            try:

                print(
                    f"Image attempt {attempt + 1}/3"
                )

                url = (
                    "https://generativelanguage.googleapis.com/"
                    "v1beta/interactions"
                )

                response = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": GEMINI_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "input": prompt,
                        "response_format": {
                            "type": "image",
                            "aspect_ratio": "9:16",
                            "image_size": "1K"
                        }
                    },
                    timeout=180
                )

                if response.status_code == 429:

                    print(
                        f"Image model {model}: "
                        "HTTP 429 - retrying..."
                    )

                    time.sleep(
                        15 * (attempt + 1)
                    )

                    continue

                response.raise_for_status()

                data = response.json()

                output_image = data.get(
                    "output_image"
                )

                if not output_image:

                    raise RuntimeError(
                        "IMAGE_GENERATION_FAILED: "
                        "no output image returned"
                    )

                image_data = output_image.get(
                    "data"
                )

                if not image_data:

                    raise RuntimeError(
                        "IMAGE_GENERATION_FAILED: "
                        "image data missing"
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
                    f"Image model succeeded: {model}"
                )

                return str(IMAGE_PATH)

            except Exception as error:

                last_error = (
                    f"{model}, attempt "
                    f"{attempt + 1}: {error}"
                )

                print(last_error)

                if attempt < 2:
                    time.sleep(
                        15 * (attempt + 1)
                    )

        print(
            f"Image model failed completely: {model}"
        )

    raise RuntimeError(
        "ALL_IMAGE_MODELS_FAILED: "
        + str(last_error)
    )
