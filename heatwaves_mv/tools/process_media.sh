#!/usr/bin/env bash
# Cloud side, after the Mac pushed media to the hw-media branch:
#   1. fetch the branch into work/ (tools/ingest_media.py)
#   2. MV-B: pre-cut every character clip (green key / anime-seg -> world-ink print -> sticker rim), cached
#   3. region sheets for MV-A keyframes (to fill design/mv_a/regions.json)
#   4. optional preview renders (--preview a|b|ab)
#   bash tools/process_media.sh [--preview b]
set -euo pipefail
cd "$(dirname "$0")/.."
PREVIEW=""
[ "${1:-}" = "--preview" ] && PREVIEW="${2:-}"
SP=${HW_SCRATCH:-/tmp/hw_scratch}
mkdir -p "$SP" out
python3 tools/ingest_media.py
if ls work/B/*/v_0*.mp4 work/B/*/final*.mp4 >/dev/null 2>&1 || ls work/B/*/kf_*.png >/dev/null 2>&1; then
  python3 -m mvb.chars --all --workers 3 2>&1 | grep -v Fontconfig | tail -40
fi
if ls work/A/*/kf_*.png >/dev/null 2>&1; then
  python3 tools/region_sheet.py --out "$SP/regions_A" 2>&1 | grep -v Fontconfig | tail -70
fi
case "$PREVIEW" in
  *b*) python3 tools/render_mvb.py --mv b --t0 0 --t1 198.74 --out out/MV-B_full.mp4 --workers 3 --audio ;;
esac
case "$PREVIEW" in
  *a*) python3 tools/render_mvb.py --mv a --t0 0 --t1 198.74 --out out/MV-A_full.mp4 --workers 3 --audio ;;
esac
echo done
