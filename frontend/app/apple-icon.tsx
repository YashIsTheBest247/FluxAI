import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

/**
 * Dot-matrix "F" — bright red glowing dots on a dark background.
 * Pattern (3 cols × 4 rows):
 *   ● ● ●
 *   ● ● ●
 *   ● ●
 *   ●
 */
const PATTERN: boolean[][] = [
  [true, true, true],
  [true, true, true],
  [true, true, false],
  [true, false, false],
];

const DOT = 22;
const GAP_X = 16;
const GAP_Y = 12;

function Dot({ on }: { on: boolean }) {
  return (
    <div
      style={{
        width: DOT,
        height: DOT,
        borderRadius: DOT / 2,
        background: on ? "#A52525" : "transparent",
        boxShadow: on ? `0 0 22px rgba(165,37,37,0.45)` : "none",
      }}
    />
  );
}

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background:
            "radial-gradient(circle at 50% 50%, #1a0d0d 0%, #08050a 100%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: GAP_Y,
        }}
      >
        {PATTERN.map((row, i) => (
          <div key={i} style={{ display: "flex", gap: GAP_X }}>
            {row.map((on, j) => (
              <Dot key={j} on={on} />
            ))}
          </div>
        ))}
      </div>
    ),
    { ...size }
  );
}
