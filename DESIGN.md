---
version: alpha
name: Daily AI Notes
description: A personal notebook, not a newsfeed. Paper ground, ink type, hairline rules and one ink-blue accent.
colors:
  primary: "{colors.accent}"
  bg: "#F5F5F1"
  surface: "#FCFCFA"
  sunk: "#ECECE6"
  line: "#DDDDD5"
  line-2: "#C6C6BC"
  ink: "#16171A"
  ink-2: "#42444A"
  ink-3: "#5F6168"
  accent: "#2346C8"
  accent-ink: "#FFFFFF"
  accent-soft: "#E7EBF8"
  ok: "#2C6A39"
  ok-soft: "#E2EEE3"
  warn: "#865400"
  warn-soft: "#F5EAD3"
  bad: "#A12F1C"
  bad-soft: "#F6E1DB"
  grid: "rgba(22, 23, 26, 0.07)"
  t1: "#EB6834"
  t2: "#1BAF7A"
  t3: "#6250D6"
  t4: "#EDA100"
  t5: "#E87BA4"
  t6: "#008300"
  t7: "#E34948"
  t8: "#2A78D6"
  dark-bg: "#111214"
  dark-surface: "#17191C"
  dark-sunk: "#0C0D0F"
  dark-line: "#2A2D32"
  dark-line-2: "#3B3F46"
  dark-ink: "#ECECE7"
  dark-ink-2: "#BDBFBA"
  dark-ink-3: "#9A9C9F"
  dark-accent: "#91A8FF"
  dark-accent-ink: "#0E1430"
  dark-accent-soft: "#1B2340"
  dark-ok: "#82C691"
  dark-ok-soft: "#16261A"
  dark-warn: "#E3B566"
  dark-warn-soft: "#2A2213"
  dark-bad: "#F2907C"
  dark-bad-soft: "#2E1915"
  dark-grid: "rgba(236, 236, 231, 0.06)"
  dark-t1: "#D95926"
  dark-t2: "#199E70"
  dark-t3: "#9085E9"
  dark-t4: "#C98500"
  dark-t5: "#D55181"
  dark-t6: "#008300"
  dark-t7: "#E66767"
  dark-t8: "#3987E5"
typography:
  display:
    fontFamily: Newsreader
    fontSize: 38px
    fontWeight: 500
    lineHeight: 42px
    letterSpacing: -0.015em
  display-desktop:
    fontFamily: Newsreader
    fontSize: 60px
    fontWeight: 500
    lineHeight: 64px
    letterSpacing: -0.015em
  h1:
    fontFamily: Newsreader
    fontSize: 30px
    fontWeight: 500
    lineHeight: 36px
    letterSpacing: -0.01em
  h1-desktop:
    fontFamily: Newsreader
    fontSize: 42px
    fontWeight: 500
    lineHeight: 48px
    letterSpacing: -0.01em
  h2:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: 500
    lineHeight: 30px
  h2-desktop:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: 500
    lineHeight: 34px
  title:
    fontFamily: Newsreader
    fontSize: 20px
    fontWeight: 500
    lineHeight: 26px
  title-desktop:
    fontFamily: Newsreader
    fontSize: 23px
    fontWeight: 500
    lineHeight: 29px
  reading:
    fontFamily: Newsreader
    fontSize: 18px
    fontWeight: 400
    lineHeight: 29px
  reading-desktop:
    fontFamily: Newsreader
    fontSize: 19px
    fontWeight: 400
    lineHeight: 31px
  ui:
    fontFamily: Hanken Grotesk
    fontSize: 15px
    fontWeight: 400
    lineHeight: 22px
  small:
    fontFamily: Hanken Grotesk
    fontSize: 13px
    fontWeight: 400
    lineHeight: 18px
  meta:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
    fontFeature: "'tnum' 1"
  badge:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: 500
    lineHeight: 16px
    fontFeature: "'tnum' 1"
  label:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: 500
    lineHeight: 14px
    letterSpacing: 0.08em
