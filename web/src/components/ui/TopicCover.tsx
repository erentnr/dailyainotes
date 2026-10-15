import { type ReactNode, useId } from "react";

import {
  coverColor,
  HOME_SLOT,
  type Motif,
  NIGHT,
  nudge,
  type Palette,
  PALETTES,
  paletteOf,
} from "../../lib/covers";

const INK = "#111";
// Grounds, bands and patterns reach past the 360 units of the art, for the wide hero.
const WIDE = { x: -400, width: 1160 };

/** A wave across the whole width: a crest every 90 units, `amp` above the line at `y`. */
function wave(y: number, amp: number): string {
  let d = `M${WIDE.x} ${y} Q${WIDE.x + 45} ${y - amp} ${WIDE.x + 90} ${y}`;
  for (let x = WIDE.x + 180; x <= WIDE.x + WIDE.width; x += 90) d += ` T${x} ${y}`;
  return `${d} V200 H${WIDE.x}Z`;
}

/** Shapes that repeat to each side of the art, for the wide hero. */
const REPEATS = [-360, 0, 360];

interface Art {
  p: Palette;
  dy: number;
  /** Where the main shape sits across: its place in the canvas art, or the middle of a tile. */
  x: (canvasX: number) => number;
  id: string;
  name: string;
}

/** A topic's drawn cover (DESIGN.md, Covers). Decoration only: hidden from screen readers. */
export function TopicCover({
  motif,
  slot,
  seed = 0,
  variant = "card",
  name = "",
}: {
  motif: Motif;
  slot?: number | undefined;
  seed?: number;
  variant?: "hero" | "card" | "tile" | "circle";
  /** The topic's name; the plain cover shows its first letter. */
  name?: string;
}) {
  // Pattern ids must be unique on the page, and url(#…) takes no colons.
  const id = `cover${useId().replace(/[^\w-]/g, "")}`;
  if (variant === "circle") {
    return (
      <span className="cover-circle" style={{ background: coverColor(motif, slot) }} aria-hidden="true" />
    );
  }
  const { dx, dy } = nudge(seed);
  // A square tile shows only the middle 200 units of the 360-wide art, so its shape moves to
  // the middle and the seed moves it a quarter as far, keeping wide shapes inside the tile.
  const x = variant === "tile" ? (_: number) => 180 + dx / 4 : (canvasX: number) => canvasX + dx;
  const art: Art = { p: paletteOf(motif, slot), dy, x, id, name };
  return (
    <svg
      className="cover"
      // A hero is a wide banner: it shows more of the art to each side instead of zooming in.
      viewBox={variant === "hero" ? "-220 0 800 200" : "0 0 360 200"}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      {DRAW[motif](art)}
    </svg>
  );
}

const DRAW: Record<Motif, (art: Art) => ReactNode> = {
  moto: ({ p, dy, x, id }) => {
    const cx = x(236);
    return (
      <>
        <defs>
          <pattern id={id} width="24" height="24" patternUnits="userSpaceOnUse">
            <rect width="24" height="24" fill={p.base} />
            <rect width="12" height="12" fill={INK} />
            <rect x="12" y="12" width="12" height="12" fill={INK} />
          </pattern>
        </defs>
        <rect {...WIDE} height="200" fill={p.base} />
        {REPEATS.map((shift) => (
          <g key={shift} transform={`translate(${shift} 0)`}>
            <path d="M30 200 L170 0 H222 L82 200Z" fill={p.dark} />
            <path d="M110 200 L250 0 H280 L140 200Z" fill={p.dark} />
            <path d="M180 200 L320 0 H334 L194 200Z" fill={p.deep} />
          </g>
        ))}
        <circle cx={cx} cy={84 + dy} r="46" fill="none" stroke={INK} strokeWidth="14" />
        <circle cx={cx} cy={84 + dy} r="15" fill={INK} />
        <rect x={WIDE.x} y="166" width={WIDE.width} height="34" fill={`url(#${id})`} />
      </>
    );
  },

  waves: ({ p, dy, x }) => (
    <>
      <rect {...WIDE} height="200" fill={p.base} />
      <circle cx={x(236)} cy={66 + dy / 2} r="30" fill={p.glow} />
      <path d={wave(118, 26)} fill={p.light} />
      <path d={wave(146, 22)} fill={p.dark} />
      <path d={wave(172, 16)} fill={p.deep} />
    </>
  ),

  bars: ({ p, x }) => {
    // The four bars and the line move together; x(174) is the middle of the group.
    const shift = x(174) - 174;
    return (
      <>
        <rect {...WIDE} height="200" fill={p.base} />
        <g transform={`translate(${shift} 0)`}>
          <rect x="96" y="128" width="30" height="72" fill={p.light} />
          <rect x="138" y="104" width="30" height="96" fill={p.light} />
          <rect x="180" y="78" width="30" height="122" fill={p.light} />
          <rect x="222" y="48" width="30" height="152" fill={p.lighter} />
          <polyline
            points="80,136 126,118 170,98 214,70 270,34"
            fill="none"
            stroke={p.glow}
            strokeWidth="7"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </g>
      </>
    );
  },

  dots: ({ p, dy, x, id }) => {
    const shift = x(190) - 190;
    const points: [number, number][] = [
      [110, 150],
      [150, 110],
      [190, 130],
      [230, 70],
      [270, 90],
    ];
    const moved = points.map(([px, py]) => [px + shift, py + dy / 2] as const);
    return (
      <>
        <defs>
          <pattern id={id} width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="10" cy="10" r="2.2" fill={INK} opacity=".28" />
          </pattern>
        </defs>
        <rect {...WIDE} height="200" fill={p.base} />
        <rect {...WIDE} height="200" fill={`url(#${id})`} />
        <polyline
          points={moved.map((pt) => pt.join(",")).join(" ")}
          fill="none"
          stroke={INK}
          strokeWidth="4"
          strokeLinejoin="round"
        />
        {moved.map(([cx, cy], i) =>
          i === 3 ? (
            <circle key={i} cx={cx} cy={cy} r="11" fill={INK} />
          ) : (
            <circle key={i} cx={cx} cy={cy} r="8" fill="#fff" stroke={INK} strokeWidth="3" />
          ),
        )}
      </>
    );
  },

  pitch: ({ p, dy, x }) => (
    <>
      <rect {...WIDE} height="200" fill={p.base} />
      <g fill="none" stroke="#fff" strokeWidth="3">
        <rect x="70" y="20" width="220" height="160" />
        <line x1="180" y1="20" x2="180" y2="180" />
        <circle cx="180" cy="100" r="30" />
        <rect x="70" y="60" width="34" height="80" />
        <rect x="256" y="60" width="34" height="80" />
      </g>
      {/* The pitch stays put; the ball moves, and stays inside the lines on a tile too. */}
      <circle cx={x(214)} cy={88 + dy} r="8" fill={INK} />
    </>
  ),

  space: ({ p, dy, x }) => {
    const hx = x(220);
    const hy = 76 + dy / 2;
    return (
      <>
        <rect {...WIDE} height="200" fill={NIGHT} />
        <ellipse
          cx="180"
          cy="104"
          rx="130"
          ry="46"
          fill="none"
          // In its home slot the orbit is the canvas's; elsewhere it takes the slot's tone.
          stroke={p === PALETTES[HOME_SLOT.space] ? "#2E3B7A" : p.dark}
          strokeWidth="2"
        />
        <path d={`M${hx - 120} ${hy + 88} L${hx - 4} ${hy - 4} L${hx + 4} ${hy + 4}Z`} fill="#FFE08A" opacity=".3" />
        <path d={`M${hx - 74} ${hy + 74} L${hx - 4} ${hy - 2} L${hx + 1} ${hy + 3}Z`} fill="#FFE08A" opacity=".55" />
        <circle cx={hx} cy={hy} r="10" fill="#FFE08A" />
        {REPEATS.map((shift) => (
          <g key={shift} fill="#fff" transform={`translate(${shift} 0)`}>
            {STARS.map(([cx, cy, r]) => (
              <circle key={`${cx},${cy}`} cx={cx} cy={cy} r={r} />
            ))}
          </g>
        ))}
      </>
    );
  },

  rings: ({ p, dy, x }) => {
    const cx = x(182);
    const cy = 100 + dy / 2;
    return (
      <>
        <rect {...WIDE} height="200" fill={p.base} />
        <circle cx={cx - 32} cy={cy} r="58" fill={p.light} />
        <circle cx={cx + 32} cy={cy} r="58" fill="none" stroke={INK} strokeWidth="12" />
        <circle cx={cx} cy={cy} r="14" fill="#fff" />
      </>
    );
  },

  custom: ({ p, id, name }) => (
    <>
      <defs>
        <pattern
          id={id}
          width="14"
          height="14"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <rect width="14" height="14" fill={p.base} />
          <rect width="5" height="14" fill={p.dark} />
        </pattern>
      </defs>
      <rect {...WIDE} height="200" fill={`url(#${id})`} />
      <circle cx="180" cy="100" r="62" fill={p.base} />
      <text
        x="180"
        y="100"
        dy="0.35em"
        textAnchor="middle"
        fill="#fff"
        fontFamily="var(--font-sans), ui-sans-serif, system-ui"
        fontWeight="900"
        fontSize="92"
      >
        {name.trim().slice(0, 1).toUpperCase()}
      </text>
    </>
  ),
};

const STARS: [number, number, number][] = [
  [40, 30, 1.8],
  [90, 60, 1.2],
  [300, 34, 2],
  [326, 150, 1.4],
  [60, 120, 1.2],
  [170, 24, 1.5],
  [24, 176, 1.6],
  [250, 170, 1.1],
  [128, 92, 1],
];
