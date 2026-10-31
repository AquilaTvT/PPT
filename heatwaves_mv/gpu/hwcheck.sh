#!/usr/bin/env bash
# First thing to run on the GPU machine: what hardware, what's installed, what's reachable.
echo "== system";  uname -a; (lsb_release -ds 2>/dev/null || sw_vers 2>/dev/null || cat /etc/os-release 2>/dev/null | head -3)
echo "== cpu";     (nproc 2>/dev/null || sysctl -n hw.ncpu); (lscpu 2>/dev/null | grep "Model name" || sysctl -n machdep.cpu.brand_string 2>/dev/null)
echo "== memory";  (free -g 2>/dev/null || (sysctl -n hw.memsize | awk '{print $1/1073741824 " GB"}'))
echo "== gpu";     (nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,compute_cap --format=csv 2>/dev/null \
                    || system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Chipset|VRAM|Metal" || echo "no nvidia-smi")
echo "== cuda";    (nvcc --version 2>/dev/null | tail -1; ls -d /usr/local/cuda* 2>/dev/null | head -3)
echo "== disk";    df -h "$PWD" "$HOME" 2>/dev/null
echo "== tools";   for t in python3 python pip3 git ffmpeg blender conda uv nvidia-smi curl aria2c; do printf "%-10s %s\n" "$t" "$(command -v $t || echo -)"; done
python3 - <<'EOF' 2>/dev/null
import importlib
for m in ("torch", "torchvision", "numpy", "cv2", "skia", "PIL"):
    try:
        mod = importlib.import_module(m)
        extra = ""
        if m == "torch":
            extra = f" cuda={mod.cuda.is_available()} mps={getattr(mod.backends, 'mps', None) and mod.backends.mps.is_available()}"
            if mod.cuda.is_available():
                extra += f" dev={mod.cuda.get_device_name(0)} vram={mod.cuda.get_device_properties(0).total_memory/2**30:.1f}GB"
        print(f"{m:12s} {getattr(mod, '__version__', '?')}{extra}")
    except Exception as e:
        print(f"{m:12s} -")
EOF
echo "== comfyui installs"
for d in "$HOME/ComfyUI" "$HOME"/*/ComfyUI "$HOME"/*/*/ComfyUI /opt/ComfyUI /data*/ComfyUI "$PWD"/../ComfyUI; do
  [ -f "$d/main.py" ] && { echo "found: $d"; ls "$d/models" 2>/dev/null | head -40; du -sh "$d/models" 2>/dev/null; }
done
echo "== network"
for u in https://huggingface.co https://hf-mirror.com https://www.modelscope.cn https://github.com https://pypi.org https://download.pytorch.org https://www.bilibili.com; do
  printf "%-36s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code} %{time_total}s' --max-time 10 "$u")"
done
