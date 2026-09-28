import os
import json
import time
import requests


GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]


def normalize_title(title):

    title = " ".join(title.strip().split())

    if len(title) <= 60:
        return title

    title = title.rstrip(" .?!")

    if len(title) <= 60:
        return title

    words = title.split()

    result = ""

    for word in words:

        candidate = (
            word
            if not result
            else result + " " + word
        )

        if len(candidate) <= 60:
            result = candidate
        else:
            break

    if not result:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title cannot be reduced to 60 characters"
        )

    return result


def generate_content(target_date: str):

    prompt = f"""
You are the BhaktiPulse daily devotional content planner.

Target date: {target_date}

Create ONE original devotional YouTube Short for this date.

Rules:

1. Check the date for an important Hindu festival, vrat, jayanti,
   observance or spiritually relevant day.

2. If an important observance exists, it gets priority.

3. Otherwise choose ONE useful devotional topic:
   mantra, sloka, stotram, ashtakam, chanting, deity fact,
   devotional practice or spiritual insight.

4. Do not invent a festival.

5. Do not repeat a recent topic if recent topics are supplied.

6. The deity/topic must be completely unambiguous because an exact
   matching visual will be generated later.

7. Prefer a short 15–25 second format.

8. Telugu must sound natural and understandable.

9. If using a mantra/sloka, use an authentic and commonly established text.

10. Do not make unsupported religious, historical or scientific claims.

TITLE:
- Maximum 60 characters including spaces.
- MUST contain both Telugu and English.
- Natural curiosity/question style.
- Must accurately match the topic.
- Keep it safely below 60 characters, preferably 50–55 characters.

DESCRIPTION:
- Topic-specific.
- Telugu + English naturally.
- Useful devotional context.
- Natural SEO keywords.
- No generic filler.

HASHTAGS:
- Only relevant to the actual topic.

VOICE_SCRIPT:
- Natural Telugu.
- Suitable for devotional narration or chanting.
- No emojis.
- No stage directions.
- Keep it short enough for a YouTube Short.

IMAGE_PROMPT:
- Exact deity/festival/topic.
- Devotional Indian visual.
- Vertical 9:16 composition.
- No text.
- No watermark.
- No logos.
- Do not include another deity unless specifically required.

Return ONLY valid JSON:

{{
  "topic": "",
  "festival": "",
  "deity": "",
  "title": "",
  "description": "",
  "hashtags": [],
  "voice_script": "",
  "image_prompt": ""
}}
"""

    last_error = None

    for model in MODELS:

        print(f"Trying Gemini model: {model}")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )

        for attempt in range(3):

            try:

                response = requests.post(
                    url,
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {"text": prompt}
                                ]
                            }
                        ]
                    },
                    timeout=90
                )

                if response.status_code == 503:

                    print(
                        f"Model {model} returned HTTP 503 "
                        f"(attempt {attempt + 1}/3)"
                    )

                    last_error = (
                        f"{model}: HTTP 503 "
                        f"{response.text[:500]}"
                    )

                    if attempt < 2:
                        wait_seconds = 2 ** attempt
                        print(
                            f"Retrying {model} in "
                            f"{wait_seconds} seconds..."
                        )
                        time.sleep(wait_seconds)
                        continue

                    print(
                        f"Model {model} unavailable after "
                        "3 attempts."
                    )

                    break

                if response.status_code != 200:

                    print(
                        f"Model {model} failed: "
                        f"HTTP {response.status_code}"
                    )

                    last_error = (
                        f"{model}: HTTP {response.status_code} "
                        f"{response.text[:500]}"
                    )

                    break

                data = response.json()

                candidates = data.get(
                    "candidates",
                    []
                )

                if not candidates:

                    last_error = (
                        f"{model}: no candidates returned"
                    )

                    print(last_error)

                    break

                parts = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [])
                )

                if not parts:

                    last_error = (
                        f"{model}: "
                        "no response parts returned"
                    )

                    print(last_error)

                    break

                text = parts[0].get(
                    "text",
                    ""
                ).strip()

                if not text:

                    last_error = (
                        f"{model}: empty response"
                    )

                    print(last_error)

                    break

                # Remove accidental markdown JSON fences.
                if text.startswith("```"):

                    text = text.replace(
                        "```json",
                        "",
                        1
                    )

                    text = text.replace(
                        "```",
                        "",
                        1
                    )

                    text = text.strip()

                content = json.loads(text)

                validate_content(content)

                print(
                    f"Gemini model succeeded: {model}"
                )

                return content

            except json.JSONDecodeError as error:

                last_error = (
                    f"{model}: invalid JSON: {error}"
                )

                print(last_error)

                break

            except Exception as error:

                last_error = (
                    f"{model}: {error}"
                )

                print(
                    f"Model {model} failed: {error}"
                )

                break

    raise RuntimeError(
        "ALL_GEMINI_MODELS_FAILED: "
        + str(last_error)
    )


def validate_content(content):

    required = [
        "topic",
        "deity",
        "title",
        "description",
        "hashtags",
        "voice_script",
        "image_prompt"
    ]

    for key in required:

        if key not in content or not content[key]:

            raise RuntimeError(
                f"CONTENT_VALIDATION_FAILED: "
                f"missing {key}"
            )

    title = normalize_title(
        content["title"]
    )

    content["title"] = title

    if len(title) > 60:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            f"title exceeds 60 characters ({len(title)})"
        )

    if not any(
        "\u0C00" <= ch <= "\u0C7F"
        for ch in title
    ):

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title has no Telugu"
        )

    english_present = any(
        ("A" <= ch <= "Z")
        or
        ("a" <= ch <= "z")
        for ch in title
    )

    if not english_present:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title has no English"
        )

    if len(
        content["voice_script"].strip()
    ) < 5:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "voice script too short"
        )

    if not content[
        "image_prompt"
    ].strip():

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "image prompt missing"
        )
