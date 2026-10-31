export const meta = {
  name: 'design-mv-a',
  description: 'MV-A (free-style, highest quality) concept panel -> judged treatment -> per-section shot specs -> critique -> revision',
  phases: [
    { title: 'Concepts', detail: '4 independent treatments from different angles' },
    { title: 'Judge', detail: '3 judges score all treatments' },
    { title: 'Treatment', detail: 'synthesize the final treatment' },
    { title: 'Shots', detail: 'per-section shot specs' },
    { title: 'Review', detail: 'continuity + quality critics' },
    { title: 'Revise', detail: 'apply fixes per section' },
  ],
}

const CTX = '/home/user/PPT/heatwaves_mv/design/context.md'
const PRIOR = `A previous single version of this MV (code-drawn, halftone print look) used: a sleepless boy in a midnight tatami room lit by a CRT TV, a noon country road under cumulonimbus with 逃げ水 mirage, a カーブミラー convex traffic mirror, a festival with fireworks, a seaside station goodbye, a dawn ending. The client found it too static (many shots were a still picture zooming/panning) and the human figures crude. You may reuse, transform or discard any of these motifs.`

const COMMON = `You are a top-tier anime music-video director and storyboard artist. Read the production context pack first: ${CTX} (song structure, every lyric line with exact timing and a Chinese translation, beat grid, what the GPU generation pipeline can and cannot do, and the client's non-negotiable requirements).
${PRIOR}
This is MV-A: free creative direction, highest possible quality, anime illustration style rendered with AI keyframes + AI image-to-video + compositing. It must clearly surpass the reference MV「花30亿token制作的千本樱mv」 (a pixel-styled 千本桜 MV made with Remotion motion graphics, Blender 3D and AI character art).`

const TREATMENT_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' }, logline: { type: 'string' },
    story_arc: { type: 'array', items: { type: 'object', properties: { section: { type: 'string' }, beats: { type: 'string' } }, required: ['section', 'beats'] } },
    characters: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, design: { type: 'string' }, outfits: { type: 'string' }, anima_tags: { type: 'string' } }, required: ['name', 'design', 'anima_tags'] } },
    locations: { type: 'array', items: { type: 'string' } },
    visual_style: { type: 'string' }, color_script: { type: 'string' }, motifs: { type: 'string' },
    camera_language: { type: 'string' }, transition_grammar: { type: 'string' }, typography: { type: 'string' },
    signature_shots: { type: 'array', items: { type: 'string' } },
    why_it_surpasses: { type: 'string' }, risks: { type: 'string' },
  },
  required: ['title', 'logline', 'story_arc', 'characters', 'locations', 'visual_style', 'color_script', 'motifs', 'camera_language', 'transition_grammar', 'typography', 'signature_shots', 'why_it_surpasses', 'risks'],
}
const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      concept: { type: 'string' }, emotion: { type: 'number' }, visual_distinction: { type: 'number' }, lyric_fit: { type: 'number' },
      coherence_flow: { type: 'number' }, feasibility: { type: 'number' }, surpass_potential: { type: 'number' }, total: { type: 'number' },
      strengths: { type: 'string' }, weaknesses: { type: 'string' }, steal_ideas: { type: 'string' } },
      required: ['concept', 'total', 'strengths', 'weaknesses', 'steal_ideas'] } },
    winner: { type: 'string' }, rationale: { type: 'string' },
  },
  required: ['scores', 'winner', 'rationale'],
}
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

const SECTIONS = [
  ['intro', 0.0, 16.98], ['hook', 16.98, 28.83], ['chorus1', 28.83, 52.53], ['verse', 52.53, 76.24], ['chorus2', 76.24, 88.09],
  ['bridge1', 88.09, 111.79], ['chorus3', 111.79, 135.50], ['bridge2', 135.50, 147.35], ['chorus4', 147.35, 162.17],
  ['outro', 162.17, 185.87], ['outro_hook', 185.87, 198.74],
]

