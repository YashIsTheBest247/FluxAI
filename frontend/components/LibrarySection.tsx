"use client";

import { AnimatePresence } from "framer-motion";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import clsx from "clsx";

import SectionHeader from "./SectionHeader";
import VideoCard, { VideoModal } from "./VideoCard";
import { deleteVideo, type Video } from "@/lib/api";
import { useFluxData } from "@/lib/useFluxData";

export default function LibrarySection() {
  const { videos, refresh } = useFluxData();
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "video" | "podcast" | "published">("all");
  const [sort, setSort] = useState<"recent" | "duration" | "scenes">("recent");
  const [modal, setModal] = useState<Video | null>(null);

  const display = useMemo(() => {
    let v = [...videos];
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      v = v.filter((x) => x.title.toLowerCase().includes(needle) || x.topic.toLowerCase().includes(needle));
    }
    if (filter === "video") v = v.filter((x) => x.media_type !== "podcast");
    if (filter === "podcast") v = v.filter((x) => x.media_type === "podcast");
    if (filter === "published") v = v.filter((x) => x.youtube_url);
    if (sort === "recent") v.sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at));
    if (sort === "duration") v.sort((a, b) => b.duration - a.duration);
    if (sort === "scenes") v.sort((a, b) => b.scene_count - a.scene_count);
    return v;
  }, [videos, q, filter, sort]);

  return (
    <section id="library" className="border-t border-line">
      <div className="mx-auto max-w-7xl px-6 pb-16 pt-6 sm:pb-20 sm:pt-8">
        <SectionHeader
          title="YOUR"
          accent="ARCHIVE."
          description="Every finished render — downloadable, replayable, searchable."
          right={
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 border-b border-line py-1.5 transition focus-within:border-red">
                <Search className="h-4 w-4 text-ink-faint" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search…"
                  className="w-44 bg-transparent text-sm text-ink placeholder:text-ink-faint outline-none"
                />
              </div>
              <div className="inline-flex rounded-full border border-line p-1">
                {(["all", "video", "podcast", "published"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={clsx(
                      "rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-widest transition",
                      filter === f ? "bg-red text-white shadow-red" : "text-ink-muted hover:text-ink"
                    )}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as any)}
                className="rounded-full border border-line bg-bg-card px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest text-ink outline-none"
              >
                <option value="recent">Recent</option>
                <option value="duration">Longest</option>
                <option value="scenes">Most scenes</option>
              </select>
            </div>
          }
        />

        {display.length === 0 ? (
          <div className="grid place-items-center rounded-2xl border border-dashed border-line p-16 text-center">
            <p className="display text-3xl text-ink">NOTHING YET.</p>
            <p className="mt-2 max-w-sm text-sm text-ink-muted">
              {q || filter !== "all"
                ? "No matches for those filters."
                : "Render your first video to populate the archive."}
            </p>
          </div>
        ) : (
          <div className="grid gap-x-6 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
            {display.map((v) => (
              <VideoCard
                key={v.id}
                video={v}
                onDelete={async (id) => {
                  await deleteVideo(id);
                  refresh();
                }}
                onExpand={(vid) => setModal(vid)}
              />
            ))}
          </div>
        )}
      </div>

      <AnimatePresence>{modal && <VideoModal video={modal} onClose={() => setModal(null)} />}</AnimatePresence>
    </section>
  );
}
