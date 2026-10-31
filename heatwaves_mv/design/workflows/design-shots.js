export const meta = {
  name: 'design-shots',
  description: 'Per-section shot specs from a final treatment, critics, revisions — all written to files',
  phases: [
    { title: 'Shots', detail: 'one agent per group of sections, writes shots_<section>.json' },
    { title: 'Review', detail: 'continuity + quality critics read every section file' },
    { title: 'Revise', detail: 'apply critic fixes per section group' },
  ],
}
const CTX = '/home/user/PPT/heatwaves_mv/design/context.md'
const PRIOR0 = `A previous single version of this MV (code-drawn, halftone print look) used: a sleepless boy in a midnight tatami room lit by a CRT TV, a noon country road under cumulonimbus with 逃げ水 mirage, a カーブミラー convex traffic mirror, a festival with fireworks, a seaside station goodbye, a dawn ending. The client found it too static (many shots were a still picture zooming/panning) and the human figures crude. You may reuse, transform or discard any of these motifs.`

const COMMON0 = `You are a top-tier anime music-video director and storyboard artist. Read the production context pack first: ${CTX} (song structure, every lyric line with exact timing and a Chinese translation, beat grid, what the GPU generation pipeline can and cannot do, and the client's non-negotiable requirements).
${PRIOR}
This is MV-A: free creative direction, highest possible quality, anime illustration style rendered with AI keyframes + AI image-to-video + compositing. It must clearly surpass the reference MV「花30亿token制作的千本樱mv」 (a pixel-styled 千本桜 MV made with Remotion motion graphics, Blender 3D and AI character art).`


const MV = args.mv            // 'A' or 'B'
const OUT = args.out_dir      // e.g. /home/user/PPT/heatwaves_mv/design/mv_a
const BRIEF = args.brief || '' // extra brief (style bible path for MV-B)
const PRIOR = PRIOR0
const COMMON = (MV === 'A' ? COMMON0 : COMMON0.replace(/This is MV-A[\s\S]*$/, '')) + BRIEF
const SHOT = {
  type: 'object',
  properties: {
    id: { type: 'string' }, t0: { type: 'number' }, t1: { type: 'number' }, lyric_ids: { type: 'array', items: { type: 'number' } },
    summary: { type: 'string' }, camera: { type: 'string' }, action: { type: 'string' },
    keyframe_prompt: { type: 'string' }, keyframe_notes: { type: 'string' },
    edit_refs: { type: 'array', items: { type: 'string' } },
    video_mode: { type: 'string', enum: ['i2v', 'flf', 'chain', 'composite'] },
    video_prompt: { type: 'string' }, end_keyframe_prompt: { type: 'string' },
    clip_seconds: { type: 'number' }, speed: { type: 'number' },
    typography: { type: 'string' }, transition_out: { type: 'string' }, sync: { type: 'string' }, risk_fallback: { type: 'string' },
  },
  required: ['id', 't0', 't1', 'lyric_ids', 'summary', 'camera', 'action', 'keyframe_prompt', 'video_mode', 'video_prompt', 'clip_seconds', 'typography', 'transition_out', 'sync', 'risk_fallback'],
}
const SECTION_SCHEMA = { type: 'object', properties: { section: { type: 'string' }, notes: { type: 'string' }, shots: { type: 'array', items: SHOT } }, required: ['section', 'shots'] }
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    global_notes: { type: 'string' },
    fixes: { type: 'array', items: { type: 'object', properties: { section: { type: 'string' }, shot_id: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['section', 'problem', 'fix'] } },
  },
  required: ['global_notes', 'fixes'],
}


const SECTIONS = args.sections   // [[name, t0, t1], ...]
const GROUPS = args.groups       // [[name, name, ...], ...] sections handled together by one agent
const TREAT = `${OUT}/treatment.json`