phase('Concepts')
const ANGLES = [
  ['cinematic', 'Narrative cinema: a deeply felt, specific love story told with Kyoto-Animation-level acting and Shinkai-level light; every shot advances the story; restraint and payoff.'],
  ['poetic', 'Visual poetry: Satoshi Kon / Masaaki Yuasa-style match cuts, memory and reality bleeding into each other through heat haze, mirrors and water; surprising but legible transitions.'],
  ['rhythmic', 'Music-driven choreography: the edit, camera moves, light pulses and kinetic typography are composed to the beat grid and the vocal phrasing; the drop at 16.98 s and the choruses hit like a live show.'],
  ['maximal', 'Production-smart maximalism: designed around what AI image-to-video does best (wind, light, water, fireworks, faces, camera moves) to maximize the visual payoff of every second while avoiding failure modes.'],
]
const concepts = await parallel(ANGLES.map(([key, angle]) => () => agent(`${COMMON}

Write ONE complete treatment for MV-A from this angle: ${angle}
Requirements: a single coherent story arc across all 11 sections (intro … outro_hook) that matches the lyric meaning line by line; two leads (a girl「君」and a boy「僕」, or another pairing if you justify it) with precise visual designs and Anima tag strings; 6–12 locations; a color script by section; recurring motifs; camera language; a transition grammar (how shots connect, with at least 6 named transition devices); a typography concept for Japanese lyrics + Chinese translation; 8–15 signature shots that would make viewers gasp; why it surpasses the reference; production risks.`, { label: `concept:${key}`, phase: 'Concepts', schema: TREATMENT_SCHEMA })))
const named = concepts.map((c, i) => c ? { key: ANGLES[i][0], ...c } : null).filter(Boolean)
log(`concepts: ${named.map(c => c.key + ' "' + c.title + '"').join(', ')}`)

phase('Judge')
const judgeLenses = ['emotional storytelling and lyric fit', 'visual distinction and craft (would it beat the reference MV?)', 'production feasibility with AI image-to-video and continuity/flow']
const verdicts = await parallel(judgeLenses.map(lens => () => agent(`${COMMON}

You are a judge. Score each of these ${named.length} MV-A treatments 1–10 on: emotion, visual_distinction, lyric_fit, coherence_flow, feasibility, surpass_potential (total = sum). Weigh especially: ${lens}. Name a winner and list the best ideas to steal from the others.

Treatments (JSON): ${JSON.stringify(named)}`, { label: `judge:${lens.split(' ')[0]}`, phase: 'Judge', schema: SCORE_SCHEMA })))

phase('Treatment')
const finalT = await agent(`${COMMON}

Synthesize the FINAL MV-A treatment: start from the concept the judges rate highest overall, graft the best ideas they flagged from the others, and fix the weaknesses they raised. Keep one coherent story. Be specific: character designs must be precise enough to generate consistently (hair, eyes, face, height/age, every outfit, accessories), and the color script and transition grammar concrete.

Treatments: ${JSON.stringify(named)}
Judge verdicts: ${JSON.stringify(verdicts.filter(Boolean))}`, { label: 'final treatment', phase: 'Treatment', schema: TREATMENT_SCHEMA })

