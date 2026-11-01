#!/usr/bin/env bash
# End-of-project cleanup on the Mac: removes everything this project installed or generated, and nothing else.
#   bash gpu/cleanup_mac.sh                                            # dry run: what would be removed, with sizes
#   cp gpu/cleanup_mac.sh /tmp/hw_cleanup.sh && bash /tmp/hw_cleanup.sh --yes   # remove (run a copy: it deletes itself)
# Removes:
#   ~/Heat Waves/PPT        (this checkout, incl. .hw: ComfyUI, venv, models, work/ media)
#   ~/Heat Waves/hw-media   (the media push clone)
#   ~/Heat Waves/hw-push    (the push test clone)
#   uv:  ~/.local/bin/uv, ~/.local/bin/uvx, ~/.local/share/uv, ~/.cache/uv
# Keeps: the Claude desktop app / CLI, Homebrew, git, anything else. The ComfyUI server is stopped first.
set -u
YES=0
[ "${1:-}" = "--yes" ] && YES=1
BASE="$HOME/Heat Waves"
TARGETS=("$BASE/PPT" "$BASE/hw-media" "$BASE/hw-push" "$HOME/.local/bin/uv" "$HOME/.local/bin/uvx" "$HOME/.local/share/uv" "$HOME/.cache/uv")

echo "== will remove:"
for p in "${TARGETS[@]}"; do
  if [ -e "$p" ]; then du -sh "$p" 2>/dev/null; else echo "   (absent) $p"; fi
done
if [ "$YES" -ne 1 ]; then
  echo "dry run. Re-run with --yes to delete."
  exit 0
fi
# stop ComfyUI / caffeinate started for this project (by command line, never by a bare pattern on other apps)
for pid in $(pgrep -f "Heat Waves/PPT/heatwaves_mv/.hw/ComfyUI/main.py" 2>/dev/null); do kill "$pid" 2>/dev/null; done
for pid in $(pgrep -f "chain_mac" 2>/dev/null); do kill "$pid" 2>/dev/null; done
sleep 2
for p in "${TARGETS[@]}"; do
  case "$p" in
    "$BASE"/*|"$HOME"/.local/bin/uv|"$HOME"/.local/bin/uvx|"$HOME"/.local/share/uv|"$HOME"/.cache/uv) ;;
    *) echo "refusing: $p"; continue ;;
  esac
  [ -e "$p" ] && rm -rf "$p" && echo "removed $p"
done
rmdir "$BASE" 2>/dev/null && echo "removed empty $BASE"
echo "done. Free space now: $(df -h ~ | awk 'NR==2 {print $4}')"
