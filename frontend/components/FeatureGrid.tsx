"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Image as ImageIcon,
  Mic,
  Captions,
  Film,
  Upload,
  Check,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

import { useFluxData } from "@/lib/useFluxData";
import type { Job, JobStage } from "@/lib/api";

const STAGES: { n: string; title: string; icon: typeof FileText; one: string; stage: JobStage }[] = [
  { n: "01", title: "SCRIPT",    icon: FileText,  one: "We write the story.",         stage: "script"    },
  { n: "02", title: "IMAGE",     icon: ImageIcon, one: "Each scene gets its frame.",  stage: "image"     },
  { n: "03", title: "VOICE",     icon: Mic,       one: "A real narrator reads it.",   stage: "voice"     },
  { n: "04", title: "SUBTITLES", icon: Captions,  one: "Captions, in step.",          stage: "subtitles" },
  { n: "05", title: "ASSEMBLY",  icon: Film,      one: "Everything composites.",      stage: "assembly"  },
  { n: "06", title: "PUBLISH",   icon: Upload,    one: "Straight to YouTube.",        stage: "upload"    },
];

const STAGE_INDEX: Record<string, number> = {
  queued:    -1,
  script:    0,
  image:     1,
  voice:     2,
  subtitles: 3,
  assembly:  4,
  upload:    5,
  done:      6,
  failed:    -2,
};

type StageState = "idle" | "done" | "active" | "failed";

export default function FeatureGrid() {
  const { jobs, videos } = useFluxData();

  // Only surface a job if it's actually still running. Once it finishes (or fails),
  // reset to the idle state so the strip doesn't keep flashing "RENDER COMPLETE".
  const active = useMemo<Job | null>(() => {
    return jobs.find((j) => !["done", "failed"].includes(j.stage)) ?? null;
  }, [jobs]);

  const stageStates = useMemo<StageState[]>(() => {
    if (!active || active.stage === "queued") return STAGES.map(() => "idle");
    if (active.stage === "done") return STAGES.map(() => "done");
    if (active.stage === "failed") {
      const failedIdx = active.stages.findIndex((s) => s.progress < 1);
      const fIdx = failedIdx === -1 ? 0 : failedIdx;
      return STAGES.map((_, i) => (i < fIdx ? "done" : i === fIdx ? "failed" : "idle"));
    }
    const idx = STAGE_INDEX[active.stage] ?? -1;
    return STAGES.map((_, i) => (i < idx ? "done" : i === idx ? "active" : "idle"));
  }, [active]);

  const status = useMemo<{ label: string; tone: "ok" | "red" | "fail" }>(() => {
    if (!active) return { label: `LIBRARY SYNCED · ${videos.length}`, tone: "red" };
    if (active.stage === "done")   return { label: "RENDER COMPLETE", tone: "ok" };
    if (active.stage === "failed") return { label: "RENDER FAILED",   tone: "fail" };
    if (active.stage === "queued") return { label: "QUEUED",          tone: "red" };
    const idx = STAGE_INDEX[active.stage] ?? 0;
    return { label: `RENDERING · ${STAGES[idx]?.title ?? ""}`, tone: "red" };
  }, [active, videos.length]);

  return (
    <section id="pipeline" className="mx-auto max-w-7xl px-6 pb-16 pt-6 sm:pb-20 sm:pt-8">
      <div className="grid items-end gap-8 lg:grid-cols-12">
        <h2 className="display text-display leading-[0.92] lg:col-span-7">
          SIX STAGES. <span className="text-red">ZERO TOUCHES.</span>
        </h2>
        <p className="text-base leading-[1.55] text-ink-soft lg:col-span-5">
          From a topic to a published video — every step happens for you, in order, in the background.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.5 }}
        className="mt-12 overflow-hidden rounded-2xl border border-line bg-bg-card"
      >
        <div className="flex items-center justify-between border-b border-line bg-bg-raised px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="eyebrow">PROJECT PIPELINE</div>
            {active && (
              <span className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                · #{active.id.slice(0, 8)}
              </span>
            )}
          </div>
          <StatusBadge {...status} />
        </div>

        {active && !["done", "failed"].includes(active.stage) && (
          <div className="relative h-[2px] overflow-hidden bg-line">
            <motion.div
              className="absolute inset-y-0 left-0 bg-red"
              initial={false}
              animate={{ width: `${Math.max(2, active.progress * 100)}%` }}
              transition={{ duration: 0.5 }}
            />
            <motion.div
              className="absolute inset-y-0 w-1/4 bg-gradient-to-r from-transparent via-red/60 to-transparent"
              animate={{ x: ["-100%", "400%"] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
            />
          </div>
        )}

        <div className="relative px-6 py-8">
          <div className="pointer-events-none absolute inset-x-12 top-[60px] hidden h-px bg-line sm:block" />
          <div className="relative grid grid-cols-2 gap-y-10 sm:grid-cols-3 lg:grid-cols-6">
            {STAGES.map((s, i) => (
              <StageNode key={s.n} stage={s} state={stageStates[i]} />
            ))}
          </div>
        </div>

        {active && active.stage !== "done" && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-bg-raised px-6 py-3 font-mono text-[11px] uppercase tracking-widest">
            <span className="truncate text-ink-muted">
              <span className="text-ink-faint">TOPIC ·</span>{" "}
              <span className="text-ink">{active.topic}</span>
            </span>
            <span className="text-ink-faint">
              {Math.round(active.progress * 100)}% · {active.duration}s
            </span>
          </div>
        )}

        {active && active.stage === "failed" && active.error && (
          <div className="border-t border-red-deep/40 bg-red-tint/60 px-6 py-3 font-mono text-[11px] text-red-deep">
            <span className="mr-2 font-bold uppercase tracking-widest">FAILED:</span>
            <span className="normal-case tracking-normal">{active.error}</span>
          </div>
        )}
      </motion.div>
    </section>
  );
}

