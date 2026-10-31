export const meta = {
  name: 'reference-mv-study-part',
  description: 'Every-frame study of a subset of reference-MV segments (and optionally pixel forensics); reports saved to files',
  phases: [{ title: 'Study', detail: 'segment readers / forensics' }],
}
const OUT = '/home/user/PPT/heatwaves_mv/design/ref_study'
const SEG_SCHEMA = {
  type: 'object',
  properties: {
    segment: { type: 'string' },
    sheets_viewed: { type: 'number' },
    keyframes_viewed: { type: 'number' },
    shots: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          start_s: { type: 'number' }, end_s: { type: 'number' },
          content: { type: 'string' }, composition: { type: 'string' }, camera: { type: 'string' },
          animation: { type: 'string' }, character: { type: 'string' }, background: { type: 'string' },
          typography: { type: 'string' }, palette: { type: 'string' }, pixel_treatment: { type: 'string' },
          transition_out: { type: 'string' }, music_sync: { type: 'string' },
          impressiveness: { type: 'number' }, why: { type: 'string' },
        },
        required: ['start_s', 'end_s', 'content', 'camera', 'animation', 'transition_out', 'impressiveness', 'why'],
      },
    },
    techniques: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['segment', 'sheets_viewed', 'keyframes_viewed', 'shots', 'techniques', 'weaknesses'],
}

const CONTEXT = `Context: an art-direction team is making TWO fan music videos for the song "Heat Waves" (Japanese version, Lime's cover of Glass Animals). One of them (MV-B) must adopt the visual style of a reference MV the client considers an aesthetic peak: 「[opus5.5]花30亿token制作的千本樱mv」 (Bilibili BV16MJY6yEKq), a 4:12, 30 fps, 1920x1080 music video for Hatsune Miku's 千本桜. Per its description it was made with Remotion (code-composited 2D motion graphics), Blender 3D scenes rendered via Blender MCP, and AI-generated Miku character art (Anima model in ComfyUI, cut out and retouched), all in a "pixel-like" look. The client says both of our MVs must clearly SURPASS it, and complained that a previous attempt had too many shots that were just a still picture slowly zooming or panning, and crude human silhouettes. So we need a precise, honest account of what the reference actually does, shot by shot, including how much real motion/animation each shot has.`


phase('Study')
const segs = args.segments || []
const segPrompt = (s) => `${CONTEXT}

You are studying ONE time segment of the reference: ${s.t0}s – ${s.t1}s (frames ${s.f0}–${s.f1}, 30 fps).

Files (use the Read tool on images; they are JPG/PNG):
1) Contact sheets that together show EVERY frame of your segment. Each sheet holds 64 consecutive frames in reading order (8 columns x 8 rows, left-to-right, top-to-bottom); each thumbnail is labelled "f<frame> <seconds>s". Read ALL of these, in order, without skipping — the client insists every single frame is looked at:
${s.sheets.map(p => '   - /tmp/claude-0/ref/every/' + p).join('\n')}
2) Full-resolution (1920x1080) keyframes taken from the middle of each shot that falls in your segment — read ALL of them to judge fine detail (pixel block size, dithering, line work, textures, typography, how the AI character art is integrated):
${s.keys.length ? s.keys.map(k => `   - /tmp/claude-0/ref/shotkeys/${k.p}  (shot ${k.a}s–${k.b}s)`).join('\n') : '   (none — no shot midpoint falls in this segment; rely on the sheets)'}
If something needs a closer look you may also extract extra full-res frames yourself: ffmpeg -v error -ss <seconds> -i /tmp/claude-0/ref/senbon.mp4 -frames:v 1 /tmp/claude-0/ref/extra_<seconds>.png  (then Read it).

Deliver, through the structured output:
- shots: EVERY shot/cut in your segment, in order (a "shot" = continuous camera/scene; note fast flash frames too). For each: start/end seconds; content (what is on screen); composition/framing; camera (static, pan, zoom, parallax depth, 3D camera move — and how fast); animation (EVERYTHING that moves inside the frame and how: character pose changes or frame-by-frame animation vs a still sprite sliding, hair/cloth motion, particles, petals, light flicker, 3D objects, looping elements; state plainly if the shot is just a still image being zoomed/panned); character (how Miku/the AI art is presented: full illustration, cut-out sprite, close-up, silhouette, pixelated or not, animated or static); background (pixel art, pixelated 3D render, flat vector graphics, photo-like, gradient...); typography (exact lyric text if readable, font style, size, placement, animate-in/out method); palette (main colours with approximate hex); pixel_treatment (estimated pixel block size in 1080p pixels, palette limitation, dithering pattern, outlines, CRT/scanlines/bloom/grain); transition_out (hard cut, flash, wipe type, zoom-through, match cut, glitch...); music_sync (cuts/accents on beats if inferable from rhythm of changes); impressiveness 1–10 and why.
- techniques: specific reusable techniques seen in this segment, concrete enough to implement.
- weaknesses: anything that looks cheap, repetitive, static, inconsistent, low-effort, or shows AI artefacts.
- sheets_viewed / keyframes_viewed: how many you actually read.
Be concrete and exhaustive; long answers are fine. Do not invent details you did not see.`

