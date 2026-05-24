import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Impact", "sans-serif"],
        mono:    ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          DEFAULT:  "#101013",  // greyer than pure black
          raised:   "#17171B",
          card:     "#1E1E23",
          hover:    "#27272D",
          elevated: "#22222A",
        },
        ink: {
          DEFAULT: "#FAFAFA",
          soft:    "#D4D4D8",   // zinc-300
          muted:   "#A1A1AA",   // zinc-400
          faint:   "#71717A",   // zinc-500
          dim:     "#3F3F46",   // zinc-700
        },
        line: {
          DEFAULT: "rgba(255,255,255,0.06)",
          strong:  "rgba(255,255,255,0.12)",
          soft:    "rgba(255,255,255,0.03)",
        },
        red: {
          DEFAULT: "#B91C1C",   // red-700, deep sober
          hover:   "#DC2626",   // red-600 on hover
          deep:    "#7F1D1D",   // red-900
          ink:     "#5F1A1A",
          tint:    "rgba(185,28,28,0.10)",
          tint2:   "rgba(185,28,28,0.18)",
          glow:    "rgba(185,28,28,0.40)",
          yt:      "#FF0000",
        },
      },
      letterSpacing: {
        tightest: "-0.04em",
        tighter:  "-0.025em",
        tight:    "-0.015em",
        wide:     "0.04em",
        wider:    "0.08em",
        widest:   "0.16em",
        eyebrow:  "0.22em",
      },
      fontSize: {
        "display-xl": ["clamp(80px, 11vw, 180px)", { lineHeight: "0.88", letterSpacing: "-0.02em" }],
        "display-lg": ["clamp(56px, 7vw, 120px)",  { lineHeight: "0.90", letterSpacing: "-0.01em" }],
        "display":    ["clamp(40px, 5vw, 80px)",   { lineHeight: "0.94", letterSpacing: "-0.005em" }],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "10px",
        xl: "14px",
        "2xl": "20px",
        "3xl": "28px",
      },
      boxShadow: {
        "soft":   "0 1px 2px rgba(0,0,0,0.4)",
        "card":   "0 1px 2px rgba(0,0,0,0.6), 0 8px 24px -8px rgba(0,0,0,0.5)",
        "raised": "0 1px 2px rgba(0,0,0,0.6), 0 20px 48px -16px rgba(0,0,0,0.8)",
        "red":    "0 1px 2px rgba(185,28,28,0.20), 0 10px 28px -10px rgba(185,28,28,0.50)",
        "red-glow": "0 0 0 1px rgba(185,28,28,0.4), 0 0 40px -8px rgba(185,28,28,0.55)",
      },
      animation: {
        "fade-up": "fadeUp 0.7s cubic-bezier(0.22,1,0.36,1) both",
        "marquee": "marquee 70s linear infinite",
        "pulse-red": "pulseRed 2.2s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%":   { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        pulseRed: {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(185,28,28,0.4)" },
          "50%":     { boxShadow: "0 0 0 14px rgba(185,28,28,0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
