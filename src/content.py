import os
import json
import requests
from datetime import date

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

MODEL = "gemini-2.5-flash"


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
6. The deity/topic must be unambiguous because an exact matching
   visual will be generated later.
7. Prefer a short 15–25 second format.
8. Telugu should sound natural and conversational.
9. If using a mantra/sloka, use an authentic, commonly established text.
10. Do not make unsupported religious, historical or scientific claims.

TITLE:
- Maximum 60 characters including spaces.
- MUST contain both Telugu and English.
- Natural curiosity/question style.
- Must accurately match the topic.

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
- Keep it short enough for a Short.

IMAGE_PROMPT:
- Exact deity/festival/topic.
- Devotional Indian visual.
- Vertical 9:16 composition.
- No text.
- No watermark.
- No logos.
- Do not include another deity unless specifically required by the topic.

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

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={GEMINI_API_KEY}"
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
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        },
        timeout=90
    )

    response.raise_for_status()

    data = response.json()

    text = (
        data["candidates"][0]["content"]["parts"][0]["text"]
        .strip()
    )

    content = json.loads(text)

    validate_content(content)

    return content


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
                f"CONTENT_VALIDATION_FAILED: missing {key}"
            )

    title = content["title"].strip()

    if len(title) > 60:
        raise RuntimeError(
            f"CONTENT_VALIDATION_FAILED: title exceeds 60 characters ({len(title)})"
        )

    if not any("\u0C00" <= ch <= "\u0C7F" for ch in title):
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title has no Telugu"
        )

    english_present = any(
        ("A" <= ch <= "Z") or ("a" <= ch <= "z")
        for ch in title
    )

    if not english_present:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: title has no English"
        )

    if len(content["voice_script"].strip()) < 5:
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: voice script too short"
        )

    if not content["image_prompt"].strip():
        raise RuntimeError(
            "CONTENT_VALIDATION_FAILED: image prompt missing"
        )
