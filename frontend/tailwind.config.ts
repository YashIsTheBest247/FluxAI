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
          DEFAULT:  "#1A1A1E",  // warm dark grey (lifted off pure black)
          raised:   "#222226",
          card:     "#2A2A30",
          hover:    "#34343A",
          elevated: "#2F2F35",
        },
        ink: {
          DEFAULT: "#F5F5F5",
          soft:    "#CBCBD0",   // slightly warmer than zinc-300
          muted:   "#9A9AA0",
          faint:   "#6B6B72",
          dim:     "#3A3A40",
        },
        line: {
          DEFAULT: "rgba(255,255,255,0.05)",
          strong:  "rgba(255,255,255,0.10)",
          soft:    "rgba(255,255,255,0.025)",
        },
        red: {
          DEFAULT: "#8B1F1F",   // deep grounded crimson (was #B91C1C neon-y)
          hover:   "#A52525",   // lifts slightly on hover
          deep:    "#5F1717",
          ink:     "#3F1010",
          tint:    "rgba(139,31,31,0.10)",
          tint2:   "rgba(139,31,31,0.18)",
          glow:    "rgba(139,31,31,0.35)",
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
        "red":    "0 1px 2px rgba(139,31,31,0.20), 0 10px 28px -10px rgba(139,31,31,0.45)",
        "red-glow": "0 0 0 1px rgba(139,31,31,0.4), 0 0 40px -8px rgba(139,31,31,0.45)",
      },
      animation: {
        "fade-up": "fadeUp 0.7s cubic-bezier(0.22,1,0.36,1) both",
        "marquee": "marquee 40s linear infinite",
        "pulse-red": "pulseRed 2.2s ease-in-out infinite",
        "blink": "blink 1s steps(1) infinite",
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
          "0%,100%": { boxShadow: "0 0 0 0 rgba(139,31,31,0.35)" },
          "50%":     { boxShadow: "0 0 0 14px rgba(139,31,31,0)" },
        },
        blink: {
          "0%, 49%":   { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
