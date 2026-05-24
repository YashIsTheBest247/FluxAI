"""Script generation service.

Supports two providers:
  * "openai" — GPT-4 chat completions (paid)
  * "gemini" — Google Gemini generateContent REST API (free tier)

Falls back to a deterministic synthesised outline if no credentials are configured
(or if MOCK_MODE=true).
"""
import json
import logging
from typing import List, Optional

import httpx

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior educational video scriptwriter.
You will receive a TOPIC, target DURATION in seconds, and optional KEY POINTS.

SCENE COUNT rules — fewer is faster and tighter:
  - DURATION <= 20s  → exactly 3 scenes
  - DURATION 21-45s  → 3 or 4 scenes
  - DURATION 46-90s  → 4 or 5 scenes
  - DURATION > 90s   → 5 or 6 scenes (NEVER more than 6)

For each scene produce:
  - narration: 1-3 sentences, conversational, factual, no filler
  - image_prompt: a vivid, cinematic visual description (no text overlays, no logos)
  - duration: seconds (float), summing approximately to the target duration

Return STRICT JSON: {"title": "...", "scenes": [{"index": 0, "narration": "...", "image_prompt": "...", "duration": 6.0}, ...]}.
No prose, no markdown fences."""


def _mock_scenes(topic: str, duration: int, key_points: Optional[str]) -> tuple[str, List[Scene]]:
    # Match the same scene-count rule as the real provider prompt
    if duration <= 20:
        n = 3
    elif duration <= 45:
        n = 4
    elif duration <= 90:
        n = 5
    else:
        n = 6
    per = duration / n
    title = topic.strip().title()
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
    scenes: List[Scene] = []
    for i in range(n):
        scenes.append(Scene(
            index=i,
            narration=snippets[i % len(snippets)],
            image_prompt=f"{topic}: {visuals[i % len(visuals)]}",
            duration=round(per, 2),
        ))
    return title, scenes


def _parse_scenes_payload(data: dict, topic: str, duration: int) -> tuple[str, List[Scene]]:
    title = data.get("title", topic.title())
    scenes_raw = data.get("scenes", [])
    total = sum(float(s.get("duration", 1)) for s in scenes_raw) or 1
    factor = duration / total
    scenes = [
        Scene(
            index=i,
            narration=str(s["narration"]).strip(),
            image_prompt=str(s["image_prompt"]).strip(),
            duration=round(float(s.get("duration", 1)) * factor, 2),
        )
        for i, s in enumerate(scenes_raw)
        if "narration" in s and "image_prompt" in s
    ]
    return title, scenes


async def _openai_scenes(topic: str, duration: int, key_points: Optional[str]) -> tuple[str, List[Scene]]:
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
    return _parse_scenes_payload(json.loads(resp.choices[0].message.content), topic, duration)


async def _gemini_scenes(topic: str, duration: int, key_points: Optional[str]) -> tuple[str, List[Scene]]:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    user = f"TOPIC: {topic}\nDURATION: {duration} seconds\nKEY POINTS: {key_points or '(none)'}"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
        data = r.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response shape: {e}; payload={data}")

    payload = json.loads(text)
    return _parse_scenes_payload(payload, topic, duration)


async def generate_scenes(topic: str, duration: int, key_points: Optional[str] = None) -> tuple[str, List[Scene]]:
    if settings.use_mock:
        logger.info("script_service: MOCK_MODE -> synthesised scenes")
        return _mock_scenes(topic, duration, key_points)

    provider = settings.provider_normalized
    try:
        if provider == "gemini":
            logger.info("script_service: using Gemini (%s)", settings.gemini_model)
            title, scenes = await _gemini_scenes(topic, duration, key_points)
        else:
            logger.info("script_service: using OpenAI (%s)", settings.gpt_model)
            title, scenes = await _openai_scenes(topic, duration, key_points)
    except Exception as e:
        logger.exception("script_service: %s failed (%s) — falling back to mock", provider, e)
        return _mock_scenes(topic, duration, key_points)

    if not scenes:
        logger.warning("script_service: provider returned no scenes, using mock")
        return _mock_scenes(topic, duration, key_points)
    return title, scenes
