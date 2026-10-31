#!/usr/bin/env bash
# Start ComfyUI on Apple Silicon with a hard cap on GPU (unified) memory: an over-budget job fails
# with an out-of-memory error instead of pushing the Mac into swap.
#   bash gpu/start_comfy_mac.sh            (from the project folder; leave it running)
cd "$(dirname "$0")/.."
WORK="${HW_WORK:-$PWD/.hw}"
export PYTORCH_ENABLE_MPS_FALLBACK=1
# ratios are relative to Metal's recommended working set (~10.7 GB on a 16 GB Mac): 0.75 -> ~8 GB cap
export PYTORCH_MPS_HIGH_WATERMARK_RATIO="${HW_MPS_HIGH:-0.75}"
export PYTORCH_MPS_LOW_WATERMARK_RATIO="${HW_MPS_LOW:-0.6}"
exec "$WORK/venv/bin/python" "$WORK/ComfyUI/main.py" --listen 127.0.0.1 --port 8188 --disable-auto-launch "$@"
