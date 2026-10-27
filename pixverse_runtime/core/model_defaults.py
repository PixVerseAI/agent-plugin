"""Plugin creative defaults, independent of the upstream CLI's own defaults."""

IMAGE_MODEL = "gpt-image-2.5-sunburst"
IMAGE_QUALITY = "1440p"
IMAGE_DETAIL = "high"
VIDEO_MODEL = "seedance-2.5"
VIDEO_QUALITY = "1080p"
FALLBACK_IMAGE_MODEL = "gemini-3.1-flash-lite"
FALLBACK_IMAGE_QUALITY = "1080p"
FALLBACK_VIDEO_MODEL = "v6"
FALLBACK_VIDEO_QUALITY = "540p"
PROMPT_ENHANCE_SKILL = "skills-shared/prompting.md"


def fallback_route() -> dict[str, str]:
    return {
        "video_model": FALLBACK_VIDEO_MODEL,
        "video_quality": FALLBACK_VIDEO_QUALITY,
        "image_model": FALLBACK_IMAGE_MODEL,
        "image_quality": FALLBACK_IMAGE_QUALITY,
    }
