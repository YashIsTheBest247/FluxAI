"""Script generation service. Uses GPT-4 to break a topic into scene-wise narration."""
import json
import math
import logging
from typing import List, Optional

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior educational video scriptwriter.
You will receive a TOPIC, target DURATION in seconds, and optional KEY POINTS.
Break the video into 4-8 cohesive SCENES. For each scene produce:
  - narration: 1-3 sentences, conversational, factual, no filler
  - image_prompt: a vivid, cinematic visual description (no text overlays, no logos)
  - duration: seconds (float), summing approximately to the target duration

Return STRICT JSON: {"title": "...", "scenes": [{"index": 0, "narration": "...", "image_prompt": "...", "duration": 6.0}, ...]}.
No prose, no markdown fences."""


def _mock_scenes(topic: str, duration: int, key_points: Optional[str]) -> tuple[str, List[Scene]]:
    n = max(4, min(8, duration // 6))
    per = duration / n
    title = topic.strip().title()
    scenes = []
    snippets = [
        f"{title} begins with a foundational idea that shapes everything that follows.",
        f"At its core, {title.lower()} rests on a few simple principles you can grasp in seconds.",
        f"Here is how {title.lower()} actually works in practice, step by step.",
        f"The most surprising thing about {title.lower()} is how widely it applies.",
        f"Researchers continue to push the boundaries of {title.lower()} every year.",
        f"Real-world examples show {title.lower()} in action across industries.",
        f"Despite the complexity, the underlying intuition behind {title.lower()} is elegant.",
        f"And that is the essence of {title}, distilled into a single arc.",
    ]
    visuals = [
        "wide cinematic shot, soft golden light, abstract concept art",
        "close-up macro photography, shallow depth of field, scientific aesthetic",
        "isometric 3d diagram, clean studio lighting, minimal palette",
        "satellite or aerial view, dramatic atmospheric haze",
        "futuristic laboratory, soft cyan glow, glass surfaces",
        "vintage chalkboard sketch, warm tungsten light",
        "data visualization, neon gradient, dark background",
        "high-detail illustration, painterly style, rich contrast",
    ]
    for i in range(n):
        scenes.append(Scene(
            index=i,
            narration=snippets[i % len(snippets)],
            image_prompt=f"{topic}: {visuals[i % len(visuals)]}",
            duration=round(per, 2),
        ))
    return title, scenes


async def generate_scenes(topic: str, duration: int, key_points: Optional[str] = None) -> tuple[str, List[Scene]]:
    if settings.use_mock:
        logger.info("script_service: MOCK_MODE -> returning synthesised scenes")
        return _mock_scenes(topic, duration, key_points)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    user = f"TOPIC: {topic}\nDURATION: {duration} seconds\nKEY POINTS: {key_points or '(none)'}"
    resp = await client.chat.completions.create(
        model=settings.gpt_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    data = json.loads(resp.choices[0].message.content)
    title = data.get("title", topic.title())
    scenes_raw = data.get("scenes", [])

    # Normalize durations to match requested total
    total = sum(float(s.get("duration", 1)) for s in scenes_raw) or 1
    factor = duration / total
    scenes = [
        Scene(
            index=i,
            narration=s["narration"].strip(),
            image_prompt=s["image_prompt"].strip(),
            duration=round(float(s.get("duration", 1)) * factor, 2),
        )
        for i, s in enumerate(scenes_raw)
    ]
    if not scenes:
        return _mock_scenes(topic, duration, key_points)
    return title, scenes
