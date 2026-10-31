# Heat Waves (Japanese Version) — fan MV 「陽炎の向こうの君」

A non-commercial fan music video for **Glass Animals「Heat Waves」(Japanese cover & lyrics by Lime)**,
3:18, 1920×1080, 30 fps.

- `HeatWaves_MV_1080p.mp4`: the finished MV (H.264 + AAC)
- `STORYBOARD.md`: concept, palette and the full 64-shot list with timings
- `mv/`: the renderer (every frame is drawn by this code)
- `tools/`: character stylisation, chunked renderer, checks
- `assets/chars/`: the stylised character art used in the film

The song, recording and lyrics belong to their respective rights holders (Glass Animals / Polydor, Lime).
This video is a fan work and is not affiliated with them.

## How it is made

The look borrows the *craft* of 「花30亿token制作的千本樱mv」 (limited inks, flat shapes, a halftone screen
doing every gradient, so each frame reads like a riso / screen print with a pixel feel); the world, palette,
story and staging are new.

1. **Music analysis**: demucs splits the song into stems; the beat grid (81 BPM, 66 bars) is fitted on the drum
   stem; lyric line times come from a lyric video and are refined against vocal onsets (`mv/timing.py`).
2. **Renderer** (`mv/core.py`): Skia rasterises vector shapes in a 1920×1080 design space; numpy composites
   them as ink layers. Gradients and light go through an AM halftone screen (`halftone`, `ramp`); `heat_haze`
   is the signature vertical shimmer; TV pictures are real 320×180 ordered dither on a 16-colour palette with a
   CRT pass (`mv/el/tv.py`).
3. **Scenes** (`mv/el/`): sphere-shaded cumulonimbus, the perspective road with 逃げ水 mirage, utility poles and
   wires, the midnight room, the CRT, カーブミラー with a fisheye reflection, festival fireworks and goldfish, the
   station, the coastal railcar, the night town.
4. **Characters**: 君 was generated with **Anima-Turbo** in ComfyUI on CPU, cut out with anime-seg (ISNet), then
   re-inked by `tools/stylize.py`: cels flattened and snapped to the palette, line art re-inked in navy, shading
   stored as maps that turn into the *same* halftone screen as the backgrounds at render time, plus a fg/bg split
   with an inpainted background for 2.5D parallax.
5. **Edit** (`mv/shots/*.py`, `mv/edit.py`): 64 shots cut on bar lines, joined by halftone-dot, heat-haze, CRT,
   whip, wipe and flash transitions; Japanese lyrics typeset vertically with a Chinese translation beside them.

## Re-rendering

```bash
pip install numpy opencv-python-headless skia-python pillow librosa
tools/fetch_fonts.sh
HW_AUDIO=/path/to/heat_waves_japanese_version.wav python -m mv.render sheet --times 18,30,84 --res 960
HW_AUDIO=/path/to/heat_waves_japanese_version.wav python tools/render_chunks.py --workers 4
```

`python tools/check.py` renders the whole timeline at 320×180 and reports any shot that throws.