rounded:
  xs: 3px
  sm: 6px
  md: 10px
  pill: 999px
spacing:
  space-1: 4px
  space-2: 8px
  space-3: 12px
  space-4: 16px
  space-5: 20px
  space-6: 24px
  space-7: 32px
  space-8: 48px
  space-9: 64px
  space-10: 96px
  margin-phone: 20px
  margin-tablet: 32px
  rail: 300px
  max-width: 1160px
  measure: 680px
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.sm}"
    height: 44px
    padding: 16px
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.sm}"
    height: 44px
    padding: 16px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.sm}"
    height: 44px
    padding: 12px
  citation-chip:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    typography: "{typography.badge}"
    rounded: "{rounded.xs}"
    height: 22px
    padding: 6px
  citation-chip-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.badge}"
    rounded: "{rounded.xs}"
    height: 22px
    padding: 6px
  badge-verified:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    typography: "{typography.badge}"
    rounded: "{rounded.xs}"
    height: 24px
    padding: 8px
  badge-partial:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    typography: "{typography.badge}"
    rounded: "{rounded.xs}"
    height: 24px
    padding: 8px
  badge-unsupported:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
    typography: "{typography.badge}"
    rounded: "{rounded.xs}"
    height: 24px
    padding: 8px
  topic-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: 40px
    padding: 14px
  topic-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.pill}"
    height: 40px
    padding: 14px
  topic-tab:
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: 36px
    padding: 12px
  topic-tab-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.pill}"
    height: 36px
    padding: 12px
  catalog-tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: 104px
    padding: 14px
  stat-tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 18px
  chat-question:
    backgroundColor: "{colors.sunk}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    padding: 16px
  note-card:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    padding: 20px
  state-error:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 18px
  skeleton:
    backgroundColor: "{colors.sunk}"
    rounded: "{rounded.xs}"
---

# Daily AI Notes design system

Written from the v2 page ("Any topic (current)") of the owner's Claude Design canvas, tokens v2.0 of 2026-10-12. Token names are the canvas's own CSS variables without the `--`: `ink-2` here is `--ink-2` there, and every `dark-` token is the same variable under `.dan.dark`.

## Overview

A personal notebook, not a newsfeed. Paper ground, ink type, hairline rules and one ink-blue accent, like a well-kept lab notebook. Serif for reading, a quiet sans for controls, monospace for anything counted or dated. Each topic carries a small color tag so a busy reader can scan a day at a glance.

The product is calm and factual: notes are short, every sentence is cited, and the interface says plainly what it does not know. Design for a phone at 390 px first; desktop adds a side column, not new ideas.

## Colors

Two themes, both designed rather than inverted: **Light · Paper** (default) and **Dark · Carbon** (`prefers-color-scheme: dark`, plus a toggle in the header).