function StageNode({
  stage,
  state,
}: {
  stage: typeof STAGES[number];
  state: StageState;
}) {
  const Icon = stage.icon;
  const isActive = state === "active";
  const isDone = state === "done";
  const isFailed = state === "failed";

  return (
    <div className="group relative flex flex-col items-center text-center">
      <div
        className={clsx(
          "relative z-10 grid h-14 w-14 place-items-center rounded-full border bg-bg-card transition",
          isActive && "border-red bg-red shadow-red animate-pulse-red",
          isDone && "border-red/60 bg-red-tint",
          isFailed && "border-red-deep bg-red-deep/20",
          state === "idle" && "border-line"
        )}
      >
        {isActive ? (
          <Loader2 className="h-5 w-5 animate-spin text-white" />
        ) : isFailed ? (
          <AlertTriangle className="h-5 w-5 text-red" />
        ) : isDone ? (
          <Check className="h-5 w-5 text-red" />
        ) : (
          <Icon className="h-5 w-5 text-ink-soft" />
        )}
      </div>

      <h3
        className={clsx(
          "display mt-3 text-lg leading-none transition",
          isActive && "text-red",
          isFailed && "text-red",
          (isDone || state === "idle") && "text-ink"
        )}
      >
        {stage.title}
      </h3>
      <p
        className={clsx(
          "mt-1.5 text-[11px] transition",
          isActive ? "text-red" : "text-ink-muted"
        )}
      >
        {isActive ? "running…" : isDone ? "done" : isFailed ? "failed" : stage.one}
      </p>
    </div>
  );
}

function StatusBadge({ label, tone }: { label: string; tone: "ok" | "red" | "fail" }) {
  if (tone === "ok") {
    return (
      <div className="inline-flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-widest text-ink">
        <Check className="h-3 w-3 text-red" />
        {label}
      </div>
    );
  }
  if (tone === "fail") {
    return (
      <div className="inline-flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-widest text-red-deep">
        <AlertTriangle className="h-3 w-3" />
        {label}
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-widest text-red">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red opacity-70" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-red" />
      </span>
      {label}
    </div>
  );
}
