---
version: alpha
name: Daily AI Notes
description: Covers. White rounded cards on a warm grey ground, one heavy grotesque, and a drawn cover for every topic.
colors:
  primary: "{colors.acc}"
  bg: "#EFEEE9"
  card: "#FFFFFF"
  sunk: "#E6E4DE"
  ink: "#121212"
  ink2: "#4A4945"
  ink3: "#6B6963"
  line: "#E0DED7"
  line2: "#CFCCC4"
  acc: "#1F4BFF"
  acc-ink: "#FFFFFF"
  acc-soft: "#E6ECFF"
  ok: "#1E7A45"
  ok-soft: "#E1F2E7"
  warn: "#8A5A00"
  warn-soft: "#FBEFD5"
  bad: "#B3261E"
  bad-soft: "#FBE3E1"
  s1: "#FF5A1F"
  s2: "#17A673"
  s3: "#5B4BE0"
  s4: "#D99A00"
  s5: "#F06BA0"
  s6: "#3A4CC0"
  s7: "#0FA3A3"
  s8: "#D93A3A"
  dark-bg: "#0F0F0E"
  dark-card: "#1A1A18"
  dark-sunk: "#242422"
  dark-ink: "#F2F1EC"
  dark-ink2: "#C2C0B9"
  dark-ink3: "#96948D"
  dark-line: "#2A2A27"
  dark-line2: "#3A3A36"
  dark-acc: "#8EA4FF"
  dark-acc-ink: "#0B1233"
  dark-acc-soft: "#1E2747"
  dark-ok: "#7FD39B"
  dark-ok-soft: "#14281B"
  dark-warn: "#F0C060"
  dark-warn-soft: "#2B2312"
  dark-bad: "#FF8F86"
  dark-bad-soft: "#2E1614"
  dark-s1: "#E8561C"
  dark-s2: "#149A6A"
  dark-s3: "#7B6EF0"
  dark-s4: "#B88000"
  dark-s5: "#D9578E"
  dark-s6: "#5266DD"
  dark-s7: "#12999A"
  dark-s8: "#D84545"
