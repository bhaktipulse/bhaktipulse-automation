def create_final_audio(narration, chant):
    print("Using clean Telugu narration only...")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(narration),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=7",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(VOICE_WAV),
        ],
        "AUDIO_PROCESSING_FAILED",
    )

    validate_audio(
        VOICE_WAV,
        20000
    )

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(VOICE_WAV),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(VOICE_MP3),
        ],
        "VOICE_MP3_FAILED",
    )

    validate_audio(
        VOICE_MP3,
        5000
    )

    print("Clean Telugu narration created.")

    return str(VOICE_WAV)
