#!/usr/bin/env bash
# Reordered overnight chain (MV-B first, so one film can be finished while MV-A keeps generating):
#   B keyframes -> wait for picks (work/B/PICKS_DONE, max 45 min) -> B videos -> upscale B
#   -> A videos (resumes; finished shots are skipped) -> upscale A
# Start it only after the old chain_mac.sh and any run_shots.py process have been stopped at a clip boundary
# and ComfyUI's queue is empty.  run_shots.py skips finished shots, so re-running this script is safe.
#   nohup bash gpu/chain_mac2.sh > /dev/null 2>&1 &
set -u
cd "$(dirname "$0")/.."
PY=.hw/venv/bin/python
mkdir -p work/A work/B
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> work/chain.log; }
wait_proc() { while pgrep -f "$1" > /dev/null; do sleep 30; done; }
wait_flag() { local f=$1 max=$2 t=0; while [ ! -f "$f" ] && [ "$t" -lt "$max" ]; do sleep 30; t=$((t + 30)); done; }
free_vram() { curl -s -X POST 127.0.0.1:8188/free -H 'Content-Type: application/json' \
                -d '{"unload_models": true, "free_memory": true}' > /dev/null; sleep 5; }
disk_ok() { [ "$(df -g ~ | awk 'NR==2 {print $4}')" -ge "${HW_MIN_FREE_GB:-8}" ]; }

log "chain2 start (B first)"
wait_proc "run_shots.py"
free_vram
$PY gpu/run_shots.py keyframes --shots design/mv_b/gpu_shots.json --cfg gpu/config_mac_b.json --n 2 >> work/kf_B.log 2>&1
log "B keyframes complete; waiting for work/B/PICKS_DONE (max 45 min)"
wait_flag work/B/PICKS_DONE 2700
wait_proc "run_shots.py keyframes --shots design/mv_b"
free_vram
disk_ok || { log "low disk, stopping"; exit 1; }
log "B videos start"
$PY gpu/run_shots.py videos --shots design/mv_b/gpu_shots.json --cfg gpu/config_mac_b.json --n 1 >> work/vid_B.log 2>&1
log "B videos complete; upscaling B"
free_vram
$PY gpu/upscale_clips.py work/B >> work/up.log 2>&1
log "B upscaled"
disk_ok || { log "low disk, stopping"; exit 1; }
free_vram
log "A videos resume"
$PY gpu/run_shots.py videos --shots design/mv_a/shots.json --cfg gpu/config_mac.json --n 1 >> work/vid_A.log 2>&1
log "A videos complete; upscaling A"
free_vram
$PY gpu/upscale_clips.py work/A >> work/up.log 2>&1
log "chain2 done"
