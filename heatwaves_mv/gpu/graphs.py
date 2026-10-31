"""ComfyUI API-format graph builders, settings taken from the official templates
shipped with ComfyUI 0.43 (comfyui_workflow_templates):

  video_wan2_2_14B_i2v.json            Wan 2.2 I2V A14B (two experts) — 20 steps cfg 3.5 split 10 shift 5,
                                       or lightx2v 4-step LoRAs: 4 steps cfg 1 split 2
  video_hunyuan_video_1.5_720p_i2v     HunyuanVideo 1.5 720p I2V — cfg 6, shift 7, 20 steps, 121 f @ 24 fps
  image_qwen_image_edit_2511.json      Qwen-Image-Edit 2511 — 40 steps cfg 3, AuraFlow shift 3.1, CFGNorm
  utility_video_frame_interpolation    FILM / RIFE x2
  utility_seedvr2_*_upscale_video      SeedVR2 one-step video super-resolution
"""
import itertools


class G:
    """tiny graph builder: n = g.add('Class', input=..., other=(node, slot))"""

    def __init__(self):
        self.nodes = {}
        self._ids = itertools.count(1)

    def add(self, cls, **inputs):
        nid = str(next(self._ids))
        ins = {}
        for k, v in inputs.items():
            if isinstance(v, Ref):
                ins[k] = [v.nid, v.slot]
            else:
                ins[k] = v
        self.nodes[nid] = {'class_type': cls, 'inputs': ins}
        return Ref(nid)

    def json(self):
        return self.nodes


class Ref:
    def __init__(self, nid, slot=0):
        self.nid, self.slot = nid, slot

    def __getitem__(self, slot):
        return Ref(self.nid, slot)


NEG_WAN = ('色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，'
           '多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走')
NEG_ANIMA = ('worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, sepia, artist name, signature, '
             'watermark, text, logo, extra fingers, bad hands, deformed')


# ----------------------------------------------------------------------------------------
# stills
# ----------------------------------------------------------------------------------------
def t2i_anima(prompt, neg=NEG_ANIMA, w=1536, h=864, seed=0, model='anima-aesthetic-v1.1.safetensors', steps=30,
              cfg=4.5, sampler='er_sde', scheduler='simple', prefix='kf', loras=()):
    g = G()
    unet = g.add('UNETLoader', unet_name=model, weight_dtype='default')
    m = unet
    for name, s in loras:
        m = g.add('LoraLoaderModelOnly', model=m, lora_name=name, strength_model=s)
    clip = g.add('CLIPLoader', clip_name='qwen_3_06b_base.safetensors', type='stable_diffusion', device='default')
    vae = g.add('VAELoader', vae_name='qwen_image_vae.safetensors')
    pos = g.add('CLIPTextEncode', text=prompt, clip=clip)
    ng = g.add('CLIPTextEncode', text=neg, clip=clip)
    lat = g.add('EmptyLatentImage', width=w, height=h, batch_size=1)
    ks = g.add('KSampler', model=m, seed=seed, steps=steps, cfg=cfg, sampler_name=sampler, scheduler=scheduler,
               positive=pos, negative=ng, latent_image=lat, denoise=1.0)
    img = g.add('VAEDecode', samples=ks, vae=vae)
    g.add('SaveImage', images=img, filename_prefix=prefix)
    return g.json()


