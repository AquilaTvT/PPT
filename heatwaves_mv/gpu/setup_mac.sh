#!/usr/bin/env bash
# One-time setup on an Apple Silicon Mac: Python (via uv, no sudo), ComfyUI pinned to the
# version the graphs were validated against, ComfyUI-GGUF, ffmpeg, then the model set sized
# to this Mac's unified memory. Idempotent: safe to re-run.
#
#   bash gpu/setup_mac.sh [--mirror]        (run from the project folder)
set -euo pipefail
cd "$(dirname "$0")/.."
PROJ="$PWD"
WORK="${HW_WORK:-$PROJ/.hw}"            # everything heavy lives here (ComfyUI, venv, models)
COMFY="$WORK/ComfyUI"
MIRROR="${1:-}"
COMFY_REF=b5a432157de6b8884f81104cd02926adf4d597e4       # ComfyUI 0.43.0
mkdir -p "$WORK"

[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo "this script is for Apple Silicon Macs"; exit 1; }
RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
FREE_GB=$(df -g "$WORK" | awk 'NR==2{print $4}')
echo "chip: $(sysctl -n machdep.cpu.brand_string)  unified memory: ${RAM_GB} GB  free disk: ${FREE_GB} GB"

# --- python via uv (user-local, no sudo) --------------------------------------------------
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
[ -d "$WORK/venv" ] || "$UV" venv --python 3.12 "$WORK/venv"
PY="$WORK/venv/bin/python"

# --- ComfyUI ---------------------------------------------------------------------------------
if [ ! -d "$COMFY/.git" ]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY"
fi
git -C "$COMFY" fetch --depth 1 origin "$COMFY_REF" 2>/dev/null || git -C "$COMFY" fetch origin
git -C "$COMFY" checkout -q "$COMFY_REF"
"$UV" pip install --python "$PY" -r "$COMFY/requirements.txt"
"$UV" pip install --python "$PY" gguf numpy opencv-python-headless pillow skia-python librosa soundfile imageio-ffmpeg

# --- ComfyUI-GGUF (GGUF loaders; needed for the 14B video experts on MPS) ---------------------
if [ ! -d "$COMFY/custom_nodes/ComfyUI-GGUF" ]; then
  git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git "$COMFY/custom_nodes/ComfyUI-GGUF"
fi

# --- ffmpeg (Homebrew if present, else the static binary shipped with imageio-ffmpeg) -------
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then brew install ffmpeg; else
    FF=$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')
    mkdir -p "$WORK/bin" && ln -sf "$FF" "$WORK/bin/ffmpeg"
    echo "ffmpeg -> $FF  (add $WORK/bin to PATH)"
  fi
fi

# --- models (sized to unified memory) ---------------------------------------------------------
"$PY" gpu/models.py fetch --platform mac --ram "$RAM_GB" --comfy "$COMFY" ${MIRROR:+--mirror}

cat <<EOF

done. start ComfyUI with:
  PYTORCH_ENABLE_MPS_FALLBACK=1 "$PY" "$COMFY/main.py" --listen 127.0.0.1 --port 8188 --disable-auto-launch
EOF
