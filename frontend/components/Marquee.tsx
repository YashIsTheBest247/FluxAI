"use client";

const WORDS = [
  "Writes scripts",
  "Generates visuals",
  "Narrates scenes",
  "Times captions",
  "Composites video",
  "Encodes 1080p",
  "Publishes to YouTube",
  "Ready to export",
  "Ships in minutes",
  "Zero touches",
];

export default function Marquee() {
  // Duplicate the row twice so translateX(-50%) wraps seamlessly.
  return (
    <div className="overflow-hidden border-y border-line bg-bg-raised">
      <div className="flex animate-marquee whitespace-nowrap py-5">
        {[0, 1].map((copy) => (
          <div
            key={copy}
            aria-hidden={copy === 1}
            className="flex shrink-0 items-center gap-10 px-6"
          >
            {WORDS.map((w, i) => (
              <span key={`${copy}-${i}`} className="flex shrink-0 items-center gap-10">
                <span className="display text-3xl text-ink">{w}</span>
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red" />
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
