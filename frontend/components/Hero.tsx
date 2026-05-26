"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Play } from "lucide-react";
import HeroChannelCard from "./HeroChannelCard";
import RecentYouTubeUploads from "./RecentYouTubeUploads";

const ease = [0.22, 1, 0.36, 1] as const;

const HEADLINES: { primary: string; accent: string }[] = [
  { primary: "Educational video,", accent: "made effortless." },
  { primary: "Type a topic.",       accent: "Ship a video." },
  { primary: "Idea to YouTube,",    accent: "in minutes." },
  { primary: "Scripts. Visuals.",   accent: "Voice. Shipped." },
  { primary: "Every render,",       accent: "auto-published." },
  { primary: "Topic in.",           accent: "Finished cut out." },
];

const TYPE_MS    = 55;    // delay between chars while typing
const DELETE_MS  = 28;    // delay between chars while deleting
const HOLD_MS    = 1800;  // pause after typing completes
const GAP_MS     = 320;   // pause after deleting before next line

function scrollTo(id: string) {
  const el = document.getElementById(id);
  if (el) {
    history.pushState(null, "", `#${id}`);
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

export default function Hero() {
  return (
    <section className="relative flex min-h-[calc(100vh-5rem)] items-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 red-aura opacity-50" />
      <div className="pointer-events-none absolute inset-0 bg-grid-dark opacity-25" />

      <div className="relative mx-auto w-full max-w-7xl px-6 py-10">
        <div className="grid items-start gap-10 lg:grid-cols-[1.5fr_1fr]">
          <div>
            <TypewriterHeadline />

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease, delay: 0.15 }}
              className="mt-6 max-w-md text-base leading-[1.55] text-ink-soft"
            >
              Type a topic. Flux scripts, narrates and edits a finished video — published to the
              Flux channel and ready to export.
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.28 }}
              className="mt-8 flex flex-wrap items-center gap-3"
            >
              <button onClick={() => scrollTo("creator")} className="btn-red group">
                Start Creating
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </button>
              <button onClick={() => scrollTo("library")} className="btn-outline">
                <Play className="h-3.5 w-3.5 fill-current" />
                View Demo
              </button>
            </motion.div>
          </div>

          <div>
            <HeroChannelCard />
            <RecentYouTubeUploads />
          </div>
        </div>
      </div>

      <motion.button
        onClick={() => scrollTo("creator")}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, y: [0, 6, 0] }}
        transition={{ opacity: { delay: 1, duration: 0.4 }, y: { duration: 2, repeat: Infinity, ease: "easeInOut" } }}
        className="absolute inset-x-0 bottom-6 mx-auto flex w-fit items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-ink-faint hover:text-red"
      >
        <span className="h-3 w-px bg-current" />
        Scroll
      </motion.button>
    </section>
  );
}

/* ===== Typewriter headline ===== */

type Phase = "typing" | "holding" | "deleting" | "gap";

function TypewriterHeadline() {
  const [idx, setIdx] = useState(0);
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("typing");

  const current = HEADLINES[idx];
  const full = `${current.primary} ${current.accent}`;

  useEffect(() => {
    let t: ReturnType<typeof setTimeout> | null = null;
    if (phase === "typing") {
      if (text.length < full.length) {
        t = setTimeout(() => setText(full.slice(0, text.length + 1)), TYPE_MS);
      } else {
        t = setTimeout(() => setPhase("holding"), 0);
      }
    } else if (phase === "holding") {
      t = setTimeout(() => setPhase("deleting"), HOLD_MS);
    } else if (phase === "deleting") {
      if (text.length > 0) {
        t = setTimeout(() => setText(full.slice(0, text.length - 1)), DELETE_MS);
      } else {
        t = setTimeout(() => setPhase("gap"), 0);
      }
    } else if (phase === "gap") {
      t = setTimeout(() => {
        setIdx((i) => (i + 1) % HEADLINES.length);
        setPhase("typing");
      }, GAP_MS);
    }
    return () => { if (t) clearTimeout(t); };
  }, [text, phase, full]);

  // Split the currently-typed text into a white part + red part using the primary length
  // as the divider (the space between primary and accent is hidden when typed).
  const splitIdx = current.primary.length;
  const whiteShown = text.slice(0, Math.min(text.length, splitIdx));
  const pastSep    = text.length > splitIdx;            // we've typed past the space
  const redShown   = text.length > splitIdx + 1 ? text.slice(splitIdx + 1) : "";

  return (
    <h1 className="display min-h-[clamp(140px,21vw,300px)] text-[clamp(46px,7vw,100px)] leading-[1.18] tracking-[0.02em]">
      <span>{whiteShown}</span>
      {pastSep && <br className="hidden sm:block" />}
      <span className="text-red">{redShown}</span>
      <span
        aria-hidden
        className="ml-1 inline-block h-[0.78em] w-[0.06em] translate-y-[0.08em] animate-blink bg-current align-baseline"
      />
    </h1>
  );
}