- **Ground (`bg` #F5F5F1, dark #111214):** the page. Paper in light, carbon in dark.
- **Surface (`surface` #FCFCFA):** raised things: inputs, popovers, tiles, secondary buttons.
- **Sunk (`sunk` #ECECE6):** wells, skeletons, quiet panels, the reader's own chat question.
- **Lines (`line` #DDDDD5, `line-2` #C6C6BC):** `line` for hairline dividers between items, `line-2` for control borders.
- **Ink (`ink` #16171A, `ink-2` #42444A, `ink-3` #5F6168):** primary text and section rules; summaries and secondary text; metadata, the lightest text allowed.
- **Accent (`accent` #2346C8, ink blue; dark #91A8FF):** rationed. Links, citation markers, the active tab, the one primary action on a screen, focus rings. Never a fill behind a headline. `primary` is an alias of `accent` for tools that expect one. `accent-soft` tints citation chips and highlighted quotes; `accent-ink` is text on an accent fill.
- **Verdicts:** `ok` for verified or supported, `warn` for partial or weak, `bad` for unsupported or an error. Each has a `-soft` background; the strong color is the text on it.
- **Grid (`grid`, ink at 7%):** only for the graph-paper texture.
- **Topic tags (`t1` to `t8`):** eight slots, given in the order the reader picked their topics, that stay put when another topic is removed. A topic keeps its color everywhere. A tag is a 10 px square beside the topic name, or a 14% tint on the active topic tab. It is never text color, never a card fill, and never shown without the name. The eight slots pass colorblind and normal-vision separation checks in both themes.

The `dark-` tokens, `t1` to `t8`, and `line`, `line-2`, `ink-2`, `ink-3` and `grid` are applied through CSS variables (borders, secondary text, the texture, the dark theme) rather than component definitions, so the linter reports them as orphaned. That is expected.

## Typography

Three families from Google Fonts, downloaded when the site is built and served from its own origin, so a visit sends nothing to Google: **Newsreader** (optical sizes 6 to 72, weights 400, 500, 600 and italic 400), **Hanken Grotesk** (400, 500, 600) and **IBM Plex Mono** (400, 500).

- **Newsreader, for reading and display:** dates, titles, note bodies, and quoted excerpts in italic.
- **Hanken Grotesk, for the interface:** summaries, buttons, inputs, chat answers, topic names.
- **IBM Plex Mono, for anything counted or dated:** dates, times, source counts, citation numbers, agent names, with tabular figures.

Phone sizes are the default tokens; `-desktop` tokens replace them from 960 px. `label` is set in capitals and labels a section ("SOURCES", "HOW THIS NOTE WAS MADE"). `badge` is the weight-500 mono used inside citation chips and verdict badges. Topic chips use Hanken at 14 px; chat messages use it at 16 px with a 23 to 26 px line height.

## Layout

A 4 px base. Cards breathe at 20 to 24 px on phones; sections at 48 to 96 px.

| Width | Layout |
|---|---|
| Under 600 px | One column, 20 px margins, bottom tab bar (Today, Topics, Ask) |
| 600 to 959 px | One column, 32 px margins, top navigation |
| 960 px and up | Feed plus a 300 px rail, at most 1160 px wide |

The reading column is at most 680 px, about 66 characters. The daily page is a phone page that grows a side column on desktop.

The signature texture is a 16 px graph-paper grid at 7% ink (`grid`). Use it once per screen, behind the date or the page header, and on empty and "not enough" states.

## Elevation & Depth

No shadows. Hierarchy comes from hairlines and type: a 1 px `line` divides items, and a 2 px `ink` rule opens each section and sits under month headings in timelines. Raised things use `surface` with a 1 px `line-2` border; the reader's chat question sits on `sunk`.

## Shapes

- **`xs` (3 px):** citation markers, verdict badges, tag squares (2 px on the 10 px square), skeleton bars.
- **`sm` (6 px):** inputs, buttons, popovers.
- **`md` (10 px):** catalog tiles, panels, stat tiles, empty and error states.
- **`pill` (999 px):** topic chips and topic tabs only.

The reader's chat question has one sharp corner: 12 px on three corners and 3 px at the bottom right, pointing at the reader's side.

Focus is a 2 px `accent` outline with a 2 px offset. Every tap target is at least 44 px.

## Components

- **Buttons:** `button-primary` is the one accent action on a screen; `button-secondary` has a 1 px `line-2` border. Both are 44 px tall with 16 px of horizontal padding.
- **Note card:** a borderless article between hairlines, 20 px above and below. Top row: the topic (tag square and name, 13 px, weight 500) and the time in `meta`. Then the title in `title`, a two-line summary in `ui` at `ink-2`, and a footer with overlapping publisher favicons, a source count and a verdict badge.
- **Citation chip:** the number in `badge` on `accent-soft`, inline in the text, 22 px tall. Pressed, it turns `citation-chip-active` and opens the expanded citation below the paragraph: a `surface` panel with a 1 px `line-2` border and `sm` corners, holding the publisher and date, the source title, the quoted passage in italic Newsreader with the cited words highlighted in `accent-soft`, the location in the source and "Open source ↗".
- **Verdict badges:** a 14 px stroke icon and a word: Verified, Partially verified, Unsupported.
- **Publisher favicons:** 20 px circles that overlap by 5 px, ringed in `bg`. Phase 1 shows the publisher's initial in mono on `sunk`, since fetching favicons would send each visit to other sites.
- **Topic chips:** a catalog chip (`topic-chip`, 1 px `line-2` border), a selected chip (`topic-chip-selected`, with a check mark) and an "add" chip with a dashed border. Custom topics are not part of phase 1.
- **Topic tabs:** "All" plus one tab per topic, each with a count in mono. A selected topic tab takes its tag color at 14% with a 1 px border in the tag color.
- **Catalog tile:** a name in Hanken 15/600, one line of what it covers, and the expected volume ("~2 notes / day") in mono. Selected, it gets a 2 px `ink` border and a filled check.
- **Timeline item:** the date and weekday in mono on the left, a tag square on a 1 px `line-2` stem, then the title in Newsreader 18/24 and its source count and verdict.
- **Chat:** the question on `sunk` at the right, at most 80% wide; the answer in Hanken 16/26 with citation chips, then a row of linked note chips (number, tag square, short title, date).
- **Stat tile:** a `label`, a value in Newsreader 40/44 with tabular figures, and either a line of context or a 28 px sparkline in `accent`.
- **States:** "first day" (graph paper, a 4 px progress bar in `ink` on `sunk`); "loading" (skeleton bars on `sunk` that pulse unless reduced motion is set); "error" (`state-error`, a 1 px `bad` border, and the reassurance that the notes are safe); a "source unreachable" strip on `sunk` with a `warn` icon.

## Iconography

Inline stroke SVG at 1.4 to 1.7 px in `currentColor`, 14 to 18 px, `aria-hidden` when next to a label. No emoji, no icon font. The logo is a notebook square with three ruled lines and an ink-blue margin line, beside "Daily AI Notes" in Newsreader 500.

## Voice and copy

Plain, specific and honest about gaps.

- Say what is missing: "Not enough in your notes to answer that." "'Nothing new' means no source published on that topic in the last 24 hours. We don't pad your page."
- Show the work in numbers: "9 reports from 7 publishers merged · 4 cited", "Fact-check: 6 supported · 0 weak · 0 unsupported".
- Every note is approved by a person in phase 1, so the note screen says "Approved by the editor", not the canvas's "published automatically".
- Dates are absolute ("Mon 12 Oct 2026"), never "yesterday".

## Screens

The v2 screens are current; phase 1 builds them without the parts that need an account.

| Screen | Canvas artboards | Phase 1 |
|---|---|---|
| Daily page | 03 phone, 03d desktop, 03b first day (phone, dark) | Built; topics come from the browser; no feedback buttons |
| Note detail | 04 phone, 04d desktop (dark) | Built, with "How this note was made" and the sources list; no feedback buttons |
| Topic picker | 05 phone, 05d desktop | Built as the catalog picker; no custom topic and no delivery-time step |
| Ask your notes | 06 phone (dark), 06d desktop | Built; "Follow" adds the topic to the browser's list |

The page "Later screens · v1, to revise" (Topic timeline, Archive, How it works, Admin review queue) is layout reference only until the owner revises it. Phase 1 builds a topic timeline and a How it works page in the v2 style, and the minimal /admin approval page from the same components.

## Do's and Don'ts

- Do keep the accent for links, citations, the active tab, focus and the one primary action.
- Do show the topic name next to every tag color.
- Do keep every interactive target at least 44 px and the focus ring visible.
- Do keep metadata in mono with tabular figures, so columns of numbers line up.
- Don't use shadows, gradients or card fills to separate content; use hairlines.
- Don't use the graph-paper texture more than once per screen.
- Don't color text with a topic color, and don't fill a card with one.
- Don't show a number, date or claim without its source on a screen that shows notes.
