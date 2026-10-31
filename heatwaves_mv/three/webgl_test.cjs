const { chromium } = require('playwright');
const fs = require('fs');
const http = require('http');
const path = require('path');
const root = path.resolve('.');
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  const ext = path.extname(p);
  res.writeHead(200, { 'Content-Type': ext === '.js' || ext === '.mjs' ? 'text/javascript' : 'text/html' });
  fs.createReadStream(p).pipe(res);
}).listen(8731);
fs.writeFileSync('t.html', `<html><body style="margin:0"><canvas id=c width=960 height=540></canvas>
<script type=module>
import * as THREE from '/node_modules/three/build/three.module.js';
const r = new THREE.WebGLRenderer({canvas: document.getElementById('c'), antialias: false, preserveDrawingBuffer: true});
const sc = new THREE.Scene(); sc.background = new THREE.Color('#87b8e8'); sc.fog = new THREE.Fog('#bcd6ee', 30, 140);
const cam = new THREE.PerspectiveCamera(40, 960/540, 0.1, 500);
sc.add(new THREE.HemisphereLight('#ffffff', '#445566', 1.2)); const d = new THREE.DirectionalLight('#fff3d6', 2.5); d.position.set(30,50,20); d.castShadow = true; d.shadow.mapSize.set(1024,1024); sc.add(d);
r.shadowMap.enabled = true;
const g = new THREE.PlaneGeometry(400,400); const gm = new THREE.Mesh(g, new THREE.MeshToonMaterial({color:'#c9c2a8'})); gm.rotation.x=-Math.PI/2; gm.receiveShadow=true; sc.add(gm);
for (let i=0;i<300;i++){ const b=new THREE.Mesh(new THREE.BoxGeometry(2+Math.random()*4, 2+Math.random()*12, 2+Math.random()*4), new THREE.MeshToonMaterial({color:new THREE.Color().setHSL(Math.random(),0.3,0.6)})); b.position.set((Math.random()-0.5)*160, 3, (Math.random()-0.5)*160); b.castShadow=true; b.receiveShadow=true; sc.add(b);}
window.renderFrame = (t) => { cam.position.set(Math.sin(t*0.2)*40, 8+Math.sin(t)*2, Math.cos(t*0.2)*40); cam.lookAt(0,4,0); r.render(sc, cam); return document.getElementById('c').toDataURL('image/png'); };
window.ready = true;
</script></body></html>`);
(async () => {
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const pg = await b.newPage({ viewport: { width: 960, height: 540 } });
pg.on('console', m => console.log('page:', m.text()));
await pg.goto('http://127.0.0.1:8731/t.html'); await pg.waitForFunction('window.ready === true');
const info = await pg.evaluate(() => { const gl = document.getElementById('c').getContext('webgl2'); const e = gl.getExtension('WEBGL_debug_renderer_info'); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'n/a'; });
console.log('renderer:', info);
const t0 = Date.now(); let n = 0;
for (let i = 0; i < 30; i++) { const u = await pg.evaluate((t) => window.renderFrame(t), i / 30); if (i === 0) fs.writeFileSync('/tmp/claude-0/-home-user-PPT/6efd636e-b919-5534-8f1e-50b51caa0eb6/scratchpad/webgl0.png', Buffer.from(u.split(',')[1], 'base64')); n++; }
console.log('ms/frame', (Date.now() - t0) / n);
await b.close(); srv.close();

})();
