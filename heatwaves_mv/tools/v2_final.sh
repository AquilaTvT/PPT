#!/usr/bin/env bash
# MV-B v2 final: media status -> full render (3 workers, audio) -> QA -> delivery encodes.
#   bash tools/v2_final.sh [name]          (default name: HeatWaves_MV)
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:-HeatWaves}"
mkdir -p out
python3 tools/v2_status.py | tail -3
start=$(date +%s)
python3 tools/render_mvb.py --mv b2 --out out/hw_v2.mp4 --workers 3 --audio
echo "render $(( ($(date +%s) - start) / 60 )) min"
rm -rf out/hw_v2.mp4.parts
python3 tools/qa_video.py out/hw_v2.mp4 | tee out/hw_v2_qa.txt | tail -12
TITLE="Heat Waves" bash tools/deliver.sh out/hw_v2.mp4 "$name"
ls -la out/deliver/
