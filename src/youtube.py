import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

VIDEO_CATEGORY_ID = "22"


def get_youtube_service():
    token = os.environ["YOUTUBE_TOKEN_JSON"]

    credentials = Credentials.from_authorized_user_info(
        __import__("json").loads(token),
        SCOPES
    )

    return build(
        "youtube",
        "v3",
        credentials=credentials
    )


def schedule_video(
    video_path: str,
    title: str,
    description: str,
    hashtags: list,
    publish_at: str
):
    video_file = Path(video_path)

    if not video_file.exists():
        raise RuntimeError(
            "YOUTUBE_UPLOAD_FAILED: video file not found"
        )

    if len(title.strip()) > 60:
        raise RuntimeError(
            "YOUTUBE_UPLOAD_FAILED: title exceeds 60 characters"
        )

    tags = [
        str(tag).lstrip("#").strip()
        for tag in hashtags
        if str(tag).strip()
    ]

    body = {
        "snippet": {
            "title": title.strip(),
            "description": description.strip(),
            "tags": tags,
            "categoryId": VIDEO_CATEGORY_ID
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True
        }
    }

    youtube = get_youtube_service()

    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            print(
                f"YouTube upload: "
                f"{int(status.progress() * 100)}%"
            )

    if not response.get("id"):
        raise RuntimeError(
            "YOUTUBE_UPLOAD_FAILED: no video ID returned"
        )

    video_id = response["id"]

    print(
        f"YOUTUBE_SCHEDULED: "
        f"https://www.youtube.com/watch?v={video_id}"
    )

    return video_id


def tomorrow_0630_ist():
    ist = timezone(timedelta(hours=5, minutes=30))

    now = datetime.now(ist)

    tomorrow = now.date() + timedelta(days=1)

    publish_time = datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        6,
        30,
        0,
        tzinfo=ist
    )

    return publish_time.isoformat()