typography:
  greeting:
    fontFamily: Schibsted Grotesk
    fontSize: 38px
    fontWeight: 900
    lineHeight: 40px
    letterSpacing: -0.035em
  greeting-desktop:
    fontFamily: Schibsted Grotesk
    fontSize: 64px
    fontWeight: 900
    lineHeight: 64px
    letterSpacing: -0.045em
  h1:
    fontFamily: Schibsted Grotesk
    fontSize: 33px
    fontWeight: 900
    lineHeight: 36px
    letterSpacing: -0.04em
  h1-desktop:
    fontFamily: Schibsted Grotesk
    fontSize: 52px
    fontWeight: 900
    lineHeight: 54px
    letterSpacing: -0.045em
  lead:
    fontFamily: Schibsted Grotesk
    fontSize: 27px
    fontWeight: 800
    lineHeight: 30px
    letterSpacing: -0.03em
  lead-desktop:
    fontFamily: Schibsted Grotesk
    fontSize: 38px
    fontWeight: 850
    lineHeight: 40px
    letterSpacing: -0.04em
  title:
    fontFamily: Schibsted Grotesk
    fontSize: 17px
    fontWeight: 750
    lineHeight: 21px
    letterSpacing: -0.02em
  title-desktop:
    fontFamily: Schibsted Grotesk
    fontSize: 21px
    fontWeight: 800
    lineHeight: 25px
    letterSpacing: -0.03em
  section:
    fontFamily: Schibsted Grotesk
    fontSize: 20px
    fontWeight: 800
    lineHeight: 24px
    letterSpacing: -0.02em
  reading:
    fontFamily: Schibsted Grotesk
    fontSize: 18px
    fontWeight: 400
    lineHeight: 29px
  reading-desktop:
    fontFamily: Schibsted Grotesk
    fontSize: 19px
    fontWeight: 400
    lineHeight: 31px
  ui:
    fontFamily: Schibsted Grotesk
    fontSize: 15px
    fontWeight: 400
    lineHeight: 22px
  ui-strong:
    fontFamily: Schibsted Grotesk
    fontSize: 14px
    fontWeight: 700
    lineHeight: 20px
  small:
    fontFamily: Schibsted Grotesk
    fontSize: 13px
    fontWeight: 400
    lineHeight: 18px
  tag:
    fontFamily: Schibsted Grotesk
    fontSize: 12px
    fontWeight: 700
    lineHeight: 16px
    letterSpacing: 0.02em
  meta:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 16px
    fontFeature: "'tnum' 1"
  chip-number:
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
  chip: 7px
  control: 10px
  tile: 12px
  cover: 14px
  card: 18px
  card-desktop: 20px
  sheet: 26px
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
  gutter-phone: 12px
  margin-phone: 20px
  gutter-desktop: 20px
  max-width: 1240px
  measure: 660px
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    typography: "{typography.ui-strong}"
    rounded: "{rounded.control}"
    height: 44px
    padding: 18px
  button-secondary:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    typography: "{typography.ui-strong}"
    rounded: "{rounded.control}"
    height: 44px
    padding: 16px
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.cover}"
    height: 52px
    padding: 16px
  note-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.card}"
    padding: 12px
  note-card-lead:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.lead}"
    rounded: "{rounded.card}"
    padding: 18px
  caught-up:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    typography: "{typography.lead}"
    rounded: "{rounded.card}"
    padding: 20px
  citation-chip:
    backgroundColor: "{colors.acc-soft}"
    textColor: "{colors.acc}"
    typography: "{typography.chip-number}"
    rounded: "{rounded.chip}"
    height: 24px
    padding: 7px
  citation-chip-active:
    backgroundColor: "{colors.acc}"
    textColor: "{colors.acc-ink}"
    typography: "{typography.chip-number}"
    rounded: "{rounded.chip}"
    height: 24px
    padding: 7px
  badge-verified:
    backgroundColor: "{colors.ok-soft}"
    textColor: "{colors.ok}"
    typography: "{typography.tag}"
    rounded: "{rounded.pill}"
    height: 24px
    padding: 9px
  badge-partial:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    typography: "{typography.tag}"
    rounded: "{rounded.pill}"
    height: 24px
    padding: 9px
  badge-unsupported:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
    typography: "{typography.tag}"
    rounded: "{rounded.pill}"
    height: 24px
    padding: 9px
  topic-chip:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.ui-strong}"
    rounded: "{rounded.pill}"
    height: 40px
    padding: 14px
  topic-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    typography: "{typography.ui-strong}"
    rounded: "{rounded.pill}"
    height: 40px
    padding: 14px
  catalog-tile:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.cover}"
    padding: 12px
  stat-tile:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: 18px
  chat-question:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    typography: "{typography.ui}"
    padding: 16px
  chat-answer:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.ui}"
    rounded: "{rounded.card}"
    padding: 16px
  tab-bar:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink3}"
    typography: "{typography.tag}"
    rounded: "{rounded.sheet}"
    height: 64px
    padding: 6px
  state-error:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: 18px
  skeleton:
    backgroundColor: "{colors.sunk}"
    rounded: "{rounded.control}"
---

# Daily AI Notes design system

Written from the page "D · Covers (current)" of the owner's Claude Design canvas, tokens v3.0 of 2026-10-15. The canvas's earlier "v2 · Any topic" page is rejected. Token names are the canvas's own CSS variables without the `--`: `ink2` here is `--ink2` there, and every `dark-` token is the same variable under the `dark` class.

## Overview

Covers. Every topic gets its own drawn cover: a motif from its category, painted in its color. Covers make a day scannable at a glance, give each reader's page a face, and never borrow a news photo we don't own. Around them: white rounded cards on a warm grey ground, one heavy grotesque, and monospace for anything counted or dated.

The product is calm, editorial and factual. Notes are short, every sentence is cited, sources are always one tap away, and the interface says plainly what it does not know. Design for a phone at 390 px first; desktop widens the same cards into splits and grids.

