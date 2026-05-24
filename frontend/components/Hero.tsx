"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, Play } from "lucide-react";
import HeroChannelCard from "./HeroChannelCard";

const ease = [0.22, 1, 0.36, 1] as const;

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
      {/* Ambient red aura + soft grid */}
      <div className="pointer-events-none absolute inset-0 red-aura opacity-50" />
      <div className="pointer-events-none absolute inset-0 bg-grid-dark opacity-25" />

      <div className="relative mx-auto w-full max-w-7xl px-6 py-10">
        <div className="grid items-start gap-10 lg:grid-cols-[1.5fr_1fr]">
          {/* Left — copy */}
          <div>
            <motion.h1
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease }}
              className="display text-[clamp(48px,7.5vw,108px)] leading-[1.02] tracking-[0.015em]"
            >
              Educational video, <br className="hidden sm:block" />
              <span className="text-red">made effortless.</span>
            </motion.h1>

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

          {/* Right — Flux Channel preview */}
          <HeroChannelCard />
        </div>
      </div>

      {/* Scroll hint */}
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