def edit_qwen2511(images, prompt, seed=0, steps=40, cfg=3.0, prefix='edit', neg='',
                  model='qwen_image_edit_2511_fp8mixed.safetensors', lightning=None):
    """identity-preserving edit with up to 3 reference images (uploaded names in ComfyUI/input)"""
    g = G()
    unet = g.add('UNETLoader', unet_name=model, weight_dtype='default')
    m = unet
    if lightning:
        m = g.add('LoraLoaderModelOnly', model=m, lora_name=lightning, strength_model=1.0)
        steps, cfg = 4, 1.0
    m = g.add('ModelSamplingAuraFlow', model=m, shift=3.1)
    m = g.add('CFGNorm', model=m, strength=1.0)
    clip = g.add('CLIPLoader', clip_name='qwen_2.5_vl_7b_fp8_scaled.safetensors', type='qwen_image', device='default')
    vae = g.add('VAELoader', vae_name='qwen_image_vae.safetensors')
    loads = [g.add('LoadImage', image=im) for im in images[:3]]
    first = g.add('FluxKontextImageScale', image=loads[0])
    refs = {f'image{i + 1}': (first if i == 0 else ld) for i, ld in enumerate(loads)}
    pos = g.add('TextEncodeQwenImageEditPlus', clip=clip, prompt=prompt, vae=vae, **refs)
    ng = g.add('TextEncodeQwenImageEditPlus', clip=clip, prompt=neg, vae=vae, **refs)
    pos = g.add('FluxKontextMultiReferenceLatentMethod', conditioning=pos, reference_latents_method='index_timestep_zero')
    ng = g.add('FluxKontextMultiReferenceLatentMethod', conditioning=ng, reference_latents_method='index_timestep_zero')
    lat = g.add('VAEEncode', pixels=first, vae=vae)
    ks = g.add('KSampler', model=m, seed=seed, steps=steps, cfg=cfg, sampler_name='euler', scheduler='simple',
               positive=pos, negative=ng, latent_image=lat, denoise=1.0)
    img = g.add('VAEDecode', samples=ks, vae=vae)
    g.add('SaveImage', images=img, filename_prefix=prefix)
    return g.json()


# ----------------------------------------------------------------------------------------
# video
# ----------------------------------------------------------------------------------------
def _save_video(g, frames, fps, prefix):
    vid = g.add('CreateVideo', images=frames, fps=float(fps))
    g.add('SaveVideo', video=vid, filename_prefix=prefix, format='mp4', codec='h264')


