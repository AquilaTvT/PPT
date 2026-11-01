#!/usr/bin/env bash
# Overnight chain on the Mac (keeps the GPU busy even if nobody is around to start the next stage):
#   A keyframes -> wait for picks (work/A/PICKS_DONE, max 45 min) -> A videos
#   -> B keyframes -> wait for picks (work/B/PICKS_DONE, max 45 min) -> B videos -> upscale A + B
# Every stage first waits for an already-running instance of itself, and run_shots.py skips finished
# shots, so re-running this script is safe.  Log: work/chain.log
#   nohup bash gpu/chain_mac.sh > /dev/null 2>&1 &
set -u
cd "$(dirname "$0")/.."
export PATH="$PWD/.hw/bin:$PATH"          # ffmpeg lives in .hw/bin (setup_mac.sh)
PY=.hw/venv/bin/python
mkdir -p work/A work/B
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> work/chain.log; }
wait_proc() { while pgrep -f "$1" > /dev/null; do sleep 30; done; }
wait_flag() { local f=$1 max=$2 t=0; while [ ! -f "$f" ] && [ "$t" -lt "$max" ]; do sleep 30; t=$((t + 30)); done; }
free_vram() { curl -s -X POST 127.0.0.1:8188/free -H 'Content-Type: application/json' \
                -d '{"unload_models": true, "free_memory": true}' > /dev/null; sleep 5; }

log "chain start"
wait_proc "run_shots.py keyframes --shots design/mv_a"
$PY gpu/run_shots.py keyframes --shots design/mv_a/shots.json --cfg gpu/config_mac.json --n 2 >> work/kf_A.log 2>&1
log "A keyframes complete; waiting for work/A/PICKS_DONE (max 45 min)"
wait_flag work/A/PICKS_DONE 2700
wait_proc "run_shots.py keyframes --shots design/mv_a"
wait_proc "run_shots.py videos --shots design/mv_a"
free_vram
log "A videos start"
$PY gpu/run_shots.py videos --shots design/mv_a/shots.json --cfg gpu/config_mac.json --n 1 >> work/vid_A.log 2>&1
log "A videos complete"
free_vram
$PY gpu/run_shots.py keyframes --shots design/mv_b/gpu_shots.json --cfg gpu/config_mac_b.json --n 2 >> work/kf_B.log 2>&1
log "B keyframes complete; waiting for work/B/PICKS_DONE (max 45 min)"
wait_flag work/B/PICKS_DONE 2700
wait_proc "run_shots.py keyframes --shots design/mv_b"
wait_proc "run_shots.py videos --shots design/mv_b"
free_vram
log "B videos start"
$PY gpu/run_shots.py videos --shots design/mv_b/gpu_shots.json --cfg gpu/config_mac_b.json --n 1 >> work/vid_B.log 2>&1
log "B videos complete; upscaling"
free_vram
$PY gpu/upscale_clips.py work/A work/B >> work/up.log 2>&1
log "chain done"
