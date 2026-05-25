"use client";

import { motion } from "framer-motion";
import { Download, ExternalLink, Play, Trash2, X, Youtube, Film, Clapperboard, FileVideo, Mic, Headphones } from "lucide-react";
import type { Video } from "@/lib/api";

/**
 * Library card — matches the documentary-cinematography card pattern:
 *   • Category badge top-left (icon + label)
 *   • YouTube tag bottom-right (red, only when published)
 *   • Centered red play button on hover
 *   • Big condensed-uppercase title under the thumb
 *   • Short description in muted grey
 */
export default function VideoCard({
  video,
  onDelete,
  onExpand,
}: {
  video: Video;
  index?: number;
  onDelete?: (id: string) => void;
  onExpand?: (v: Video) => void;
}) {
  const category = pickCategory(video);
  const CatIcon = category.icon;

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="group flex flex-col"
    >
      {/* Thumb */}
      <button
        onClick={() => onExpand?.(video)}
        className="relative aspect-video w-full overflow-hidden rounded-2xl bg-bg-elevated text-left"
      >
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="h-full w-full object-cover transition duration-[1200ms] group-hover:scale-[1.04]"
          />
        ) : (
          <div className="h-full w-full bg-gradient-to-br from-bg-hover via-bg-elevated to-bg-card" />
        )}

        {/* Vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/10" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-transparent" />

        {/* Top-left category badge */}
        <div className="absolute left-4 top-4">
          <span className="cat-badge">
            <CatIcon className="h-3.5 w-3.5" />
            {category.label}
          </span>
        </div>

        {/* Top-right delete */}
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(video.id);
            }}
            className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-md bg-black/60 text-ink-soft opacity-0 backdrop-blur transition group-hover:opacity-100 hover:bg-red hover:text-white"
            aria-label="Delete"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Bottom-right YouTube tag (only when published) */}
        {video.youtube_url && (
          <a
            href={video.youtube_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="absolute bottom-4 right-4 inline-flex items-center gap-1.5 rounded-md bg-red px-2.5 py-1 text-[11px] font-bold uppercase tracking-widest text-white shadow-red transition hover:bg-red-hover"
          >
            <Youtube className="h-3 w-3 fill-current" />
            YouTube
          </a>
        )}

        {/* Bottom-left duration */}
        <div className="absolute bottom-4 left-4 rounded-md bg-black/60 px-2 py-0.5 font-mono text-[11px] tabular-nums text-white backdrop-blur">
          {fmtDuration(video.duration)}
        </div>

        {/* Centered red play */}
        <div className="absolute inset-0 grid place-items-center">
          <span className="grid h-16 w-16 place-items-center rounded-full bg-red shadow-red transition duration-300 group-hover:scale-110 group-hover:bg-red-hover">
            <Play className="h-6 w-6 translate-x-[1px] fill-white text-white" />
          </span>
        </div>
      </button>

      {/* Title block — heavy condensed display caps */}
      <div className="mt-5">
        <h3 className="display line-clamp-2 text-2xl leading-[1.05] text-ink transition group-hover:text-red sm:text-3xl">
          {(video.title || "").toUpperCase()}
        </h3>
        <p className="mt-3 line-clamp-2 text-[13px] leading-[1.55] text-ink-muted">
          {video.topic}
        </p>

        {/* Meta + actions */}
        <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
          <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            <span>{video.scene_count} SCN</span>
            <span className="h-[3px] w-[3px] rounded-full bg-ink-dim" />
            <span>{video.resolution}</span>
            <span className="h-[3px] w-[3px] rounded-full bg-ink-dim" />
            <span>{new Date(video.created_at).toLocaleDateString("en-US", { month: "short", day: "2-digit" })}</span>
          </div>
          <div className="flex items-center gap-1">
            {video.audio_url && (
              <a
                href={video.audio_url}
                download
                onClick={(e) => e.stopPropagation()}
                className="grid h-7 w-7 place-items-center rounded text-ink-muted transition hover:bg-bg-hover hover:text-red"
                aria-label="Download MP3"
                title="Download MP3"
              >
                <Headphones className="h-3.5 w-3.5" />
              </a>
            )}
            <a
              href={video.file_url}
              download
              onClick={(e) => e.stopPropagation()}
              className="grid h-7 w-7 place-items-center rounded text-ink-muted transition hover:bg-bg-hover hover:text-ink"
              aria-label="Download"
              title={video.media_type === "podcast" ? "Download MP4 cover-cut" : "Download MP4"}
            >
              <Download className="h-3.5 w-3.5" />
            </a>
            {video.youtube_url && (
              <a
                href={video.youtube_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="grid h-7 w-7 place-items-center rounded text-ink-muted transition hover:bg-bg-hover hover:text-red"
                aria-label="YouTube"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={() => onDelete(video.id)}
                className="grid h-7 w-7 place-items-center rounded text-ink-muted transition hover:bg-red-tint hover:text-red"
                aria-label="Delete"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.article>
  );
}

function pickCategory(v: Video): { label: string; icon: typeof Film } {
  if (v.media_type === "podcast") {
    if (v.duration <= 90)  return { label: "INTERLUDE", icon: Mic };
    if (v.duration <= 300) return { label: "EPISODE",   icon: Headphones };
    return { label: "DEEP DIVE", icon: Headphones };
  }
  // Deterministic mapping from duration to a documentary-style category.
  if (v.duration <= 20)  return { label: "TEASER",     icon: Clapperboard };
  if (v.duration <= 45)  return { label: "TRAILER",    icon: Clapperboard };
  if (v.duration <= 75)  return { label: "SHORT FILM", icon: FileVideo };
  if (v.duration <= 110) return { label: "EPISODE",    icon: Film };
  return { label: "FEATURE", icon: Film };
}

export function VideoModal({ video, onClose }: { video: Video; onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-[60] grid place-items-center bg-black/85 p-6 backdrop-blur-md"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-4xl overflow-hidden rounded-2xl border border-line bg-bg-card shadow-raised"
      >
        <div className="flex items-start justify-between border-b border-line px-6 py-4">
          <div>
            <div className="eyebrow mb-1">NOW PLAYING</div>
            <div className="display text-2xl text-ink">{(video.title || "").toUpperCase()}</div>
            <div className="mt-1 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              {video.topic} · {fmtDuration(video.duration)} · {video.scene_count} SCENES
            </div>
          </div>
          <button
            onClick={onClose}
            className="grid h-9 w-9 place-items-center rounded-full border border-line text-ink-soft hover:border-red hover:text-red"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {video.media_type === "podcast" && video.audio_url ? (
          <div className="relative bg-black">
            {video.thumbnail_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={video.thumbnail_url}
                alt={video.title}
                className="aspect-video w-full object-cover opacity-90"
              />
            )}
            <audio src={video.audio_url} controls autoPlay className="absolute inset-x-0 bottom-0 w-full" />
          </div>
        ) : (
          <video src={video.file_url} controls autoPlay className="w-full bg-black" />
        )}
      </motion.div>
    </motion.div>
  );
}

function fmtDuration(secs: number) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