## Colors

Two themes, both designed rather than inverted: light (default) and dark (`prefers-color-scheme: dark`, plus a toggle in the header that the browser remembers).

- **Ground (`bg` #EFEEE9, dark #0F0F0E):** the page, warm grey.
- **Card (`card` #FFFFFF, dark #1A1A18):** every raised thing: note cards, panels, inputs, chips, the tab bar.
- **Sunk (`sunk` #E6E4DE):** wells, skeletons, the empty-page icon tile.
- **Lines (`line`, `line2`):** `line` divides rows inside a card; `line2` outlines a disabled control or a dashed placeholder.
- **Ink (`ink` #121212, `ink2` #4A4945, `ink3` #6B6963):** headlines and body; summaries; metadata, the lightest text allowed. Ink also fills the selected chip, the primary button, the reader's chat question and the "all caught up" card.
- **Accent (`acc` #1F4BFF; dark #8EA4FF):** links, citations and focus only. Never a button fill, never behind a headline. `primary` is an alias of `acc` for tools that expect one. `acc-soft` tints citation chips and highlighted quotes; `acc-ink` is text on an accent fill.
- **Verdicts:** `ok` for verified or supported, `warn` for partly verified or weak, `bad` for unsupported or an error. Each has a `-soft` background; the strong color is the text on it.
- **Topic slots (`s1` to `s8`: Ember, Fern, Iris, Saffron, Rose, Night, Lagoon, Signal):** the 8 px dot beside a topic's name. A dot is never shown without the name, which is why Saffron and Rose may sit under 3:1 on white. The eight dots pass colorblind and normal-vision separation checks in both themes.

The `dark-` tokens, `s1` to `s8`, and `line`, `line2` and `ink2` are applied through CSS variables (dots, dividers, secondary text, the dark theme) rather than component definitions, so the linter reports them as orphaned. That is expected.

## Covers

`TopicCover` draws one inline SVG (`viewBox 0 0 360 200`, sliced to fill its box, hidden from screen readers). The motif comes from the topic's category; the colors come from the topic's slot.

| Category | Motif | Default slot |
|---|---|---|
| Motorsport | Speed stripes, a tyre, a chequered band | 1 Ember |
| Climate and energy | Sun over layered waves | 2 Fern |
| Business and markets | Rising bars and a trend line | 3 Iris |
| Technology and AI | Dot matrix with one lit path | 4 Saffron |
| Team sports | Pitch or court lines and a ball | 5 Rose |
| Space and science | Night sky, an orbit, a comet; always on deep night (#121A40) | 6 Night |
| Custom or uncategorized | Diagonal hatch, a circle and the topic's initial | 7 Lagoon |
| Culture | Overlapping rings | 8 Signal |

- **Slots:** a topic takes its category's default slot if it is free, otherwise the next free one. Slots are given in the order topics are followed and never move when another topic is removed. A topic not followed yet shows the slot it would take.
- **Palettes:** each slot has four cover tones (base, light, dark, deep) plus the motif's fixed details (the tyre and chequer in near-black, the sun and comet in pale yellow, the trend line in gold). A motif drawn in its own default slot matches the canvas exactly. The tones live in `web/src/lib/covers.ts`.
- **Variation:** a seed from the note nudges the main shape by up to 40 units, so two notes on one topic and day never look the same.
- **Variants:** `card` (the art as drawn), `hero` (a wide banner that shows more of the art to each side rather than zooming in), `tile` (square crop, focal shape centered) and `circle` (a plain disc in the cover's base color, for chips and tabs).
- **Same art in both themes.** Covers keep full strength in dark mode; only the surfaces around them change. Covers are decoration and carry nothing the text doesn't say.

## Typography

Two families from Google Fonts, downloaded when the site is built and served from its own origin, so a visit sends nothing to Google: **Schibsted Grotesk** (variable, 400 to 900) for everything, and **IBM Plex Mono** (400, 500) for anything counted or dated, with tabular figures.

Phone sizes are the default tokens; `-desktop` tokens replace them from 960 px, with the greeting and note title growing fluidly between. Note titles use `text-wrap: balance`. `meta` is set in capitals for section metadata ("THU 15 OCT · 2 OF 8"); `label` names a small section ("PREVIEW · A NOTE ON FORMULA 1").

## Layout

A 4 px base. Phone first: cards sit 12 px from the screen edge, text blocks 20 px.

| Width | Layout |
|---|---|
| Under 760 px | One column; the lead note full width with a 200 px cover, the rest as list cards with an 88 px cover tile; a floating tab bar (Today, Topics, Ask, You) |
| 760 px and up | Top pill navigation; the other notes in a grid of `minmax(300px, 1fr)` cards with a 160 px cover |
| 960 px and up | The lead note becomes a split card (cover left, text right); note pages get a 340 px right rail |

On a phone, the topic picker and Ask put their own bar at the bottom (the picks tray, the question box) in place of the tab bar. Content is at most 1240 px wide; a note's text at most 660 px. Nothing scrolls sideways at 360 px except chip rows, which hide their scrollbars.

## Elevation & Depth

Cards have no border and no shadow; they stand out from the ground by color alone. Only floating things get a soft shadow: the phone tab bar, the onboarding tray and the Ask composer (`0 8px 24px` at 12% black, 30% in dark).

## Shapes

- **`chip` (7 px):** citation chips.
- **`control` (10 px):** buttons, feedback-sized icon buttons.
- **`tile` (12 px):** the 88 px cover tile in list cards.
- **`cover` (14 px):** inputs, inset covers, catalog tiles, small panels.
- **`card` (18 px, 20 px on desktop):** note cards, panels, states.
- **`sheet` (26 px):** the note page's content sheet over its cover; the tab bar uses 20 px.
- **`pill` (999 px):** topic chips and tabs, verdict badges, day buttons.

The reader's chat question has one sharp corner: 20 px on three corners and 6 px at the bottom right. Focus is a 2 px `acc` outline with a 2 px offset. Tap targets are at least 40 px; primary actions at least 44 px.

## Components

- **Note cards.** The day's biggest story (the most merged reports) leads. *Lead:* cover on top (200 px), then the topic tag and "N reports → 1" in `meta`, the title in `lead`, a two-line summary, and a footer with publisher initials, the source count and the verdict badge. On desktop the cover sits left and the text right. *List (phone):* an 88 px cover tile beside the tag, title and two-line summary; the footer spans the card. *Grid (desktop):* a 160 px cover on top, the footer pinned to the bottom.
- **Topic tag:** an 8 px slot dot and the name in `tag`.
- **Topic chips and tabs:** 40 px pills on `card` with a 26 to 28 px cover circle, the name and an optional mono count. Selected: ink fill, card-colored text. "For you" and "All topics" have no circle.
- **Publishers:** 22 px circles overlapping by 6 px, ringed in `card`, each the publisher's initial in mono on ink. No favicons are fetched: that would send each visit to other sites.
- **Verdict badge:** a pill with an icon and a word: ✓ Verified (`ok-soft`), a half-filled circle and "Partly verified" (`warn-soft`), a cross and "Unsupported" (`bad-soft`). Never color alone.
- **Citation chip:** an inline button with the number in mono on `acc-soft`, 7 px corners, `aria-expanded`; active, it turns `acc` with `acc-ink` text. On a phone the source opens right after the paragraph; on desktop the matching row in the Sources panel highlights and opens. The source shows its initial, publisher and date, title, the stored quote highlighted in `acc-soft`, and "Open source ↗". The quote is at most 25 words and is the only text shown from a source.
- **Sources panel:** "Sources" with "N cited of M merged", one row per cited source, and a button that lists the other merged reports by title and publisher.
- **How this note was made:** a disclosure card, open by default. It shows a numbered stepper of the five real steps (Scout, Researcher, Writer, Fact-checker, Editor), each with its time in UTC where one is kept and one line on what it did, ending with a bar in the verdict's color: "✓ 6 supported · 0 weak · 0 unsupported".
- **Context row:** earlier notes on the topic as small cover cards, 220 px wide and scrolling sideways on a phone, a grid on desktop.
- **Chat:** the reader's question right-aligned on ink; the answer on a card with a mono "FROM THE NOTES · scope" label, citation chips that open the cited note (its cover, topic and day, title and opening lines, "Open note →", and "Follow" when the reader doesn't follow its topic), and a footer with the number of notes cited and Copy. While it streams: "Searching the notes…", then "✓ Found N notes › Writing an answer with citations…" over skeleton lines. *Not enough:* an empty-page icon tile, "Not enough in the notes to answer that.", the reason when we know it, and a way to widen the search.
- **Catalog tile:** a button (`aria-pressed`) with a cover on top (78 px phone, 96 px desktop), the name, the description and the notes so far. Selected: a 3 px ink outline and an ink check disc at the top right.
- **Stat tile:** a mono label and a big weight-900 number. Real numbers only.
- **States:** skeleton cards (a cover block and three bars, pulsing unless reduced motion is set); "nothing new" with its explanation; an error card with a `bad` outline, "Couldn't load today. Your notes are safe." and "Try again"; a source-unreachable notice.
- **Navigation:** phone, a floating tab bar 12 px from the edges with 20 px corners, the active tab ink-filled; desktop, a pill navigation on `card` (Today, Topics, Ask, How it works), the theme toggle, and the reader's initial or "Sign in".

## Iconography

Inline stroke SVG at 1.6 to 2 px in `currentColor`, 14 to 20 px, `aria-hidden` when next to a label. No emoji, no icon font. The logo is an ink rounded square with three ruled lines in `card`, beside "Daily AI Notes" in weight 800.

## Voice and copy

Plain, specific and honest about gaps. No jargon: never "RAG", "embeddings" or "LLM" in the interface.

- Say what is missing: "Not enough in the notes to answer that." "'Nothing new' means no source published on that topic in the last 24 hours. We don't pad your page."
- Show the work in numbers: "9 reports → 1", "4 cited of 9 merged", "6 supported · 0 weak · 0 unsupported".
- Every note is approved by the editor before it is published, so say "Approved by the editor", never "published automatically". Notes are drafted overnight and appear once approved, so never promise a delivery time.
- The greeting follows the reader's clock ("Good morning.") and uses no name: an account holds only an email.
- Dates are absolute ("Thu 15 Oct 2026"), never "yesterday".

## Screens

| Screen | Canvas artboards | Built |
|---|---|---|
| Daily page (`/`, `/day/<date>`) | 03 phone, 03d desktop, 03b first day | Yes. The first-day state shows each followed topic's real status (notes, or nothing new) instead of live progress |
| Note detail (`/notes/<slug>`) | 04 phone, 04d desktop | Yes |
| Topic picker and onboarding (`/topics`) | 05 phone, 05d desktop | Yes. "Something more specific?" sends a topic suggestion for the editor; step 2 is signing in to keep topics on every device |
| Ask the notes (`/ask`) | 06 phone, 06d desktop | Yes |
| Topic timeline, How it works, Sign in, Account, Privacy, /admin | Not on the D page | Built from these tokens and components; layouts to revise |

Not built, by the owner's decision (2026-10-16), because nothing behind them exists yet: the More, Less and Not relevant feedback buttons, a delivery time, live progress while a first page is written, and custom topics written by readers. The conflicting-source box waits until the pipeline records which sources disagree.

## Do's and Don'ts

- Do keep the accent for links, citations and focus.
- Do show the topic name next to every slot dot and cover circle.
- Do keep every tap target at least 40 px, primary actions 44 px, and the focus ring visible.
- Do keep metadata in mono with tabular figures.
- Don't add borders or shadows to cards; only floating bars get a shadow.
- Don't use gradient washes, glowing orbs, robots, sparkle icons, emoji or glass effects.
- Don't use a news photo; the cover is the image.
- Don't show a number, date or claim without its source on a screen that shows notes.
