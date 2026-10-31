# GPU runbook (Mac mini / Apple Silicon)

Everything heavy (ComfyUI, models, generated clips) lives in `.hw/` and `work/` inside the
project folder and is git-ignored.

## 0. Get the code onto the Mac

```bash
cd ~/"Heat Waves"
git clone --filter=blob:none --sparse -b claude/loving-darwin-3ck6oy https://github.com/AquilaTvT/PPT.git PPT
cd PPT && git sparse-checkout set heatwaves_mv && cd heatwaves_mv
```

## 1. Hardware check

```bash
bash gpu/hwcheck.sh
```

## 2. Install ComfyUI + models sized to this Mac's memory (~24 GB download)

```bash
bash gpu/setup_mac.sh            # add --mirror if huggingface.co is slow
```

## 3. Start ComfyUI (leave it running)

```bash
bash gpu/start_comfy_mac.sh      # caps GPU memory at ~8 GB on a 16 GB Mac (OOM error instead of swap)
```

## 4. Benchmark (decides resolution / steps / shot budget)

```bash
.hw/venv/bin/python gpu/bench.py --platform mac      # 5B turbo path; results in work/bench.json
```

## 5. Characters -> LoRA

```bash
.hw/venv/bin/python gpu/charsheet.py gen --n 3
.hw/venv/bin/python gpu/charsheet.py sheet --char kimi            # review, pick the consistent ones
.hw/venv/bin/python gpu/charsheet.py dataset --char kimi --keep 0,3,5,...
.hw/venv/bin/python gpu/charsheet.py train --char kimi
```

## 6. Shots

```bash
.hw/venv/bin/python gpu/run_shots.py keyframes --shots design/mv_a_shots.json --cfg gpu/config_mac.json --n 4
.hw/venv/bin/python gpu/sheet.py keyframes work/A work/A/kf_sheet.jpg
.hw/venv/bin/python gpu/run_shots.py pick --shots design/mv_a_shots.json --id A-hook-01 --kf kf_2.png
.hw/venv/bin/python gpu/run_shots.py videos --shots design/mv_a_shots.json --cfg gpu/config_mac.json
.hw/venv/bin/python gpu/run_shots.py finish --shots design/mv_a_shots.json --cfg gpu/config_mac.json
```

Memory rule: never run two model families at once; `run_shots.py` frees models between
keyframe and video batches, and the GGUF quant is chosen so one 14B expert + text encoder +
VAE stay well under the Mac's unified memory.
