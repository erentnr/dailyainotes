/** Stroke icons in currentColor (DESIGN.md, Iconography); hidden from screen readers. */
import type { ReactNode } from "react";

function Icon({ size = 14, width = 2, children }: { size?: number; width?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const Check = ({ size = 13 }: { size?: number }) => (
  <Icon size={size} width={2.4}>
    <path d="M4.3 10.4l3.7 3.7 7.7-7.8" />
  </Icon>
);

/** Half a circle filled: "partly". */
export const Half = ({ size = 13 }: { size?: number }) => (
  <Icon size={size} width={2}>
    <circle cx="10" cy="10" r="7.5" />
    <path d="M10 2.5a7.5 7.5 0 010 15z" fill="currentColor" />
  </Icon>
);

export const Cross = ({ size = 13 }: { size?: number }) => (
  <Icon size={size} width={2.2}>
    <path d="M5.5 5.5l9 9M14.5 5.5l-9 9" />
  </Icon>
);

export const External = () => (
  <Icon size={12} width={2}>
    <path d="M8 4H4v12h12v-4M11 4h5v5M16 4l-7 7" />
  </Icon>
);

/** Light or dark: a circle half filled. */
export const Contrast = () => (
  <Icon size={18} width={1.6}>
    <circle cx="10" cy="10" r="7.2" />
    <path d="M10 2.8v14.4a7.2 7.2 0 000-14.4z" fill="currentColor" />
  </Icon>
);

export const Search = () => (
  <Icon size={18} width={1.8}>
    <circle cx="8.9" cy="8.9" r="6.1" />
    <path d="M13.3 13.3l4.4 4.4" />
  </Icon>
);

export const Back = ({ size = 16 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M12.8 3.6L6.4 10l6.4 6.4" />
  </Icon>
);

export const Forward = ({ size = 16 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M7.2 3.6l6.4 6.4-6.4 6.4" />
  </Icon>
);

export const Share = () => (
  <Icon size={17} width={1.8}>
    <path d="M10 2.8v10M6.1 6.7L10 2.8l3.9 3.9M3.9 11.1v5h12.2v-5" />
  </Icon>
);

/** A page with nothing on it, for "not enough". */
export const EmptyPage = () => (
  <Icon size={24} width={1.8}>
    <rect x="3.5" y="2.5" width="13" height="15" rx="2.5" />
    <path d="M7 8h6M7 11.5h4" strokeDasharray="1.7 2.5" />
  </Icon>
);

/** The tab bar's icons. */
export const TodayIcon = () => (
  <Icon size={20} width={1.8}>
    <rect x="3" y="3" width="14" height="14" rx="3" />
    <path d="M6.5 7.5h7M6.5 10.5h7M6.5 13.5h4" />
  </Icon>
);

export const TopicsIcon = () => (
  <Icon size={20} width={1.8}>
    <circle cx="6.5" cy="6.5" r="3" />
    <circle cx="13.5" cy="6.5" r="3" />
    <circle cx="6.5" cy="13.5" r="3" />
    <circle cx="13.5" cy="13.5" r="3" />
  </Icon>
);

export const AskIcon = () => (
  <Icon size={20} width={1.8}>
    <path d="M3.5 4.5h13v9h-7l-4 3v-3h-2z" />
  </Icon>
);

export const YouIcon = () => (
  <Icon size={20} width={1.8}>
    <circle cx="10" cy="7" r="3.2" />
    <path d="M4 17c.8-3 3.2-4.5 6-4.5s5.2 1.5 6 4.5" />
  </Icon>
);

/** Angle brackets: the source link when the code is not on GitHub. */
export const CodeIcon = () => (
  <Icon size={16} width={1.8}>
    <path d="M7 6l-4 4 4 4M13 6l4 4-4 4" />
  </Icon>
);

/** GitHub's own mark (Octicons' mark-github, MIT), filled and drawn as GitHub draws it: the one
 * icon that is not a stroke (DESIGN.md, Iconography). */
export const GitHubMark = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false">
    <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
  </svg>
);