def i2v_wan22(start_image, prompt, neg=NEG_WAN, w=1280, h=720, frames=81, seed=0, end_image=None,
              lightning=False, steps=20, cfg=3.5, split=10, shift=5.0, prefix='wan', save_frames=False):
    """Wan 2.2 A14B image-to-video; with end_image -> first/last-frame conditioning"""
    if lightning:
        steps, cfg, split = 4, 1.0, 2
    g = G()
    hi = g.add('UNETLoader', unet_name='wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors', weight_dtype='default')
    lo = g.add('UNETLoader', unet_name='wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors', weight_dtype='default')
    if lightning:
        hi = g.add('LoraLoaderModelOnly', model=hi, lora_name='wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors',
                   strength_model=1.0)
        lo = g.add('LoraLoaderModelOnly', model=lo, lora_name='wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors',
                   strength_model=1.0)
    hi = g.add('ModelSamplingSD3', model=hi, shift=shift)
    lo = g.add('ModelSamplingSD3', model=lo, shift=shift)
    clip = g.add('CLIPLoader', clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors', type='wan', device='default')
    vae = g.add('VAELoader', vae_name='wan_2.1_vae.safetensors')
    pos = g.add('CLIPTextEncode', text=prompt, clip=clip)
    ng = g.add('CLIPTextEncode', text=neg, clip=clip)
    st = g.add('LoadImage', image=start_image)
    if end_image:
        en = g.add('LoadImage', image=end_image)
        cond = g.add('WanFirstLastFrameToVideo', positive=pos, negative=ng, vae=vae, width=w, height=h, length=frames,
                     batch_size=1, start_image=st, end_image=en)
    else:
        cond = g.add('WanImageToVideo', positive=pos, negative=ng, vae=vae, width=w, height=h, length=frames,
                     batch_size=1, start_image=st)
    k1 = g.add('KSamplerAdvanced', model=hi, add_noise='enable', noise_seed=seed, steps=steps, cfg=cfg,
               sampler_name='euler', scheduler='simple', positive=cond[0], negative=cond[1], latent_image=cond[2],
               start_at_step=0, end_at_step=split, return_with_leftover_noise='enable')
    k2 = g.add('KSamplerAdvanced', model=lo, add_noise='disable', noise_seed=seed, steps=steps, cfg=cfg,
               sampler_name='euler', scheduler='simple', positive=cond[0], negative=cond[1], latent_image=k1,
               start_at_step=split, end_at_step=10000, return_with_leftover_noise='disable')
    img = g.add('VAEDecode', samples=k2, vae=vae)
    if save_frames:
        g.add('SaveImage', images=img, filename_prefix=prefix)
    _save_video(g, img, 16, prefix)
    return g.json()


def i2v_hy15(start_image, prompt, neg='', w=1280, h=720, frames=121, seed=0, steps=20, cfg=6.0, shift=7.0,
             model='hunyuanvideo1.5_720p_i2v_fp16.safetensors', prefix='hy15', sr=False):
    """HunyuanVideo 1.5 720p image-to-video (+ optional 1080p latent SR pass)"""
    g = G()
    unet = g.add('UNETLoader', unet_name=model, weight_dtype='default')
    m = g.add('ModelSamplingSD3', model=unet, shift=shift)
    clip = g.add('DualCLIPLoader', clip_name1='qwen_2.5_vl_7b_fp8_scaled.safetensors',
                 clip_name2='byt5_small_glyphxl_fp16.safetensors', type='hunyuan_video_15', device='default')
    vae = g.add('VAELoader', vae_name='hunyuanvideo15_vae_fp16.safetensors')
    cv = g.add('CLIPVisionLoader', clip_name='sigclip_vision_patch14_384.safetensors')
    st = g.add('LoadImage', image=start_image)
    cvo = g.add('CLIPVisionEncode', clip_vision=cv, image=st, crop='center')
    pos = g.add('CLIPTextEncode', text=prompt, clip=clip)
    ng = g.add('CLIPTextEncode', text=neg, clip=clip)
    cond = g.add('HunyuanVideo15ImageToVideo', positive=pos, negative=ng, vae=vae, width=w, height=h, length=frames,
                 batch_size=1, start_image=st, clip_vision_output=cvo)
    noise = g.add('RandomNoise', noise_seed=seed)
    guider = g.add('CFGGuider', model=m, positive=cond[0], negative=cond[1], cfg=cfg)
    sampler = g.add('KSamplerSelect', sampler_name='euler')
    sigmas = g.add('BasicScheduler', model=m, scheduler='simple', steps=steps, denoise=1.0)
    out = g.add('SamplerCustomAdvanced', noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=cond[2])
    lat = out[0]
    if sr:
        ups = g.add('LatentUpscaleModelLoader', model_name='hunyuanvideo15_latent_upsampler_1080p.safetensors')
        up = g.add('HunyuanVideo15LatentUpscaleWithModel', model=ups, samples=lat, upscale_method='bilinear',
                   width=1920, height=1080, crop='disabled')
        sru = g.add('UNETLoader', unet_name='hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.safetensors',
                    weight_dtype='default')
        srm = g.add('ModelSamplingSD3', model=sru, shift=2.0)
        src = g.add('HunyuanVideo15SuperResolution', positive=pos, negative=ng, latent=up, noise_augmentation=0.7,
                    vae=vae, start_image=st, clip_vision_output=cvo)
        n2 = g.add('RandomNoise', noise_seed=seed + 1)
        g2 = g.add('CFGGuider', model=srm, positive=src[0], negative=src[1], cfg=1.0)
        s2 = g.add('BasicScheduler', model=srm, scheduler='simple', steps=8, denoise=1.0)
        o2 = g.add('SamplerCustomAdvanced', noise=n2, guider=g2, sampler=sampler, sigmas=s2, latent_image=src[2])
        lat = o2[0]
        img = g.add('VAEDecodeTiled', samples=lat, vae=vae, tile_size=512, overlap=64, temporal_size=64,
                    temporal_overlap=4096)
    else:
        img = g.add('VAEDecode', samples=lat, vae=vae)
    _save_video(g, img, 24, prefix)
    return g.json()


def interpolate(video, multiplier=2, fps_out=32, model='rife_v4.26.safetensors', prefix='interp'):
    """video = file name in ComfyUI/input (uploaded mp4)"""
    g = G()
    lv = g.add('LoadVideo', file=video)
    comp = g.add('GetVideoComponents', video=lv)
    im = g.add('FrameInterpolationModelLoader', model_name=model)
    fr = g.add('FrameInterpolate', interp_model=im, images=comp[0], multiplier=multiplier)
    _save_video(g, fr, fps_out, prefix)
    return g.json()


# ----------------------------------------------------------------------------------------
# character LoRA (native ComfyUI training)
# ----------------------------------------------------------------------------------------
def train_lora(dataset_folder, model='anima-base-v1.0.safetensors', steps=2400, lr=1e-4, rank=32, seed=0,
               prefix='loras/heatwaves_char', batch_size=1, grad_accum=4, offloading=False):
    """dataset_folder: a folder inside ComfyUI/input holding images + same-name .txt captions"""
    g = G()
    ds = g.add('LoadImageTextDataSetFromFolder', folder=dataset_folder)
    unet = g.add('UNETLoader', unet_name=model, weight_dtype='default')
    clip = g.add('CLIPLoader', clip_name='qwen_3_06b_base.safetensors', type='stable_diffusion', device='default')
    vae = g.add('VAELoader', vae_name='qwen_image_vae.safetensors')
    td = g.add('MakeTrainingDataset', images=ds[0], vae=vae, clip=clip, texts=ds[1])
    tr = g.add('TrainLoraNode', model=unet, latents=td[0], positive=td[1], batch_size=batch_size,
               grad_accumulation_steps=grad_accum, steps=steps, learning_rate=lr, rank=rank, optimizer='AdamW',
               loss_function='MSE', seed=seed, training_dtype='bf16', lora_dtype='bf16', quantized_backward=False,
               algorithm='LoRA', gradient_checkpointing=True, checkpoint_depth=1, offloading=offloading,
               existing_lora='[None]', bucket_mode=True, bypass_mode=False)
    g.add('SaveLoRA', lora=tr[0], prefix=prefix, steps=steps)
    return g.json()


# ----------------------------------------------------------------------------------------
# Apple Silicon variants (MPS: no fp8) — GGUF experts via ComfyUI-GGUF, or the 5B model in fp16
# ----------------------------------------------------------------------------------------
def i2v_wan22_gguf(start_image, prompt, neg=NEG_WAN, w=832, h=480, frames=81, seed=0, end_image=None,
                   quant='Q5_K_M', te='umt5-xxl-encoder-Q8_0.gguf', lightning=True, steps=20, cfg=3.5, split=10,
                   shift=5.0, prefix='wan_gguf'):
    """Wan 2.2 A14B I2V with GGUF experts (UnetLoaderGGUF / CLIPLoaderGGUF from ComfyUI-GGUF)"""
    if lightning:
        steps, cfg, split = 4, 1.0, 2
    g = G()
    hi = g.add('UnetLoaderGGUF', unet_name=f'Wan2.2-I2V-A14B-HighNoise-{quant}.gguf')
    lo = g.add('UnetLoaderGGUF', unet_name=f'Wan2.2-I2V-A14B-LowNoise-{quant}.gguf')
    if lightning:
        hi = g.add('LoraLoaderModelOnly', model=hi, lora_name='wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors',
                   strength_model=1.0)
        lo = g.add('LoraLoaderModelOnly', model=lo, lora_name='wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors',
                   strength_model=1.0)
    hi = g.add('ModelSamplingSD3', model=hi, shift=shift)
    lo = g.add('ModelSamplingSD3', model=lo, shift=shift)
    if te.endswith('.gguf'):
        clip = g.add('CLIPLoaderGGUF', clip_name=te, type='wan')
    else:
        clip = g.add('CLIPLoader', clip_name=te, type='wan', device='default')
    vae = g.add('VAELoader', vae_name='wan_2.1_vae.safetensors')
    pos = g.add('CLIPTextEncode', text=prompt, clip=clip)
    ng = g.add('CLIPTextEncode', text=neg, clip=clip)
    st = g.add('LoadImage', image=start_image)
    if end_image:
        en = g.add('LoadImage', image=end_image)
        cond = g.add('WanFirstLastFrameToVideo', positive=pos, negative=ng, vae=vae, width=w, height=h, length=frames,
                     batch_size=1, start_image=st, end_image=en)
    else:
        cond = g.add('WanImageToVideo', positive=pos, negative=ng, vae=vae, width=w, height=h, length=frames,
                     batch_size=1, start_image=st)
    k1 = g.add('KSamplerAdvanced', model=hi, add_noise='enable', noise_seed=seed, steps=steps, cfg=cfg,
               sampler_name='euler', scheduler='simple', positive=cond[0], negative=cond[1], latent_image=cond[2],
               start_at_step=0, end_at_step=split, return_with_leftover_noise='enable')
    k2 = g.add('KSamplerAdvanced', model=lo, add_noise='disable', noise_seed=seed, steps=steps, cfg=cfg,
               sampler_name='euler', scheduler='simple', positive=cond[0], negative=cond[1], latent_image=k1,
               start_at_step=split, end_at_step=10000, return_with_leftover_noise='disable')
    img = g.add('VAEDecode', samples=k2, vae=vae)
    _save_video(g, img, 16, prefix)
    return g.json()


def ti2v_wan22_5b(start_image, prompt, neg=NEG_WAN, w=1280, h=704, frames=121, seed=0, steps=20, cfg=5.0,
                  shift=8.0, te='umt5_xxl_fp16.safetensors', prefix='wan5b',
                  unet_name='wan2.2_ti2v_5B_fp16.safetensors'):
    """Wan 2.2 TI2V 5B (fp16, 720p, 24 fps) — the template settings: uni_pc 20 steps cfg 5 shift 8"""
    g = G()
    if unet_name.endswith('.gguf'):
        unet = g.add('UnetLoaderGGUF', unet_name=unet_name)
    else:
        unet = g.add('UNETLoader', unet_name=unet_name, weight_dtype='default')
    m = g.add('ModelSamplingSD3', model=unet, shift=shift)
    if te.endswith('.gguf'):
        clip = g.add('CLIPLoaderGGUF', clip_name=te, type='wan')
    else:
        clip = g.add('CLIPLoader', clip_name=te, type='wan', device='default')
    vae = g.add('VAELoader', vae_name='wan2.2_vae.safetensors')
    pos = g.add('CLIPTextEncode', text=prompt, clip=clip)
    ng = g.add('CLIPTextEncode', text=neg, clip=clip)
    st = g.add('LoadImage', image=start_image)
    lat = g.add('Wan22ImageToVideoLatent', vae=vae, width=w, height=h, length=frames, batch_size=1, start_image=st)
    ks = g.add('KSampler', model=m, seed=seed, steps=steps, cfg=cfg, sampler_name='uni_pc', scheduler='simple',
               positive=pos, negative=ng, latent_image=lat, denoise=1.0)
    img = g.add('VAEDecode', samples=ks, vae=vae)
    _save_video(g, img, 24, prefix)
    return g.json()


def upscale_video(video, model='2x-AnimeSharpV4_RCAN.safetensors', prefix='up', fps=32.0):
    """per-frame model upscale (fast on MPS); final resize to 1080p happens in the compositor"""
    g = G()
    lv = g.add('LoadVideo', file=video)
    comp = g.add('GetVideoComponents', video=lv)
    um = g.add('UpscaleModelLoader', model_name=model)
    up = g.add('ImageUpscaleWithModel', upscale_model=um, image=comp[0])
    _save_video(g, up, fps, prefix)
    return g.json()
