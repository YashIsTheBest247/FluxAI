"use client";

import SectionHeader from "./SectionHeader";
import GenerationPanel from "./GenerationPanel";
import { useFluxData } from "@/lib/useFluxData";

export default function CreatorSection() {
  const { refresh } = useFluxData();

  return (
    <section id="creator" className="border-t border-line">
      <div className="mx-auto max-w-7xl px-6 pb-16 pt-6 sm:pb-20 sm:pt-8">
        <SectionHeader
          eyebrow="CREATOR"
          title="COMPOSE,"
          accent="RENDER, PUBLISH."
          description="Type a topic. We handle scripting, visuals, narration and assembly — then publish straight to YouTube."
        />
        <GenerationPanel
          onSubmitted={() => {
            refresh();
            // Smooth-scroll the user to the pipeline section so they can watch progress.
            setTimeout(() => {
              document.getElementById("pipeline")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 80);
          }}
        />
      </div>
    </section>
  );
}
