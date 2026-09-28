def normalize_title(title):
    title = " ".join(title.strip().split())

    if len(title) <= 60:
        return title

    # Remove trailing punctuation/spaces first.
    title = title.rstrip(" .?!")

    if len(title) <= 60:
        return title

    # Keep complete words and stay within 60 characters.
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