const forensicPrompt = `${CONTEXT}

Your job: QUANTITATIVE forensics of the reference's "pixel" rendering, so it can be reproduced exactly.
Material: the source video /tmp/claude-0/ref/senbon.mp4 (1920x1080, 30 fps, 7573 frames) and 91 full-res shot keyframes listed in /tmp/claude-0/ref/shotkeys/index.json (paths like /tmp/claude-0/ref/shotkeys/k01234.png, key_frame = frame number, shot_start/shot_end = frame range). Python 3 with numpy, opencv-python (cv2), Pillow and scipy is installed; ffmpeg is installed. Write scratch scripts and outputs under /tmp/claude-0/ref/forensics/ (create it).
Determine, with numbers and short evidence:
1) Internal render resolution / pixel grid: are frames drawn at a low internal resolution and upscaled with nearest neighbour? Estimate the block size per keyframe (e.g. run-length of identical-colour runs along rows/columns after denoising, or autocorrelation of the horizontal/vertical gradient), report the distribution across all 91 keyframes, and whether different layers (character vs background vs text vs particles) use different grids.
2) Palette: distinct colours per keyframe after clustering away compression noise (e.g. k-means in Lab with an elbow, or counting colours after rounding); typical palette size; is a global limited palette used, or free colour?
3) Dithering: none, ordered/Bayer, or error diffusion? Inspect 1:1 crops (crop ~400x300 regions with Python, save PNGs, and Read them to look).
4) Post effects: scanlines, CRT curvature, chromatic aberration, bloom/glow, film grain, vignette, colour grading — present or not, and how strong.
5) Motion: does the pixel grid stay locked when the camera moves (snapped integer scrolling) or do pixels shimmer/sub-pixel? Extract 3-4 consecutive frames from at least two moving shots (ffmpeg -ss <t> -i ... -frames:v 4 out_%d.png) and compare.
6) Text: are lyrics rendered as smooth anti-aliased type or pixel fonts? Typical sizes.
7) How the AI character art is integrated (same pixel grid? outlines? palette-reduced?).
Read enough crops yourself to be sure. Return a concise but complete Markdown report with the numbers, method notes, and a final "recipe to reproduce" section.`


const SAVE = (name) => `\n\nFinally, ALSO save your complete answer with the Write tool to ${OUT}/${name} (for structured answers: the same JSON object you return; for the forensic report: the Markdown). Then return.`
const jobs = segs.map(s => () => agent(segPrompt(s) + SAVE(`seg_${String(s.t0).replace('.', '_')}.json`), { label: `segment ${s.t0}-${s.t1}s`, phase: 'Study', schema: SEG_SCHEMA }))
if (args.forensic) jobs.push(() => agent(forensicPrompt + SAVE('forensics.md'), { label: 'pixel forensics', phase: 'Study' }))
const res = await parallel(jobs)
return { done: res.map(r => !!r), shots: res.filter(r => r && r.shots).map(r => ({ segment: r.segment, shots: r.shots.length, sheets: r.sheets_viewed, keys: r.keyframes_viewed })) }
