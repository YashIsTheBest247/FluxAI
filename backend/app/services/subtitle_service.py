"""Subtitle timing - aligns narration text against measured audio length per scene."""
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple

import pysrt

from ..models.schemas import Scene


def _td(seconds: float) -> pysrt.SubRipTime:
    ms = int(round(seconds * 1000))
    return pysrt.SubRipTime(milliseconds=ms)


def _chunk(text: str, max_chars: int = 110) -> List[str]:
    """Word-wrap to ~110 chars. Most scene narrations fit in 1 chunk now,
    which means one subtitle clip per scene instead of 3-4 — dramatic assembly speedup
    (compositing cost scales with chunk count, not narration length)."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    chunks: List[str] = []
    cur = ""
    for w in words:
        if len(cur) + 1 + len(w) > max_chars and cur:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def build_srt(
    scenes: List[Scene],
    scene_audio_lengths: List[float],
    out: Path,
) -> Path:
    subs = pysrt.SubRipFile()
    t0 = 0.0
    idx = 1
    for scene, dur in zip(scenes, scene_audio_lengths):
        lines = _chunk(scene.narration)
        per = dur / max(1, len(lines))
        for line in lines:
            sub = pysrt.SubRipItem(
                index=idx,
                start=_td(t0),
                end=_td(t0 + per),
                text=line,
            )
            subs.append(sub)
            t0 += per
            idx += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(out), encoding="utf-8")
    return out
