"""Model catalogue + VRAM-tier selection + resumable downloader.

  python gpu/models.py plan  --vram 24 --ram 64            # what would be fetched
  python gpu/models.py fetch --comfy ~/ComfyUI --vram 24 --ram 64 [--only keyframes,video] [--mirror]

Downloads go straight into ComfyUI/models/<folder>/ with curl -C - (resumable).
--mirror switches huggingface.co to hf-mirror.com (mainland China).
"""
import argparse
import os
import subprocess
import sys

HF = 'https://huggingface.co'
MIRROR = 'https://hf-mirror.com'

# (key, group, folder, repo, path_in_repo, size_gb, min_vram)
CATALOGUE = [
    # --- keyframes: anime stills -------------------------------------------------------
    ('anima_aesthetic', 'keyframes', 'diffusion_models', 'circlestone-labs/Anima',
     'split_files/diffusion_models/anima-aesthetic-v1.1.safetensors', 4.18, 8),
    ('anima_turbo', 'keyframes', 'diffusion_models', 'circlestone-labs/Anima',
     'split_files/diffusion_models/anima-turbo-v1.1.safetensors', 4.18, 8),
    ('anima_base', 'lora_train', 'diffusion_models', 'circlestone-labs/Anima',
     'split_files/diffusion_models/anima-base-v1.0.safetensors', 4.18, 12),
    ('qwen3_06b', 'keyframes', 'text_encoders', 'circlestone-labs/Anima',
     'split_files/text_encoders/qwen_3_06b_base.safetensors', 1.19, 8),
    ('qwen_image_vae', 'keyframes', 'vae', 'circlestone-labs/Anima',
     'split_files/vae/qwen_image_vae.safetensors', 0.25, 8),
    # --- identity-preserving edits ----------------------------------------------------
    ('qwen_edit_2511', 'edit', 'diffusion_models', 'Comfy-Org/Qwen-Image-Edit_ComfyUI',
     'split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors', 20.53, 16),
    ('qwen25vl_7b', 'edit', 'text_encoders', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors', 9.38, 16),
    # --- image-to-video: Wan 2.2 A14B (two experts) + 4-step distill LoRAs -------------
    ('wan22_i2v_high', 'video', 'diffusion_models', 'Comfy-Org/Wan-2.2',
     'split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors', 14.29, 16),
    ('wan22_i2v_low', 'video', 'diffusion_models', 'Comfy-Org/Wan-2.2',
     'split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors', 14.29, 16),
    ('wan22_lx2v_high', 'video', 'loras', 'Comfy-Org/Wan-2.2',
     'split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors', 1.23, 16),
    ('wan22_lx2v_low', 'video', 'loras', 'Comfy-Org/Wan-2.2',
     'split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors', 1.23, 16),
    ('umt5_xxl_fp8', 'video', 'text_encoders', 'Comfy-Org/Wan-2.2',
     'split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors', 6.74, 8),
    ('wan21_vae', 'video', 'vae', 'Comfy-Org/Wan-2.2', 'split_files/vae/wan_2.1_vae.safetensors', 0.25, 8),
    # low-VRAM fallback: Wan 2.2 TI2V 5B (720p native)
    ('wan22_ti2v_5b', 'video_small', 'diffusion_models', 'Comfy-Org/Wan-2.2',
     'split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors', 10.0, 8),
    ('wan22_vae', 'video_small', 'vae', 'Comfy-Org/Wan-2.2', 'split_files/vae/wan2.2_vae.safetensors', 1.41, 8),
    # --- image-to-video alternative: HunyuanVideo 1.5 (720p) + 1080p SR ----------------
    ('hy15_i2v_720', 'video_hy', 'diffusion_models', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/diffusion_models/hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.safetensors', 8.33, 12),
    ('hy15_sr_1080', 'video_hy', 'diffusion_models', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/diffusion_models/hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.safetensors', 8.34, 12),
    ('hy15_te', 'video_hy', 'text_encoders', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors', 9.38, 12),
    ('hy15_byt5', 'video_hy', 'text_encoders', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors', 0.44, 12),
    ('hy15_vae', 'video_hy', 'vae', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/vae/hunyuanvideo15_vae_fp16.safetensors', 2.52, 12),
    ('hy15_sigclip', 'video_hy', 'clip_vision', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/clip_vision/sigclip_vision_patch14_384.safetensors', 0.86, 12),
    ('hy15_upsampler_1080', 'video_hy', 'latent_upscale_models', 'Comfy-Org/HunyuanVideo_1.5_repackaged',
     'split_files/latent_upscale_models/hunyuanvideo15_latent_upsampler_1080p.safetensors', 0.20, 12),
    # --- finishing: frame interpolation + video super-resolution ----------------------
    ('rife_426', 'finish', 'frame_interpolation', 'Comfy-Org/frame_interpolation',
     'frame_interpolation/rife_v4.26.safetensors', 0.02, 4),
    ('film_fp16', 'finish', 'frame_interpolation', 'Comfy-Org/frame_interpolation',
     'frame_interpolation/film_net_fp16.safetensors', 0.07, 4),
    ('seedvr2_7b_sharp', 'finish', 'diffusion_models', 'Comfy-Org/SeedVR2',
     'diffusion_models/seedvr2_7b_sharp_fp8_e4m3fn.safetensors', 8.24, 16),
    ('seedvr2_3b', 'finish_small', 'diffusion_models', 'Comfy-Org/SeedVR2',
     'diffusion_models/seedvr2_3b_fp8_e4m3fn.safetensors', 3.39, 8),
    ('seedvr2_vae', 'finish', 'vae', 'Comfy-Org/SeedVR2', 'vae/seedvr2_ema_vae_fp16.safetensors', 0.50, 8),
]

# --- Apple Silicon (MPS cannot run fp8): GGUF experts via ComfyUI-GGUF, 5B in fp16 -----
MAC = [
    ('anima_aesthetic', 'keyframes', 'diffusion_models', 'circlestone-labs/Anima',
     'split_files/diffusion_models/anima-aesthetic-v1.1.safetensors', 4.18, 0),
    ('anima_base', 'lora_train', 'diffusion_models', 'circlestone-labs/Anima',
     'split_files/diffusion_models/anima-base-v1.0.safetensors', 4.18, 0),
    ('qwen3_06b', 'keyframes', 'text_encoders', 'circlestone-labs/Anima',
     'split_files/text_encoders/qwen_3_06b_base.safetensors', 1.19, 0),
    ('qwen_image_vae', 'keyframes', 'vae', 'circlestone-labs/Anima', 'split_files/vae/qwen_image_vae.safetensors', 0.25, 0),
    ('umt5_q8_gguf', 'video', 'text_encoders', 'city96/umt5-xxl-encoder-gguf', 'umt5-xxl-encoder-Q8_0.gguf', 6.04, 0),
    ('wan21_vae', 'video', 'vae', 'Comfy-Org/Wan-2.2', 'split_files/vae/wan_2.1_vae.safetensors', 0.25, 0),
    ('wan22_lx2v_high', 'video', 'loras', 'Comfy-Org/Wan-2.2',
     'split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors', 1.23, 0),
    ('wan22_lx2v_low', 'video', 'loras', 'Comfy-Org/Wan-2.2',
     'split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors', 1.23, 0),
    # A14B experts: quant chosen from unified memory in plan_mac()
    ('wan22_gguf_high', 'video14b', 'diffusion_models', 'QuantStack/Wan2.2-I2V-A14B-GGUF',
     'HighNoise/Wan2.2-I2V-A14B-HighNoise-{q}.gguf', 0, 0),
    ('wan22_gguf_low', 'video14b', 'diffusion_models', 'QuantStack/Wan2.2-I2V-A14B-GGUF',
     'LowNoise/Wan2.2-I2V-A14B-LowNoise-{q}.gguf', 0, 0),
    ('wan22_ti2v_5b', 'video5b', 'diffusion_models', 'Comfy-Org/Wan-2.2',
     'split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors', 10.0, 0),
    ('wan22_vae', 'video5b', 'vae', 'Comfy-Org/Wan-2.2', 'split_files/vae/wan2.2_vae.safetensors', 1.41, 0),
    ('rife_426', 'finish', 'frame_interpolation', 'Comfy-Org/frame_interpolation',
     'frame_interpolation/rife_v4.26.safetensors', 0.02, 0),
    ('film_fp16', 'finish', 'frame_interpolation', 'Comfy-Org/frame_interpolation',
     'frame_interpolation/film_net_fp16.safetensors', 0.07, 0),
    ('animesharp_v4', 'finish', 'upscale_models', 'Kim2091/2x-AnimeSharpV4', '2x-AnimeSharpV4_RCAN.safetensors', 0.03, 0),
]
GGUF_SIZE = {'Q4_K_M': 9.65, 'Q5_K_M': 10.79, 'Q6_K': 12.0, 'Q8_0': 15.41}


def plan_mac(ram):
    """unified memory budget: one 14B expert + text encoder + VAE + activations must stay well under RAM"""
    q = 'Q8_0' if ram >= 96 else 'Q6_K' if ram >= 64 else 'Q5_K_M' if ram >= 48 else 'Q4_K_M' if ram >= 32 else None
    rows = []
    for key, group, folder, repo, path, size, mv in MAC:
        if group == 'video14b':
            if q is None:
                continue
            rows.append((key, group, folder, repo, path.format(q=q), GGUF_SIZE[q], mv))
        else:
            rows.append((key, group, folder, repo, path, size, mv))
    return rows, q


def plan(vram, ram, only=None):
    """Select model groups for the machine.

    16 GB+ runs the 14B Wan experts (fp8, ComfyUI offloads what does not fit);
    below that the 5B Wan model and the 3B SeedVR2. The 20B Qwen edit model needs
    20 GB VRAM or 64 GB RAM to offload into.
    """
    groups = {'keyframes', 'finish', 'lora_train', 'video_hy'}
    if vram >= 16:
        groups.add('video')
    else:
        groups |= {'video_small', 'finish_small'}
    if vram >= 20 or (vram >= 16 and ram >= 64):
        groups.add('edit')
    rows = [r for r in CATALOGUE if r[1] in groups and vram >= r[6] and (not only or r[1] in only)]
    seen, out = set(), []
    for row in rows:                      # shared files (e.g. the Qwen2.5-VL encoder) only once
        dst = (row[2], os.path.basename(row[4]))
        if dst not in seen:
            seen.add(dst)
            out.append(row)
    return out


def fetch(comfy, rows, mirror=False):
    base = MIRROR if mirror else HF
    for key, group, folder, repo, path, size, _ in rows:
        dst_dir = os.path.join(comfy, 'models', folder)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(path))
        if os.path.exists(dst) and os.path.getsize(dst) > size * 1e9 * 0.98:
            print(f'ok      {key:22s} {dst}', flush=True)
            continue
        url = f'{base}/{repo}/resolve/main/{path}'
        print(f'fetch   {key:22s} {size:6.2f} GB  {url}', flush=True)
        for attempt in range(5):
            r = subprocess.run(['curl', '-fL', '-C', '-', '--retry', '5', '--retry-delay', '5', '-o', dst, url])
            if r.returncode == 0:
                break
        else:
            print(f'FAILED  {key}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['plan', 'fetch'])
    ap.add_argument('--vram', type=float, default=0)
    ap.add_argument('--ram', type=float, default=32)
    ap.add_argument('--comfy', default=os.path.expanduser('~/ComfyUI'))
    ap.add_argument('--only', default='')
    ap.add_argument('--mirror', action='store_true')
    ap.add_argument('--platform', choices=['cuda', 'mac'], default='cuda')
    a = ap.parse_args()
    if a.platform == 'mac':
        rows, q = plan_mac(a.ram)
        print(f'apple silicon, {a.ram:.0f} GB unified memory -> Wan 2.2 A14B GGUF {q or "(none: use the 5B model)"}')
    else:
        rows = plan(a.vram, a.ram, set(a.only.split(',')) if a.only else None)
    total = sum(r[5] for r in rows)
    for r in rows:
        print(f'{r[1]:12s} {r[0]:22s} {r[5]:6.2f} GB  -> models/{r[2]}/{os.path.basename(r[4])}')
    print(f'total {total:.1f} GB')
    if a.mode == 'fetch':
        fetch(a.comfy, rows, a.mirror)


if __name__ == '__main__':
    sys.exit(main())
