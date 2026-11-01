#!/usr/bin/env bash
# Delivery encodes for a finished film (the render's own CRF-15 encode is the master; nothing is re-encoded twice).
#   bash tools/deliver.sh out/mva_final.mp4 HeatWaves_MV-A_Nigemizu
# Writes into out/deliver/:
#   <name>_master_1080p.mp4   the render remuxed (faststart, metadata), ~45-50 Mbps
#   <name>_1080p.mp4          2-pass H.264 High 4.1, 12 Mbps, AAC 256k  (phones, sharing)
#   <name>_720p.mp4           2-pass H.264 High, 4.5 Mbps, AAC 192k     (small)
# and checks each against tools/qa_video.py (duration, audio, flashes).
set -euo pipefail
cd "$(dirname "$0")/.."
src="$1"; name="$2"
out=out/deliver
mkdir -p "$out"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
title="Heat Waves (Japanese version) - ${name}"
ffmpeg -v error -y -i "$src" -map 0 -c copy -movflags +faststart -metadata title="$title" "$out/${name}_master_1080p.mp4"
enc() {   # enc <w> <h> <vbitrate> <abitrate> <outfile> <level>
  local vf="scale=$1:$2:flags=lanczos"
  ffmpeg -v error -y -i "$src" -vf "$vf" -c:v libx264 -preset slow -profile:v high -level:v "$6" -b:v "$3" -maxrate "$3" \
    -bufsize "$3" -pass 1 -passlogfile "$tmp/p" -an -f mp4 /dev/null
  ffmpeg -v error -y -i "$src" -vf "$vf" -c:v libx264 -preset slow -profile:v high -level:v "$6" -b:v "$3" \
    -pass 2 -passlogfile "$tmp/p" -pix_fmt yuv420p -c:a aac -b:a "$4" -movflags +faststart -metadata title="$title" "$5"
}
enc 1920 1080 12M 256k "$out/${name}_1080p.mp4" 4.1
enc 1280 720 4500k 192k "$out/${name}_720p.mp4" 4.0
for f in "$out/${name}_master_1080p.mp4" "$out/${name}_1080p.mp4" "$out/${name}_720p.mp4"; do
  printf '%s  %s MB  ' "$(basename "$f")" "$(( $(stat -c %s "$f") / 1000000 ))"
  python3 tools/qa_video.py "$f" | tail -1
done
