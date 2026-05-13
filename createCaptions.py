import os
import cv2
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─────────────────────────────────────────
# HELPER: Convert image file to base64
# (Required format for OpenAI Vision API)
# ─────────────────────────────────────────
def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# ─────────────────────────────────────────
# HELPER: Extract middle frame from video
# Returns it as base64 string
# ─────────────────────────────────────────
def extract_frame_from_video(video_path: str) -> str:
    """
    Extracts the middle frame of a video file.
    Returns the frame as a base64 encoded string.
    """
    print(f"🎬 Extracting frame from video: {video_path}")

    cap         = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    middle_frame = total_frames // 2   # Jump to middle of video

    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
    success, frame = cap.read()
    cap.release()

    if not success:
        raise ValueError("❌ Could not extract frame from video.")

    # Convert OpenCV frame (BGR) to PIL Image (RGB)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)

    # Convert to base64
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG")
    base64_frame = base64.b64encode(buffer.getvalue()).decode("utf-8")

    print(f"✅ Frame extracted successfully!")
    return base64_frame

# ─────────────────────────────────────────
# CORE: Generate caption from base64 image
# ─────────────────────────────────────────
def generate_caption_from_image(
    base64_image:    str,
    tone:            str = "engaging",
    include_hashtags: bool = True,
    language:        str = "English",
    custom_prompt:   str = None,
    max_length:      int = 2200
) -> str:
    """
    Sends image to GPT-4o and gets an Instagram caption back.

    tone             : "engaging", "professional", "funny", "inspirational", "casual"
    include_hashtags : Whether to add hashtags at the end
    language         : Language for the caption
    custom_prompt    : Override the default prompt entirely
    max_length       : Max caption length (Instagram limit = 2200)
    """
    if custom_prompt:
        prompt = custom_prompt
    else:
        hashtag_instruction = (
            "End with 5-10 relevant hashtags."
            if include_hashtags
            else "Do NOT include any hashtags."
        )
        prompt = f"""
You are an expert Instagram content creator.
Look at this image carefully and write an Instagram caption for it.

Requirements:
- Tone: {tone}
- Language: {language}
- Maximum length: {max_length} characters
- {hashtag_instruction}
- Make it feel natural and human-written
- Do not use generic filler phrases like "Check this out!"
- Return ONLY the caption text, nothing else
        """.strip()

    print(f"✍️  Generating caption (tone: {tone}, hashtags: {include_hashtags})...")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type":      "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=500
    )

    caption = response.choices[0].message.content.strip()
    print(f"✅ Caption generated! ({len(caption)} characters)")
    return caption

# ─────────────────────────────────────────
# METHOD 1: Generate caption from IMAGE file
# ─────────────────────────────────────────
def generate_caption_for_image(
    image_path:      str,
    tone:            str  = "engaging",
    include_hashtags: bool = True,
    language:        str  = "English",
    custom_prompt:   str  = None,
) -> str:
    """
    Generate an Instagram caption for an image file.

    image_path : Path to your local image file (.jpg, .png etc)
    """
    print(f"\n{'='*55}")
    print(f"🖼️  Generating caption for IMAGE: {image_path}")
    print(f"{'='*55}")

    base64_image = image_to_base64(image_path)
    caption      = generate_caption_from_image(
        base64_image     = base64_image,
        tone             = tone,
        include_hashtags = include_hashtags,
        language         = language,
        custom_prompt    = custom_prompt
    )

    print(f"\n📝 Generated Caption:\n{'-'*40}\n{caption}\n{'-'*40}")
    return caption

# ─────────────────────────────────────────
# METHOD 2: Generate caption from VIDEO file
# (Extracts middle frame → sends to GPT-4o)
# ─────────────────────────────────────────
def generate_caption_for_video(
    video_path:      str,
    tone:            str  = "engaging",
    include_hashtags: bool = True,
    language:        str  = "English",
    custom_prompt:   str  = None,
) -> str:
    """
    Generate an Instagram caption for a video file.
    Extracts the middle frame and analyzes it with GPT-4o.

    video_path : Path to your local video file (.mp4 etc)
    """
    print(f"\n{'='*55}")
    print(f"🎬 Generating caption for VIDEO: {video_path}")
    print(f"{'='*55}")

    base64_frame = extract_frame_from_video(video_path)
    caption      = generate_caption_from_image(
        base64_image     = base64_frame,
        tone             = tone,
        include_hashtags = include_hashtags,
        language         = language,
        custom_prompt    = custom_prompt
    )

    print(f"\n📝 Generated Caption:\n{'-'*40}\n{caption}\n{'-'*40}")
    return caption

