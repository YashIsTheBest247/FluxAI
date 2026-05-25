"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Globe, Lock, Eye, Film, Mic } from "lucide-react";
import clsx from "clsx";
import { generate, type Job, type MediaType } from "@/lib/api";

const VIDEO_DURATIONS = [15, 30, 60, 90, 120];
const PODCAST_DURATIONS = [60, 120, 300, 600];

const MEDIA_OPTIONS: { v: MediaType; label: string; icon: typeof Film; desc: string }[] = [
  { v: "video",   label: "Video",   icon: Film, desc: "Per-scene visuals + narration" },
  { v: "podcast", label: "Podcast", icon: Mic,  desc: "One cover + long-form audio" },
];

const PRIVACY = [
  { v: "unlisted", label: "Unlisted", icon: Eye },
  { v: "public",   label: "Public",   icon: Globe },
  { v: "private",  label: "Private",  icon: Lock },
];

export default function GenerationPanel({ onSubmitted }: { onSubmitted?: (job: Job) => void }) {
  const [mediaType, setMediaType] = useState<MediaType>("video");
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(60);
  const [keyPoints, setKeyPoints] = useState("");
  const [privacy, setPrivacy] = useState("unlisted");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const durations = mediaType === "podcast" ? PODCAST_DURATIONS : VIDEO_DURATIONS;

  const switchMedia = (m: MediaType) => {
    setMediaType(m);
    const next = m === "podcast" ? PODCAST_DURATIONS : VIDEO_DURATIONS;
    if (!next.includes(duration)) setDuration(next[1] ?? next[0]);
  };

  const submit = async () => {
    if (!topic.trim()) {
      setError("Topic required.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const job = await generate({
        topic: topic.trim(),
        duration,
        key_points: keyPoints.trim() || undefined,
        privacy,
        media_type: mediaType,
      });
      onSubmitted?.(job);
      setTopic("");
      setKeyPoints("");
    } catch (e: any) {
      setError(e.message ?? "Generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const ctaLabel = mediaType === "podcast" ? "Generate podcast" : "Generate video";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="overflow-hidden rounded-2xl border border-line bg-bg-card"
    >
      <div className="grid divide-line lg:grid-cols-[1.5fr_1fr] lg:divide-x">
        {/* Composition */}
        <div className="px-6 py-7">
          <div>
            <label className="field-label">Format</label>
            <div className="mt-3 grid grid-cols-2 gap-1.5">
              {MEDIA_OPTIONS.map((m) => {
                const Icon = m.icon;
                const active = mediaType === m.v;
                return (
                  <button
                    key={m.v}
                    type="button"
                    onClick={() => switchMedia(m.v)}
                    className={clsx(
                      "flex items-start gap-3 rounded-lg border px-4 py-3 text-left transition",
                      active
                        ? "border-red bg-red-tint text-ink"
                        : "border-line bg-bg-raised text-ink-muted hover:border-line-strong"
                    )}
                  >
                    <Icon className={clsx("mt-0.5 h-4 w-4", active ? "text-red" : "text-ink-muted")} />
                    <span>
                      <span className="block text-[12px] font-bold uppercase tracking-widest">{m.label}</span>
                      <span className="mt-0.5 block text-[11px] leading-snug text-ink-faint">{m.desc}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-8">
            <label className="field-label">Topic</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value.slice(0, 120))}
              placeholder={
                mediaType === "podcast"
                  ? "e.g. The hidden history of standard time"
                  : "e.g. The architecture of photosynthesis"
              }
              className="display mt-3 w-full bg-transparent py-2 text-3xl tracking-tight text-ink placeholder:text-ink-dim outline-none"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.18)" }}
            />
          </div>

          <div className="mt-8">
            <label className="field-label">Duration</label>
            <div className="mt-3 inline-flex rounded-full border border-line p-1">
              {durations.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDuration(d)}
                  className={clsx(
                    "rounded-full px-4 py-1.5 text-[12px] font-bold uppercase tracking-widest transition",
                    duration === d ? "bg-red text-white shadow-red" : "text-ink-muted hover:text-ink"
                  )}
                >
                  {d >= 60 ? `${Math.round(d / 60)}m${d % 60 ? ` ${d % 60}s` : ""}` : `${d}s`}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-8">
            <label className="field-label">Key points</label>
            <textarea
              value={keyPoints}
              onChange={(e) => setKeyPoints(e.target.value.slice(0, 2000))}
              placeholder="Optional. Tone, data points, anything you want included."
              rows={4}
              className="mt-3 w-full resize-none bg-transparent py-2 text-base leading-relaxed text-ink placeholder:text-ink-dim outline-none"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.18)" }}
            />
          </div>
        </div>

        {/* Settings + submit */}
        <aside className="bg-bg-raised px-6 py-7">
          <div>
            <label className="field-label">Visibility on YouTube</label>
            <div className="mt-3 grid grid-cols-3 gap-1.5">
              {PRIVACY.map((p) => {
                const Icon = p.icon;
                const active = privacy === p.v;
                return (
                  <button
                    key={p.v}
                    type="button"
                    onClick={() => setPrivacy(p.v)}
                    className={clsx(
                      "flex flex-col items-start gap-2 rounded-lg border px-3 py-3 text-left transition",
                      active
                        ? "border-red bg-red-tint text-ink"
                        : "border-line bg-bg-card text-ink-muted hover:border-line-strong"
                    )}
                  >
                    <Icon className={clsx("h-4 w-4", active ? "text-red" : "text-ink-muted")} />
                    <span className="text-[12px] font-bold uppercase tracking-widest">{p.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="mt-6 rounded-lg border border-red/40 bg-red-tint px-4 py-2.5 text-sm text-red">
              {error}
            </div>
          )}

          <button
            onClick={submit}
            disabled={loading || !topic.trim()}
            className="btn-red mt-6 w-full justify-between"
          >
            <span>{loading ? "Queuing…" : ctaLabel}</span>
            <ArrowUpRight className="h-4 w-4" />
          </button>

          <p className="mt-3 text-center font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            {mediaType === "podcast"
              ? "MP3 + YouTube upload · ~3–8 min"
              : "Auto-publishes to YouTube · ~5–10 min"}
          </p>
        </aside>
      </div>
    </motion.div>
  );
}
