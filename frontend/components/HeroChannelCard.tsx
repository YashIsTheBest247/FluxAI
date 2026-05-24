"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, Youtube } from "lucide-react";
import { useFluxData } from "@/lib/useFluxData";
import { useChannelUrl } from "@/lib/useChannel";

/**
 * Right-hero panel — a real "Flux Channel" preview showing the most-recent
 * render and the running total. No floating chips, no faux UI fragments.
 */
export default function HeroChannelCard() {
  const { videos } = useFluxData();
  const channelUrl = useChannelUrl();
  const latest = videos[0] ?? null;
  const published = videos.filter((v) => v.youtube_url);
  const totalSeconds = videos.reduce((a, v) => a + v.duration, 0);
  const hours = totalSeconds / 3600;

  // Footer link priority: latest video's YouTube URL → operator channel URL → scroll to library
  const footerHref = latest?.youtube_url || channelUrl || "#library";
  const isExternal = !!(latest?.youtube_url || channelUrl);
  const footerLabel = latest?.youtube_url
    ? "Watch on YouTube"
    : channelUrl
    ? "Visit Flux Channel"
    : "Browse the archive";

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
      className="relative"
    >
      {/* Outer soft glow */}
      <div className="pointer-events-none absolute -inset-8 bg-[radial-gradient(circle_at_30%_30%,rgba(139,31,31,0.18),transparent_65%)] blur-2xl" />

      <div className="relative overflow-hidden rounded-2xl border border-line bg-bg-card shadow-raised">
        {/* Channel header */}
        <div className="flex items-center justify-between border-b border-line bg-bg-raised px-4 py-2.5">
          <div className="flex items-center gap-2">
            <div className="grid h-6 w-6 place-items-center rounded-md bg-red shadow-red">
              <Youtube className="h-3 w-3 fill-white text-white" />
            </div>
            <div className="leading-tight">
              <div className="text-[12px] font-semibold text-ink">Flux Channel</div>
              <div className="font-mono text-[9px] uppercase tracking-widest text-ink-faint">
                AUTO-PUBLISHED
              </div>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 font-mono text-[9px] font-bold uppercase tracking-widest text-red">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red opacity-70" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-red" />
            </span>
            LIVE
          </span>
        </div>

        {/* Compact stats */}
        <div className="grid grid-cols-2 divide-x divide-line border-b border-line">
          <div className="px-4 py-3">
            <div className="font-mono text-[9px] uppercase tracking-widest text-ink-muted">
              ON CHANNEL
            </div>
            <div className="display mt-1 text-3xl leading-none text-ink">
              {videos.length || "—"}
            </div>
            <div className="mt-1 text-[10px] text-ink-faint">{published.length} on YouTube</div>
          </div>
          <div className="px-4 py-3">
            <div className="font-mono text-[9px] uppercase tracking-widest text-ink-muted">
              RUNTIME
            </div>
            <div className="display mt-1 text-3xl leading-none text-ink">
              {hours >= 1 ? `${hours.toFixed(1)}` : `${totalSeconds}`}
              <span className="ml-1 text-lg text-ink-muted">{hours >= 1 ? "H" : "S"}</span>
            </div>
            <div className="mt-1 text-[10px] text-ink-faint">all renders</div>
          </div>
        </div>

        {/* Footer CTA */}
        <a
          href={footerHref}
          target={isExternal ? "_blank" : undefined}
          rel="noreferrer"
          onClick={(e) => {
            if (!isExternal) {
              e.preventDefault();
              document
                .getElementById("library")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          }}
          className="group flex items-center justify-between border-t border-line bg-bg-raised px-4 py-2.5 transition hover:bg-bg-hover"
        >
          <span className="inline-flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-widest text-ink">
            {isExternal && <Youtube className="h-3 w-3 text-red" />}
            {footerLabel}
          </span>
          <ArrowUpRight className="h-3.5 w-3.5 text-ink-muted transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-red" />
        </a>
      </div>
    </motion.div>
  );
}

