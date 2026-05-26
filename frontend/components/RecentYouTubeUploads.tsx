"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, Youtube } from "lucide-react";
import { useFluxData } from "@/lib/useFluxData";

/** Compact list of every render that landed on YouTube, shown directly under
 *  the channel card on the hero. Hidden when there's nothing published yet. */
export default function RecentYouTubeUploads({ limit = 5 }: { limit?: number }) {
  const { videos } = useFluxData();
  const published = videos.filter((v) => v.youtube_url).slice(0, limit);

  if (published.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="mt-4 overflow-hidden rounded-2xl border border-line bg-bg-card"
    >
      <div className="flex items-center justify-between border-b border-line bg-bg-raised px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Youtube className="h-3.5 w-3.5 text-red" />
          <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-ink">
            On YouTube
          </span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          {published.length} {published.length === 1 ? "video" : "videos"}
        </span>
      </div>

      <ul className="divide-y divide-line">
        {published.map((v) => (
          <li key={v.id}>
            <a
              href={v.youtube_url ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="group flex items-center gap-3 px-4 py-2.5 transition hover:bg-bg-hover"
            >
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-red-tint">
                <Youtube className="h-3.5 w-3.5 fill-red text-red" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] font-semibold text-ink transition group-hover:text-red">
                  {v.title}
                </div>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-widest text-ink-faint">
                  {v.media_type === "podcast" ? "PODCAST" : "VIDEO"} ·{" "}
                  {fmtDuration(v.duration)} ·{" "}
                  {new Date(v.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "2-digit",
                  })}
                </div>
              </div>
              <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-ink-muted transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-red" />
            </a>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

function fmtDuration(secs: number) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
