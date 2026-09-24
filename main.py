import sys
from datetime import date

from src.content import generate_content
from src.image import generate_image
from src.voice import generate_voice
from src.video import create_video
from src.youtube import schedule_video, tomorrow_0630_ist


def main():
    print("BHaktiPulse automation started")

    target_date = date.today().isoformat()

    # 1. Generate daily devotional content
    print("STEP 1: Generating content...")
    content = generate_content(target_date)

    print(f"TOPIC: {content['topic']}")
    print(f"DEITY: {content['deity']}")
    print(f"TITLE: {content['title']}")

    # 2. Generate exact devotional image
    print("STEP 2: Generating image...")
    image_path = generate_image(
        content["image_prompt"]
    )

    # 3. Generate Telugu voice
    print("STEP 3: Generating Telugu voice...")
    voice_path = generate_voice(
        content["voice_script"]
    )

    # 4. Create final 9:16 MP4
    print("STEP 4: Creating video...")
    video_path = create_video(
        image_path,
        voice_path
    )

    # 5. Schedule YouTube publication
    print("STEP 5: Scheduling YouTube...")
    publish_at = tomorrow_0630_ist()

    video_id = schedule_video(
        video_path=video_path,
        title=content["title"],
        description=content["description"],
        hashtags=content["hashtags"],
        publish_at=publish_at
    )

    print("")
    print("====================================")
    print("BHaktiPulse AUTOMATION SUCCESS")
    print("====================================")
    print(f"Video ID: {video_id}")
    print(f"Scheduled: {publish_at}")
    print("====================================")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("")
        print("====================================")
        print("BHaktiPulse AUTOMATION BLOCKED")
        print("====================================")
        print(str(error))
        print("====================================")
        sys.exit(1)
