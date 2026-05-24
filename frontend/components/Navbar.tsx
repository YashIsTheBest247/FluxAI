"use client";

import { useEffect, useState } from "react";
import { Search, Menu, X, ArrowUpRight, Youtube } from "lucide-react";
import clsx from "clsx";
import { useChannelUrl } from "@/lib/useChannel";

const NAV = [
  { id: "dashboard", label: "Dashboard" },
  { id: "creator",   label: "Creator" },
  { id: "pipeline",  label: "Pipeline" },
  { id: "library",   label: "Library" },
];

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<string>("dashboard");
  const [q, setQ] = useState("");
  const channelUrl = useChannelUrl();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Active-section tracking via IntersectionObserver
  useEffect(() => {
    const ids = NAV.map((n) => n.id);
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((e): e is HTMLElement => !!e);
    if (!elements.length) return;

    const visible = new Map<string, number>();
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => visible.set(e.target.id, e.intersectionRatio));
        // Pick the section with the highest intersection ratio currently.
        let best = active;
        let bestRatio = -1;
        for (const [id, ratio] of visible) {
          if (ratio > bestRatio) {
            best = id;
            bestRatio = ratio;
          }
        }
        if (bestRatio > 0) setActive(best);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] }
    );
    elements.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const onNavClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    setOpen(false);
    history.pushState(null, "", `#${id}`);
    scrollToSection(id);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    history.pushState(null, "", "#library");
    scrollToSection("library");
    setOpen(false);
  };

  return (
    <header
      className={clsx(
        "fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300",
        scrolled ? "border-line bg-bg/90 backdrop-blur-md" : "border-transparent bg-bg"
      )}
    >
      <div className="mx-auto flex h-20 max-w-7xl items-center gap-8 px-6">
        <a
          href="#dashboard"
          onClick={(e) => onNavClick(e, "dashboard")}
          className="group flex items-baseline gap-1.5"
        >
          <span className="display text-3xl tracking-tight text-ink">FLUX</span>
          <span className="display text-3xl leading-none text-red transition group-hover:rotate-12">.</span>
        </a>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((n) => {
            const isActive = active === n.id;
            return (
              <a
                key={n.id}
                href={`#${n.id}`}
                onClick={(e) => onNavClick(e, n.id)}
                className={clsx(
                  "relative px-3 py-2 text-[12px] font-semibold uppercase tracking-widest transition-colors",
                  isActive ? "text-ink" : "text-ink-muted hover:text-ink"
                )}
              >
                {n.label}
                {isActive && <span className="absolute inset-x-3 -bottom-[26px] h-[2px] bg-red" />}
              </a>
            );
          })}
        </nav>

        <form onSubmit={submit} className="ml-auto hidden flex-1 md:block md:max-w-xs">
          <div className="group flex items-center gap-2 border-b border-line py-1.5 transition focus-within:border-red">
            <Search className="h-4 w-4 text-ink-faint group-focus-within:text-red" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search library…"
              className="w-full bg-transparent text-sm text-ink placeholder:text-ink-faint outline-none"
            />
          </div>
        </form>

        {channelUrl && (
          <a
            href={channelUrl}
            target="_blank"
            rel="noreferrer"
            aria-label="Flux Channel on YouTube"
            title="Flux Channel on YouTube"
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-line text-ink-muted transition hover:border-red/40 hover:bg-red-tint hover:text-red md:inline-flex"
          >
            <Youtube className="h-4 w-4" />
          </a>
        )}

        <a
          href="#creator"
          onClick={(e) => onNavClick(e, "creator")}
          className="hidden items-center gap-1.5 rounded-full bg-red px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-white shadow-red hover:bg-red-hover md:inline-flex"
        >
          Create <ArrowUpRight className="h-3.5 w-3.5" />
        </a>

        <button
          onClick={() => setOpen((v) => !v)}
          className="ml-auto inline-flex h-9 w-9 items-center justify-center md:hidden"
          aria-label="menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-line bg-bg md:hidden">
          <nav className="mx-auto flex max-w-7xl flex-col px-6 py-4">
            {NAV.map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                onClick={(e) => onNavClick(e, n.id)}
                className={clsx(
                  "border-b border-line py-3 text-base font-semibold uppercase tracking-widest",
                  active === n.id ? "text-red" : "text-ink-soft"
                )}
              >
                {n.label}
              </a>
            ))}
            <form onSubmit={submit} className="mt-4">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search library…"
                className="input-line"
              />
            </form>
          </nav>
        </div>
      )}
    </header>
  );
}
