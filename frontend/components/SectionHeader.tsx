"use client";

import { motion } from "framer-motion";

export default function SectionHeader({
  eyebrow,
  title,
  accent,
  description,
  right,
}: {
  eyebrow: string;
  title: string;
  accent?: string;
  description?: string;
  right?: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5 }}
      className="mb-8 grid items-end gap-6 lg:grid-cols-12"
    >
      <div className="lg:col-span-8">
        <div className="eyebrow">
          <span className="eyebrow-dot" /> {eyebrow}
        </div>
        <h2 className="display mt-4 text-display leading-[0.92]">
          {title} {accent && <span className="text-red">{accent}</span>}
        </h2>
        {description && (
          <p className="mt-4 max-w-xl text-base leading-[1.55] text-ink-soft">{description}</p>
        )}
      </div>
      {right && <div className="lg:col-span-4 lg:justify-self-end">{right}</div>}
    </motion.div>
  );
}
