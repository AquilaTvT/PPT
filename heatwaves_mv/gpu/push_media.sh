#!/usr/bin/env bash
# Push generated media to the repo's separate `hw-media` branch so the cloud compositor can fetch it.
# The branch lives in its own folder (~/Heat Waves/hw-media); the code checkout is never touched.
#   bash gpu/push_media.sh work/A/A-intro-01 work/bench.json ...      (paths relative to the project)
set -euo pipefail
cd "$(dirname "$0")/.."
PROJ="$PWD"
MEDIA="${HW_MEDIA:-$(cd "$PROJ/../.." && pwd)/hw-media}"
if [ ! -d "$MEDIA/.git" ]; then
  git init -q "$MEDIA"
  git -C "$MEDIA" remote add origin "$(git -C "$PROJ" remote get-url origin)"
  git -C "$MEDIA" checkout -q -b hw-media
  git -C "$MEDIA" fetch -q origin hw-media 2>/dev/null && git -C "$MEDIA" reset -q --soft FETCH_HEAD || true
fi
for p in "$@"; do
  [ -e "$p" ] || { echo "missing: $p"; continue; }
  mkdir -p "$MEDIA/$(dirname "$p")"
  if [ -d "$p" ]; then rsync -a --exclude '*.tmp' "$p/" "$MEDIA/$p/"; else cp -p "$p" "$MEDIA/$p"; fi
done
git -C "$MEDIA" add -A
if git -C "$MEDIA" diff --cached --quiet; then echo "nothing new"; exit 0; fi
git -C "$MEDIA" -c user.name="hw-mac" -c user.email="hw-mac@localhost" commit -q -m "media $(date '+%m-%d %H:%M:%S')"
for i in 1 2 3 4; do
  GIT_TERMINAL_PROMPT=0 git -C "$MEDIA" push -q origin HEAD:refs/heads/hw-media && { echo "pushed $(git -C "$MEDIA" rev-parse --short HEAD)"; exit 0; }
  sleep $((2 ** i))
done
echo "push failed"; exit 1
