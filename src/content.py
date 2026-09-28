import json
import os
import re
import time
from datetime import datetime, timezone

import requests


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured"
    )


MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]


API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


def clean_text(value):
    return " ".join(
        str(value).strip().split()
    )


def validate_telugu_voice_script(text):
    text = clean_text(text)

    if not text:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script is empty"
        )

    # Must contain Telugu.
    if not re.search(r"[\u0C00-\u0C7F]", text):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script has no Telugu text"
        )

    # Prevent unnatural excessive punctuation.
    if "..." in text:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script contains artificial pauses"
        )

    # Prevent repeated punctuation.
    if re.search(r"[!?.,]{3,}", text):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script contains excessive punctuation"
        )

    # Do not allow spaces around punctuation.
    if re.search(r"\s+[,.!?;:]", text):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script has spaces before punctuation"
        )

    # Natural mantra phrase must stay intact.
    mantra_variants = [
        "ఓం నమః శివాయ",
        "ఓం నమః శివాయ.",
        "ఓం నమః శివాయ!",
        "ఓం నమః శివాయ?",
    ]

    if "ఓం" in text and "నమః" in text and "శివాయ" in text:
        if not re.search(
            r"ఓం\s+నమః\s+శివాయ",
            text
        ):
            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: Om Namah Shivaya phrase was split unnaturally"
            )

    # No accidental hyphenation inside Telugu phrases.
    if re.search(
        r"[\u0C00-\u0C7F]\s*[-–—]\s*[\u0C00-\u0C7F]",
        text
    ):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: Telugu phrase contains artificial hyphen"
        )

    # Voice script should be short enough for a Short.
    words = text.split()

    if len(words) < 8:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script is too short"
        )

    if len(words) > 75:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice_script is too long"
        )

    return text


def validate_content(data):
    required_fields = [
        "topic",
        "festival",
        "deity",
        "title",
        "description",
        "hashtags",
        "voice_script",
        "image_prompt",
        "text_cards",
    ]

    for field in required_fields:
        if field not in data:
            raise RuntimeError(
                f"CONTENT_VALIDATION_FAILED: missing field: {field}"
            )

    topic = clean_text(data["topic"])
    festival = clean_text(data["festival"])
    deity = clean_text(data["deity"])
    title = clean_text(data["title"])
    description = clean_text(data["description"])
    hashtags = clean_text(data["hashtags"])
    image_prompt = clean_text(data["image_prompt"])

    voice_script = validate_telugu_voice_script(
        data["voice_script"]
    )

    text_cards = data["text_cards"]

    if not topic:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: topic is empty"
        )

    if not deity:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: deity is empty"
        )

    if not title:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title is empty"
        )

    if len(title) > 60:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title exceeds 60 characters"
        )

    # Require Telugu + English in title.
    if not re.search(
        r"[\u0C00-\u0C7F]",
        title
    ):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title must contain Telugu"
        )

    if not re.search(
        r"[A-Za-z]",
        title
    ):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title must contain English"
        )

    if not description:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: description is empty"
        )

    if not hashtags:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: hashtags are empty"
        )

    if not image_prompt:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: image_prompt is empty"
        )

    if not isinstance(
        text_cards,
        list
    ):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: text_cards must be a list"
        )

    if not 3 <= len(text_cards) <= 5:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: text_cards must contain 3-5 cards"
        )

    cleaned_cards = []

    for card in text_cards:
        card = clean_text(card)

        if not card:
            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: empty text card"
            )

        if len(card) > 80:
            raise RuntimeError(
                "CONTENT_VALIDATION_FAILED: text card exceeds 80 characters"
            )

        cleaned_cards.append(card)

    data["topic"] = topic
    data["festival"] = festival
    data["deity"] = deity
    data["title"] = title
    data["description"] = description
    data["hashtags"] = hashtags
    data["voice_script"] = voice_script
    data["image_prompt"] = image_prompt
    data["text_cards"] = cleaned_cards

    return data