# ─────────────────────────────────────────
# METHOD 3: Generate caption from TEXT only
# (When you just describe what the content is)
# ─────────────────────────────────────────
def generate_caption_from_description(
    description:     str,
    tone:            str  = "engaging",
    include_hashtags: bool = True,
    language:        str  = "English",
) -> str:
    """
    Generate a caption from a text description of the content.
    Use this when you don't have the local file available.

    description : e.g. "A sunset photo on a beach in Bali"
    """
    print(f"\n{'='*55}")
    print(f"💬 Generating caption from description...")
    print(f"{'='*55}")

    hashtag_instruction = (
        "End with 5-10 relevant hashtags."
        if include_hashtags
        else "Do NOT include any hashtags."
    )

    prompt = f"""
You are an expert Instagram content creator.
Write an Instagram caption for the following content:

Content description: {description}

Requirements:
- Tone: {tone}
- Language: {language}
- Maximum length: 2200 characters
- {hashtag_instruction}
- Make it feel natural and human-written
- Return ONLY the caption text, nothing else
    """.strip()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )

    caption = response.choices[0].message.content.strip()
    print(f"✅ Caption generated! ({len(caption)} characters)")
    print(f"\n📝 Generated Caption:\n{'-'*40}\n{caption}\n{'-'*40}")
    return caption

# ─────────────────────────────────────────
# METHOD 4: Generate MULTIPLE caption
# variations to choose from
# ─────────────────────────────────────────
def generate_caption_variations(
    image_path:  str = None,
    video_path:  str = None,
    description: str = None,
    variations:  int = 3,
    language:    str = "English",
) -> list:
    """
    Generate multiple caption options for the same content.
    Returns a list of captions with different tones.

    variations : How many caption options to generate (default 3)
    """
    print(f"\n{'='*55}")
    print(f"🎨 Generating {variations} caption variations...")
    print(f"{'='*55}")

    # Get base64 image if file provided
    base64_image = None
    if image_path:
        base64_image = image_to_base64(image_path)
    elif video_path:
        base64_image = extract_frame_from_video(video_path)

    prompt = f"""
You are an expert Instagram content creator.
Generate exactly {variations} different Instagram caption variations.
{'For the image provided.' if base64_image else f'For this content: {description}'}

Rules:
- Each variation must have a DIFFERENT tone
  (e.g. engaging, funny, inspirational, professional, casual)
- Each must include 5 relevant hashtags
- Language: {language}
- Return ONLY a valid JSON array like this:
[
  {{"tone": "engaging", "caption": "caption text here..."}},
  {{"tone": "funny",    "caption": "caption text here..."}}
]
- No extra text outside the JSON array
    """.strip()

    # Build message content
    content = []
    if base64_image:
        content.append({
            "type":      "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    content.append({"type": "text", "text": prompt})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=1000
    )

    raw      = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    raw      = raw.replace("```json", "").replace("```", "").strip()
    captions = json.loads(raw)

    print(f"\n📝 Caption Variations Generated:")
    for i, item in enumerate(captions, 1):
        print(f"\n   Variation {i} ({item['tone'].upper()}):")
        print(f"   {item['caption'][:100]}...")

    return captions


# ─────────────────────────────────────────
# FULL PIPELINE: Generate caption + Post
# ─────────────────────────────────────────
def run_full_pipeline(
    media_path:      str,
    media_type:      str  = "video",   # "video" or "image"
    tone:            str  = "engaging",
    include_hashtags: bool = True,
    language:        str  = "English",
    custom_caption:  str  = None,      # Override auto-generation
):
    """
    Complete pipeline:
    1. Generate caption using OpenAI
    2. Return caption ready to pass into postReels.py

    media_path    : Path to your local video or image file
    media_type    : "video" or "image"
    custom_caption: Skip AI generation and use this caption instead
    """
    # Use custom caption if provided
    if custom_caption is not None:
        print(f"📝 Using custom caption (skipping AI generation)")
        return custom_caption

    # Auto-generate caption
    if media_type == "image":
        caption = generate_caption_for_image(
            image_path       = media_path,
            tone             = tone,
            include_hashtags = include_hashtags,
            language         = language,
        )
    elif media_type == "video":
        caption = generate_caption_for_video(
            video_path       = media_path,
            tone             = tone,
            include_hashtags = include_hashtags,
            language         = language,
        )
    else:
        raise ValueError("media_type must be 'video' or 'image'")

    return caption


# ─────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────
if __name__ == "__main__":

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

    # ── Set your file path here ──
    media_path = r"E:\BitBash\GeelarkAutomation\getContent\ugc_videos\07-05-26 BuzzPatch\07-06-26 Short Form Yapper Sceptic Asian Mom.mp4"

    ext = os.path.splitext(media_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        caption = generate_caption_for_image(
            image_path       = media_path,
            tone             = "engaging",
            include_hashtags = True,
            language         = "English",
        )
    elif ext in VIDEO_EXTENSIONS:
        caption = generate_caption_for_video(
            video_path       = media_path,
            tone             = "engaging",
            include_hashtags = True,
            language         = "English",
        )
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Use an image or video file.")

    print(f"\nFinal caption to use:\n{caption}")