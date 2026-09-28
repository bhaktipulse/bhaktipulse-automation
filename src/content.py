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

    title = " ".join(
        title.strip().split()
    )

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
You are the BhaktiPulse daily devotional Short planner.

Target date: {target_date}

Create ONE original Hindu devotional YouTube Short.

CORE REQUIREMENT:
The final Short must feel like a polished devotional social-media video,
not a static AI image with random narration.

DATE / FESTIVAL:
1. Check the target date for an important Hindu festival, vrat,
   jayanti, observance or spiritually relevant day.
2. If an important observance exists, it gets priority.
3. Never invent a festival.
4. Otherwise choose ONE useful devotional topic.

TOPIC:
Choose exactly ONE clear subject.

Possible topics:
- mantra
- sloka
- stotram
- deity significance
- devotional practice
- festival meaning
- traditional devotional knowledge
- chanting guidance

Do not combine unrelated subjects.

VOICE:
- Natural conversational Telugu.
- Suitable for a devotional Short.
- Warm, calm and human-sounding wording.
- Avoid robotic list-like sentences.
- Avoid excessive Sanskrit unless necessary.
- Do not make unsupported claims.
- 15–25 seconds.
- Use natural punctuation for breathing.
- Do not use emojis.
- Do not use stage directions.

ON-SCREEN TEXT:
Create 3–5 very short Telugu/English text cards.
They must summarize the actual topic.
They must NOT duplicate the entire voice script.
Each card should be readable on a mobile screen.

TITLE:
- Maximum 60 characters including spaces.
- Telugu + English.
- Curiosity/question style.
- Accurate to the topic.
- Prefer 50–55 characters.

DESCRIPTION:
- Topic-specific.
- Telugu + English.
- Natural SEO.
- No generic filler.

HASHTAGS:
Only relevant hashtags.

IMAGE:
- Exact deity/topic.
- Traditional Indian devotional appearance.
- Respectful.
- Vertical 9:16.
- No text.
- No watermark.
- No logo.
- No unrelated deity.
- No unrelated objects.

Return ONLY valid JSON:

{{
  "topic": "",
  "festival": "",
  "deity": "",
  "title": "",
  "description": "",
  "hashtags": [],
  "voice_script": "",
  "image_prompt": "",
  "text_cards": [
    "",
    "",
    ""
  ]
}}
"""

    last_error = None

    for model in MODELS:

        print(
            f"Trying Gemini model: {model}"
        )

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
            f"?key={GEMINI_API_KEY}"
        )

        for attempt in range(3):

            try:

                response = requests.post(
                    url,
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": prompt
                                    }
                                ]
                            }
                        ]
                    },
                    timeout=90
                )

                if response.status_code == 503:

                    last_error = (
                        f"{model}: HTTP 503"
                    )

                    print(
                        f"{model} returned HTTP 503 "
                        f"(attempt {attempt + 1}/3)"
                    )

                    if attempt < 2:

                        time.sleep(
                            2 ** attempt
                        )

                        continue

                    break

                if response.status_code != 200:

                    last_error = (
                        f"{model}: HTTP "
                        f"{response.status_code} "
                        f"{response.text[:500]}"
                    )

                    print(last_error)

                    break

                data = response.json()

                candidates = data.get(
                    "candidates",
                    []
                )

                if not candidates:

                    last_error = (
                        f"{model}: no candidates"
                    )

                    break

                parts = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [])
                )

                if not parts:

                    last_error = (
                        f"{model}: no response parts"
                    )

                    break

                text = parts[0].get(
                    "text",
                    ""
                ).strip()

                if not text:

                    last_error = (
                        f"{model}: empty response"
                    )

                    break

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
                    f"Gemini model succeeded: "
                    f"{model}"
                )

                return content

            except json.JSONDecodeError as error:

                last_error = (
                    f"{model}: invalid JSON: "
                    f"{error}"
                )

                break

            except Exception as error:

                last_error = (
                    f"{model}: {error}"
                )

                print(
                    f"{model} failed: {error}"
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
        "image_prompt",
        "text_cards",
    ]

    for key in required:

        if key not in content:

            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: "
                f"missing {key}"
            )

    for key in required:

        if not content[key]:

            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: "
                f"empty {key}"
            )

    content["title"] = normalize_title(
        content["title"]
    )

    title = content["title"]

    if len(title) > 60:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title exceeds 60 characters"
        )

    has_telugu = any(
        "\u0C00" <= ch <= "\u0C7F"
        for ch in title
    )

    if not has_telugu:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title has no Telugu"
        )

    has_english = any(
        ("A" <= ch <= "Z")
        or
        ("a" <= ch <= "z")
        for ch in title
    )

    if not has_english:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "title has no English"
        )

    voice = content[
        "voice_script"
    ].strip()

    if len(voice) < 20:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "voice script too short"
        )

    cards = content[
        "text_cards"
    ]

    if not isinstance(cards, list):

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "text_cards must be a list"
        )

    if not 3 <= len(cards) <= 5:

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "text_cards must contain 3–5 cards"
        )

    for card in cards:

        if not isinstance(card, str):

            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: "
                "text card must be text"
            )

        if not card.strip():

            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: "
                "empty text card"
            )

        if len(card.strip()) > 80:

            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: "
                "text card is too long"
            )

    if not content[
        "image_prompt"
    ].strip():

        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: "
            "image prompt missing"
        )
