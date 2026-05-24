"use client";

import { motion } from "framer-motion";
import { Play, Maximize2, Volume2, Settings } from "lucide-react";

const SCENES = [
  { title: "", caption: "O₂ is released as a byproduct.",          image: "/Screenshot 2026-05-24 160713.png" },
  { title: "", caption: "Photons strike the leaf surface.",        image: "/Screenshot 2026-05-24 160644.png" },
  { title: "", caption: "Inside the plant cell, chloroplasts wait.", image: "/Screenshot 2026-05-24 160651.png" },
  { title: "", caption: "The spider balances seemingly on its web.", image: "/Screenshot 2026-05-24 160658.png" },
  { title: "", caption: "Light energy splits water molecules.",    image: "/Screenshot 2026-05-24 160705.png" },
  { title: "", caption: "Carbon and hydrogen become sugar.",       image: "/Screenshot 2026-05-24 160747.png" },
  { title: "", caption: "Stored energy fuels new growth.",         image: "/Screenshot 2026-05-24 160906.png" },
] as const;

export default function PreviewCard() {
  const activeScene = 3;

  return (
    <div className="relative">
      <div className="overflow-hidden rounded-2xl border border-line bg-bg-card shadow-raised">
        {/* Window chrome */}
        <div className="flex items-center justify-between border-b border-line bg-bg-raised px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red" />
            <span className="h-2.5 w-2.5 rounded-full bg-ink-dim" />
            <span className="h-2.5 w-2.5 rounded-full bg-ink-dim" />
          </div>
          <div className="flex items-center gap-1.5 rounded-md border border-line bg-bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-ink-muted">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red" />
            flux.app / sample
          </div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            preview
          </div>
        </div>

        <div className="px-7 py-8">
          <div className="eyebrow">SAMPLE RENDER</div>
          <h3 className="display mt-3 text-4xl text-ink">
            MINI <span className="text-red">DOCUMENTARY</span>
          </h3>

          {/* Video frame */}
          <div className="relative mt-6 aspect-video overflow-hidden rounded-xl border border-line bg-black">
            <SceneArt index={activeScene} large />
            <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-black/15" />

            <div className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-md border border-white/15 bg-black/55 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-widest text-white backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-red" />
              DEMO
            </div>

            <button className="absolute left-1/2 top-1/2 grid h-14 w-14 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-red shadow-red animate-pulse-red">
              <Play className="h-5 w-5 translate-x-[1px] fill-white text-white" />
            </button>

            <div className="absolute inset-x-0 bottom-12 mx-auto w-fit max-w-[80%] rounded bg-black/70 px-3 py-1.5 text-center text-[13px] font-medium text-white backdrop-blur">
              {SCENES[activeScene].caption}
            </div>

            <div className="absolute inset-x-4 bottom-4">
              <div className="flex items-center gap-3 text-white">
                <Play className="h-3 w-3 fill-current" />
                <div className="relative h-[3px] flex-1 overflow-hidden rounded-full bg-white/15">
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full bg-red"
                    initial={{ width: "0%" }}
                    animate={{ width: "62%" }}
                    transition={{ duration: 4, ease: [0.22, 1, 0.36, 1] }}
                  />
                  <span
                    className="absolute -top-1 h-[7px] w-[7px] rounded-full bg-red shadow-red"
                    style={{ left: "62%", transform: "translateX(-50%)" }}
                  />
                </div>
                <span className="font-mono text-[10px] tabular-nums">0:37 / 1:00</span>
                <Volume2 className="h-3.5 w-3.5" />
                <Settings className="h-3.5 w-3.5" />
                <Maximize2 className="h-3.5 w-3.5" />
              </div>
            </div>
          </div>

          {/* Scene strip */}
          <div className="mt-5 flex gap-2 overflow-hidden">
            {SCENES.map((_, i) => {
              const isActive = i === activeScene;
              return (
                <div key={i} className="flex-1">
                  <div
                    className={
                      "relative aspect-video overflow-hidden rounded-md ring-1 ring-inset transition " +
                      (isActive ? "ring-red shadow-red" : "ring-white/10")
                    }
                  >
                    <SceneArt index={i} />
                    {isActive && (
                      <div className="absolute inset-0 ring-2 ring-inset ring-red/60" />
                    )}
                  </div>
                  <div
                    className={
                      "mt-1.5 flex items-center justify-between font-mono text-[9px] uppercase tracking-widest " +
                      (isActive ? "text-red" : "text-ink-faint")
                    }
                  >
                    <span>SCN · 0{i + 1}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Floating spec tile */}
      <div className="absolute -right-3 -top-3 hidden rounded-xl border border-line bg-bg-card px-4 py-2.5 shadow-card md:block">
        <div className="eyebrow">AUTO-PUBLISH</div>
        <div className="mt-1 flex items-center gap-1.5 text-sm font-medium text-red">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red" />
          CONNECTED · YOUTUBE
        </div>
      </div>
    </div>
  );
}

function SceneArt({ index, large = false }: { index: number; large?: boolean }) {
  const scn = SCENES[index] ?? SCENES[0];
  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img
      src={scn.image}
      alt=""
      className={
        "absolute inset-0 h-full w-full object-cover " + (large ? "scale-[1.02]" : "")
      }
      draggable={false}
    />
  );
}