def build_prompt(target_date):
    return f"""
You are the content director for BhaktiPulse devotional YouTube Shorts.

TARGET DATE:
{target_date}

Create ONE accurate devotional Short for this exact date.

IMPORTANT:
First determine the most relevant devotional topic, deity, mantra,
festival, observance, or spiritually meaningful subject for the target date.

Do NOT randomly choose a deity when an important festival or observance
exists for that date.

Do NOT invent festival facts.

If there is no major festival, choose ONE suitable devotional topic
for the day.

The final content must be respectful, natural, concise and suitable
for an Indian devotional audience.

==================================================
VOICE SCRIPT — VERY IMPORTANT
==================================================

The voice_script will be converted directly into Telugu speech using
a Telugu neural TTS voice.

Write it as a HUMAN SPEAKING naturally.

The most important requirement is NATURAL WORD FLOW.

Do NOT write the script like a list.

Do NOT separate words that naturally belong together.

Do NOT put commas between every word.

Do NOT put punctuation between words of a single phrase.

Do NOT use artificial pauses.

Do NOT use ellipses.

Do NOT use hyphens to separate Telugu words.

Use a normal space between words that belong to one phrase.

Use commas ONLY where a real short speaking pause is natural.

Use a full stop ONLY at a real sentence boundary.

==================================================
MANTRA RULE
==================================================

If the selected topic includes a mantra such as:

ఓం నమః శివాయ

treat the COMPLETE phrase as ONE continuous spoken mantra.

Write:

ఓం నమః శివాయ

Do NOT write:

ఓం, నమః, శివాయ

Do NOT write:

ఓం. నమః. శివాయ.

Do NOT write:

ఓం — నమః — శివాయ

Do NOT put punctuation between the three words.

The mantra must be spoken as one natural phrase.

If the mantra appears in the voice_script, it should normally appear
as one complete phrase, not as separated sentence fragments.

==================================================
TELUGU NATURALNESS
==================================================

Use simple natural Telugu.

Avoid overly literary or difficult Telugu.

Avoid unnatural machine-translation wording.

Avoid English words unless genuinely useful.

Do not create unnecessary pauses before or after short words.

Do not break compound expressions unnecessarily.

The listener should feel that a Telugu speaker is speaking naturally,
not reading isolated words.

Target voice length:
approximately 15–25 seconds.

==================================================
TEXT CARDS
==================================================

Create 3–5 short on-screen text cards.

Cards must support the voice script.

Do not split a natural Telugu phrase into unnatural word fragments.

Each card must be short and readable on a vertical mobile video.

==================================================
TITLE
==================================================

Create one title.

Maximum 60 characters.

Must contain Telugu + English.

Use curiosity/question style where natural.

Do not use fake claims.

Do not use excessive emojis.

==================================================
DESCRIPTION
==================================================

Create a short natural Telugu + English description.

Keep it topic-specific.

Do not stuff keywords.

==================================================
HASHTAGS
==================================================

Create relevant devotional hashtags.

Do not use unrelated trending hashtags.

==================================================
IMAGE
==================================================

Create an exact image_prompt for the selected topic/deity.

The image must show the requested deity/topic accurately.

No unrelated deity.

No extra deity.

No text.

No watermark.

No logo.

No captions.

Vertical 9:16 devotional composition.

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

Use exactly these fields:

{{
  "topic": "",
  "festival": "",
  "deity": "",
  "title": "",
  "description": "",
  "hashtags": "",
  "voice_script": "",
  "image_prompt": "",
  "text_cards": [
    "",
    "",
    ""
  ]
}}

No markdown.
No explanation outside JSON.
"""


def call_gemini(model, prompt):
    url = API_URL.format(
        model=model
    )

    params = {
        "key": GEMINI_API_KEY
    }

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
            "temperature": 0.35,
            "topP": 0.85,
            "responseMimeType": "application/json"
        }
    }

    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"GEMINI_HTTP_{response.status_code}: "
            + response.text[:2000]
        )

    data = response.json()

    try:
        text = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
    except Exception:
        raise RuntimeError(
            "GEMINI_RESPONSE_FAILED: no usable response"
        )

    return text


def parse_json_response(text):
    text = text.strip()

    # Remove accidental markdown fences if model returns them.
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        print("Invalid Gemini response:")
        print(text)

        raise RuntimeError(
            "GEMINI_JSON_FAILED: " +
            str(error)
        )


def generate_content(target_date):
    prompt = build_prompt(
        target_date
    )

    last_error = None

    for model in MODELS:
        print(
            f"Generating content with Gemini model: {model}"
        )

        for attempt in range(3):
            try:
                response_text = call_gemini(
                    model,
                    prompt
                )

                data = parse_json_response(
                    response_text
                )

                data = validate_content(
                    data
                )

                print(
                    "Content generated and validated successfully."
                )

                print(
                    "VOICE SCRIPT:"
                )
                print(
                    data["voice_script"]
                )

                return data

            except Exception as error:
                last_error = error

                print(
                    f"Gemini attempt {attempt + 1}/3 failed:"
                )
                print(
                    str(error)
                )

                # Retry temporary server/API errors.
                if (
                    "503" in str(error)
                    or "429" in str(error)
                    or "500" in str(error)
                    or "502" in str(error)
                    or "504" in str(error)
                ):
                    time.sleep(
                        5 * (attempt + 1)
                    )
                    continue

                # Content/validation errors should try
                # the next model rather than looping forever.
                break

    raise RuntimeError(
        "CONTENT_GENERATION_FAILED: "
        + str(last_error)
    )