phase('Shots')
const shotJob = (names) => {
  const secs = SECTIONS.filter(s => names.includes(s[0]))
  return agent(`${COMMON}

Read the FINAL TREATMENT (follow it exactly): ${TREAT}
You design the complete shot lists for these consecutive sections: ${secs.map(s => `"${s[0]}" ${s[1]}–${s[2]} s`).join(', ')}.
For EACH section: cover its window with no gaps or overlaps (first shot t0 = section start, last t1 = section end). Cut on bar lines (bar m starts at 2.1635 + m*2.9630 s) or beats for fast passages; typical shot 1–6 s. Every lyric line in the window must be covered (lyric_ids). For EACH shot give:
- id ("${MV}-<section>-01", "-02", ...), t0, t1, lyric_ids, summary, camera (move + speed), action (what genuinely moves: acting, hair/cloth, environment, light — never a static picture zooming);
- keyframe_prompt: an Anima prompt (Danbooru tags + natural language; write character tokens as <kimi> / <boku> followed by outfit tags; lighting, lens, composition, palette); keyframe_notes;
- edit_refs (character sheets/outfits needed);
- video_mode: i2v | flf (first+last keyframe morph — give end_keyframe_prompt) | chain (continues the previous shot's last frame) | composite (typography/graphic/compositing shot that still has real motion);
- video_prompt (English motion prompt for the image-to-video model: subject motion + camera motion + atmosphere, 1–3 sentences);
- clip_seconds (<=5 per generated clip; chain for longer), speed (playback retime);
- typography (lyric placement/orientation/animation, Chinese translation placement), transition_out (named device), sync (beats/accents hit), risk_fallback.
Write each section to its own file with the Write tool: ${OUT}/shots_<section>.json containing {"section": ..., "notes": ..., "shots": [...]}. Validate the JSON (python3 -c 'import json;json.load(open(...))'). Return one short line per section: name, shot count.`, { label: `shots:${names.join('+')}`, phase: 'Shots' })
}
const shotRes = await parallel(GROUPS.map(g => () => shotJob(g)))
log(`shot agents: ${shotRes.filter(Boolean).length}/${GROUPS.length}`)

phase('Review')
const files = SECTIONS.map(s => `${OUT}/shots_${s[0]}.json`).join(', ')
const critic = (role, focus, name) => agent(`${COMMON}

Read the FINAL TREATMENT ${TREAT} and EVERY section file: ${files}.
You are the ${role}. ${focus}
Write your findings as JSON {"global_notes": "...", "fixes": [{"section": ..., "shot_id": ..., "problem": ..., "fix": ...}]} to ${OUT}/${name} with the Write tool (validate the JSON). Return the number of fixes.`, { label: `critic:${role}`, phase: 'Review' })
await parallel([
  () => critic('continuity & coverage critic', 'Check: timeline gaps/overlaps over 0–198.74 s, every lyric line (ids 0–66) covered at the right time, cuts on bar lines/beats, story continuity across shots and sections (characters, outfits, time of day, props), real motion in every shot (flag anything that is effectively a still image), variety of shot sizes/angles/moves, transition logic, typography consistency.', 'review_continuity.json'),
  () => critic('quality critic', 'Would each shot clearly surpass the reference MV and impress a demanding Bilibili audience? Flag weak, generic, repetitive or risky shots; check keyframe prompts would really produce the intended image with an anime model and video prompts describe motion image-to-video can deliver; demand stronger signature moments at the music peaks (16.98 s drop, chorus entries, 111.8 s climax, 162.2 s outro chorus).', 'review_quality.json'),
])

phase('Revise')
const revRes = await parallel(GROUPS.map(g => () => agent(`${COMMON}

Read the FINAL TREATMENT ${TREAT}, the critics' findings ${OUT}/review_continuity.json and ${OUT}/review_quality.json, and your section files: ${g.map(n => `${OUT}/shots_${n}.json`).join(', ')}.
Apply EVERY fix that concerns your sections (${g.join(', ')}) plus the global notes where relevant; keep everything else; keep each section window fully covered with no gaps/overlaps. Overwrite each section file with the revised version (same JSON shape; validate it). Return one short line per section: name, shot count, fixes applied.`, { label: `revise:${g.join('+')}`, phase: 'Revise' })))
return { shots: shotRes, revised: revRes }
