#!/usr/bin/env bash
# The README's pictures (`make readme-media`). Playwright takes them from the live site
# (e2e/readme.media.ts); ImageMagick sets the daily page's desktop and phone views side by side
# as WebP (a tenth of a PNG's size), and ffmpeg turns one loop of How it works' "One story's
# night" into a GIF. Light and dark each, into docs/images/. Needs ffmpeg and ImageMagick 7 on the development machine only.
set -euo pipefail
cd "$(dirname "$0")/.."

raw=screenshots/readme
out=../docs/images
rm -rf "$raw"
mkdir -p "$raw" "$out"
npx --yes pnpm@12.8.1 exec playwright test -c playwright.readme.config.ts

# Rounded corners and a hairline edge, as cards have (DESIGN.md).
card() {
  local in=$1 result=$2 edge=$3 radius=$4 w h
  read -r w h < <(magick identify -format "%w %h\n" "$in")
  magick "$in" -alpha set \
    \( -size "${w}x${h}" xc:none -fill white -draw "roundrectangle 0,0,$((w - 1)),$((h - 1)),$radius,$radius" \) \
    -compose DstIn -composite \
    -compose Over -fill none -stroke "$edge" -strokewidth 2 \
    -draw "roundrectangle 1,1,$((w - 2)),$((h - 2)),$radius,$radius" \
    "$result"
}

# The daily page: desktop and phone at the same height on the sunk ground, 1760 px wide (twice
# GitHub's column).
daily() {
  local theme=$1 ground=$2 edge=$3 dw dh pw pad=64
  card "$raw/daily-desktop-$theme.png" "$raw/desktop-card-$theme.png" "$edge" 28
  read -r dw dh < <(magick identify -format "%w %h\n" "$raw/desktop-card-$theme.png")
  magick "$raw/daily-phone-$theme.png" -resize "x$dh" "$raw/phone-$theme.png"
  card "$raw/phone-$theme.png" "$raw/phone-card-$theme.png" "$edge" 56
  pw=$(magick identify -format "%w" "$raw/phone-card-$theme.png")
  magick -size "$((pad + dw + pad + pw + pad))x$((pad + dh + pad))" "xc:$ground" \
    "$raw/desktop-card-$theme.png" -geometry "+$pad+$pad" -composite \
    "$raw/phone-card-$theme.png" -geometry "+$((pad + dw + pad))+$pad" -composite \
    -resize 1760x -strip -quality 90 "$out/daily-$theme.webp"
}

# One loop of the night: each frame shows until the next was taken (ffmpeg's concat list).
night() {
  local theme=$1 dir="$raw/night-$1"
  find "$dir" -name '*.png' -exec basename {} \; | sort | awk '
    { name[NR] = $0; ms[NR] = $0 + 0 }
    END {
      for (i = 1; i <= NR; i++) {
        next_ms = (i < NR) ? ms[i + 1] : 16000
        printf "file %s\nduration %.3f\n", name[i], (next_ms - ms[i]) / 1000
      }
      printf "file %s\n", name[NR]
    }' > "$dir/frames.txt"
  ffmpeg -y -v error -f concat -i "$dir/frames.txt" \
    -vf "fps=12,scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" \
    -loop 0 "$out/how-it-works-$theme.gif"
}

daily light "#E6E4DE" "#CFCCC4"
daily dark "#242422" "#3A3A36"
night light
night dark
ls -l "$out"