phase('Shots')
const shotPrompt = (s) => `${COMMON}

FINAL TREATMENT (follow it exactly): ${JSON.stringify(finalT)}

Design the complete shot list for section "${s[0]}" covering ${s[1]}s to ${s[2]}s with no gaps or overlaps (t0 of the first shot = ${s[1]}, t1 of the last = ${s[2]}). Cut on bar lines (bar m starts at 2.1635 + m*2.9630 s) or on beats for fast passages; typical shot 1–6 s. Every lyric line in this window must be covered by exactly one or more shots (lyric_ids). For EACH shot give:
- summary, camera (move + speed), action (what genuinely moves: acting, hair/cloth, environment, light — never a static picture zooming);
- keyframe_prompt: an Anima prompt (Danbooru-style tags + natural language; write character tokens as <kimi> / <boku> plus their outfit tags; include lighting, lens, composition, palette); keyframe_notes (composition, must-haves);
- edit_refs (which character sheets/outfits are needed);
- video_mode: i2v (image-to-video from the keyframe), flf (first+last keyframe morph — give end_keyframe_prompt), chain (continuation of the previous shot's last frame), or composite (typography/graphic/compositing-built shot that still has real motion);
- video_prompt: an English motion prompt for the image-to-video model (subject motion + camera motion + atmosphere, 1–3 sentences);
- clip_seconds (generated length, <=5 per clip, chain for longer), speed (playback retime);
- typography (how the lyric appears: vertical/horizontal, placement, font feel, animation in/out, Chinese translation placement);
- transition_out (named device from the transition grammar), sync (which beats/accents the cut or motion hits), risk_fallback (what may fail in generation and the fallback).
Shot ids: "A-${s[0]}-01", "A-${s[0]}-02", ...`
const sections = await parallel(SECTIONS.map(s => () => agent(shotPrompt(s), { label: `shots:${s[0]}`, phase: 'Shots', schema: SECTION_SCHEMA })))
const okSections = sections.map((r, i) => r ? r : null)
const miss = SECTIONS.filter((s, i) => !okSections[i]).map(s => s[0])
if (miss.length) log(`WARNING: no shot list for sections: ${miss.join(', ')}`)
log(`shots designed: ${okSections.filter(Boolean).reduce((a, r) => a + r.shots.length, 0)}`)

phase('Review')
const allShots = okSections.filter(Boolean)
const reviews = await parallel([
  () => agent(`${COMMON}
FINAL TREATMENT: ${JSON.stringify(finalT)}
You are the continuity & coverage critic. Check the full MV-A shot list below for: timeline gaps/overlaps (0–198.74 s), every lyric line (ids 0–66) covered at the right time, cuts on bar lines/beats, story continuity across shots and sections (characters, outfits, time of day, props), motion in every shot (flag any shot that is effectively a still image), variety of shot sizes/angles/moves, transition logic, typography consistency. Return concrete fixes per shot.
SHOT LIST: ${JSON.stringify(allShots)}`, { label: 'critic:continuity', phase: 'Review', schema: REVIEW_SCHEMA }),
  () => agent(`${COMMON}
FINAL TREATMENT: ${JSON.stringify(finalT)}
You are the quality critic: would each shot clearly surpass the reference MV and impress a demanding Bilibili audience? Flag weak, generic, repetitive or risky shots; check the keyframe prompts would actually produce the intended image with an anime model, and the video prompts describe motion an image-to-video model can deliver; demand stronger signature moments where the music peaks (16.98 s drop, chorus entries, 111.8 s climax, 162.2 s outro chorus). Return concrete fixes per shot.
SHOT LIST: ${JSON.stringify(allShots)}`, { label: 'critic:quality', phase: 'Review', schema: REVIEW_SCHEMA }),
])
const fixes = reviews.filter(Boolean).flatMap(r => r.fixes)
const globalNotes = reviews.filter(Boolean).map(r => r.global_notes).join('\n\n')
log(`review fixes: ${fixes.length}`)

phase('Revise')
const revised = await parallel(SECTIONS.map((s, i) => () => {
  const sec = okSections[i]
  if (!sec) return Promise.resolve(null)
  const mine = fixes.filter(f => f.section === s[0] || (f.shot_id || '').startsWith(`A-${s[0]}-`))
  if (!mine.length) return Promise.resolve(sec)
  return agent(`${COMMON}
FINAL TREATMENT: ${JSON.stringify(finalT)}
GLOBAL NOTES FROM CRITICS: ${globalNotes}
Revise the shot list for section "${s[0]}" (${s[1]}–${s[2]} s) applying ALL of these fixes; keep everything else; keep the time window fully covered with no gaps/overlaps; return the complete revised section.
FIXES: ${JSON.stringify(mine)}
CURRENT SECTION: ${JSON.stringify(sec)}`, { label: `revise:${s[0]}`, phase: 'Revise', schema: SECTION_SCHEMA })
}))
return { treatment: finalT, concepts: named, verdicts: verdicts.filter(Boolean), sections: revised.map((r, i) => r || okSections[i]), reviews: reviews.filter(Boolean) }
