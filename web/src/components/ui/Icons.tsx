/** Stroke icons in currentColor (DESIGN.md, Iconography); hidden from screen readers. */
import type { ReactNode } from "react";

function Icon({ size = 14, children }: { size?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const Check = () => (
  <Icon>
    <path d="M3 8.5l3 3 7-7" />
  </Icon>
);

export const Half = () => (
  <Icon>
    <circle cx="8" cy="8" r="5.5" />
    <path d="M8 2.5v11" />
  </Icon>
);

export const Cross = () => (
  <Icon>
    <path d="M4 4l8 8M12 4l-8 8" />
  </Icon>
);

export const External = () => (
  <Icon size={12}>
    <path d="M6 3H3v10h10v-3M9 3h4v4M13 3L7 9" />
  </Icon>
);

export const Moon = () => (
  <Icon size={18}>
    <path d="M13 9.5A5.5 5.5 0 016.5 3a5.5 5.5 0 106.5 6.5z" />
  </Icon>
);

export const Sun = () => (
  <Icon size={18}>
    <circle cx="8" cy="8" r="3" />
    <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1" />
  </Icon>
);
