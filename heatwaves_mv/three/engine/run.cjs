// Render a scene module to PNG frames with headless Chromium (SwiftShader WebGL2).
//   node engine/run.cjs --scene s2_coast --t0 0 --t1 4 --fps 24 --out /tmp/frames [--w 1920 --h 1080]
//        [--params '{"world":"night"}'] [--beats 0.682,0.74075]   (first beat, beat length -> pulse)
const { chromium } = require('playwright');
const fs = require('fs');
const http = require('http');
const path = require('path');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1]]);
  return a;
}, []));
const root = path.resolve(__dirname, '..');
const W = +(args.w || 1920), H = +(args.h || 1080), fps = +(args.fps || 24);
const t0 = +(args.t0 || 0), t1 = +(args.t1 || 2);
const out = args.out || '/tmp/frames';
const [beat0, beatLen] = (args.beats || '0.682,0.74075').split(',').map(Number);
fs.mkdirSync(out, { recursive: true });
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  const ext = path.extname(p);
  const types = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.html': 'text/html', '.png': 'image/png',
                  '.jpg': 'image/jpeg', '.json': 'application/json', '.mp4': 'video/mp4' };
  res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0);
(async () => {
  const port = srv.address().port;
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                           '--ignore-gpu-blocklist', '--js-flags=--max-old-space-size=4096'] });
  const pg = await b.newPage({ viewport: { width: W, height: H } });
  pg.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('page:', m.text()); });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  const q = `scene=${args.scene}&w=${W}&h=${H}&aa=${args.aa || '1'}&params=${encodeURIComponent(args.params || '{}')}`;
  await pg.goto(`http://127.0.0.1:${port}/engine/page.html?${q}`);
  await pg.waitForFunction('window.ready === true', null, { timeout: 120000 });
  const n = Math.round((t1 - t0) * fps);
  const start = Date.now();
  const anchors = [];
  for (let i = 0; i < n; i++) {
    const t = t0 + i / fps;
    const sinceBeat = ((t - beat0) % beatLen + beatLen) % beatLen;
    const pulse = Math.exp(-sinceBeat / 0.12);
    const url = await pg.evaluate(([t, p, i]) => window.renderAt(t, p, i), [t, pulse, Math.round(t * fps)]);
    fs.writeFileSync(path.join(out, `f_${String(i).padStart(5, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
    anchors.push(await pg.evaluate(() => (window.anchors ? window.anchors() : null)));
  }
  if (anchors.some(a => a)) fs.writeFileSync(path.join(out, 'anchors.json'), JSON.stringify(anchors));
  console.log(`${args.scene}: ${n} frames in ${((Date.now() - start) / 1000).toFixed(1)}s -> ${out}`);
  await b.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });
