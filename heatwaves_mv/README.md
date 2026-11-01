# Heat Waves (Japanese Version) — fan music video

A non-commercial fan music video for **Glass Animals「Heat Waves」(Japanese cover and lyrics by Lime)**,
3:18, 1920×1080, 24 fps.

The film: `HeatWaves_720p.mp4` in this folder is a copy small enough for the repository; the full-quality
`HeatWaves_1080p.mp4` is delivered alongside it (`tools/v2_final.sh` re-renders the CRF-15 master and both encodes). `poster.jpg` shows twenty of its moments. The
repository holds everything that makes the film. The song, recording and lyrics belong to their rights holders (Glass
Animals / Polydor, Lime); this is a fan work, not affiliated with them.

## The film

A summer in a small coastal town in 1985, printed like a riso / screen print that moves. Just after midnight a boy
cannot sleep with the old CRT on; a stamp-rally card on the low table still has its sixth cell empty — the sunrise
at the lighthouse, the one stamp they never collected. Through the night the song's images come back to him in
heat haze and curve mirrors: her walk on the noon road, the pool, the festival, the chalk umbrella on the seawall.
At dawn he walks the coast to the lighthouse, the sixth stamp lands in its cell, the card flies off toward the sun,
and at the end the print runs backwards to bare paper, leaving only the sun stamp.

- **Lyrics:** the original Japanese lines only, set vertically in Mincho; the English lines run on a station-style
  dot-matrix LED strip.
- **The print:** every frame of generated anime footage is printed by `mvb/print2.py`: ~22 flat inks fitted per shot
  and harmonised with the section's colour world, a 45° halftone screen carrying the shading, a 15° light screen,
  AM halos around light sources, key lines (gold on dark inks), cream paper, grain and gate weave
  (measured from the reference, `design/ref_study/forensics.md`). Faces print clean on a warm cream -- only on
  people: anime person / face detection and character segmentation gate it (`mvb/people.py`), and the detected
  faces anchor the skin colour, so a sunset cloud, a lantern or a wall in dusk light keeps its own ink.
- **The town is real:** the map and the stamp card are drawn from OpenStreetMap data of the Enoden coast
  (Koshigoe – Shichirigahama – Enoshima), renamed 潮見 (Shiomi): every building footprint, the coastal railway,
  the streets the stamp route follows (`mvb/shiomi_map.py`, `mvb/card2.py`).
- **Devices** composited into the footage (`mvb/v2_*.py`): her moments swimming inside tracked curve mirrors, the
  title rising out of a mirage, the press printing itself plate by plate at the start and running backwards at the
  end, LED clocks and boards, CRT channels, tanzaku strips, lyric bubbles, chalk drawings, fireworks that spell
  glyphs, a goldfish school spelling 幸せ, a duotone dream, a zoetrope train, the night-to-dawn plate peel. Signs,
  screens, clocks and the card follow the footage with a planar tracker (`mvb/v2_fx.py`).

## How it is made

1. **Music** (`mv/timing.py`, `assets/glyph_times.json`): beat grid fitted on the drum stem (81 BPM), lyric lines
   and per-glyph sung times aligned to the vocal stem.
2. **Generation** on an Apple M4 Mac with ComfyUI (`gpu/`, `GPU_RUNBOOK.md`): Anima keyframes (two candidates per
   shot, picked by review), Wan 2.2 TI2V 5B video (832×480, 16 fps; shots with a broken face, colour drift or stray
   marks re-rolled after review), RIFE ×3 interpolation and a 2× AnimeSharp upscale to 1920×1108 at 24 fps; the shot
   list with prompts is `design/mv_b/gpu_shots_v2.json`. Media travel to the cloud on the `hw-media` branch
   (`gpu/push_media.sh` → `tools/ingest_media.py`).
3. **Compositing** on CPU (`mvb/v2.py` + `mvb/v2_*.py`): per shot, raw stage (footage + devices + heat shimmer and
   glow) → print → graphics over the print (LED, stamps, lyrics).
4. **Render and checks:** `tools/render_mvb.py --mv b2` (per-shot caches warmed in parallel, then the film in 16
   parts, each in a fresh process that is retried if it dies; complete parts are kept, so a fix re-renders only the
   parts it touches), `tools/qa_video.py` (duration, audio, W3C general-flash check), `tools/deliver.sh` (delivery
   encodes).

```bash
python3 -m mvb.people                                         # the print's people models (once)
python3 tools/ingest_media.py --only work/B2                 # footage from the hw-media branch
bash tools/v2_final.sh                                        # render -> QA -> out/deliver/HeatWaves_*.mp4
```

## Credits and data

- Map data © OpenStreetMap contributors, available under the Open Database License (ODbL 1.0).
- Fonts: Shippori Mincho, Zen Old Mincho, Zen Kaku Gothic New, DotGothic16, EB Garamond, Silkscreen and others under
  the SIL Open Font License (`assets/fonts/`).
- Models: Anima (keyframes), Wan 2.2 TI2V 5B (video), RIFE (frame interpolation), an anime upscaler;
  for the print, SkyTNT anime-segmentation ISNet (Apache-2.0) and deepghs anime person / face detection (MIT),
  fetched by `python3 -m mvb.people`.

## Earlier versions in this repository

- `STORYBOARD.md`, `mv/`: v1 「陽炎の向こうの君」, drawn entirely by a 2D renderer (its film is
  `HeatWaves_MV_1080p.mp4`).
- `mvb/recipes.py`, `three/`: MV-B v1, three.js plates printed in the same style (superseded by v2; its recipes are
  the fallback for any shot without footage).
- `mva/`: a cinematic version that was discontinued.
