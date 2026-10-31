// S1: six-tatami room at night, CRT TV (screen anchor for 2D inserts), oscillating fan, curtain, window onto
// the railway, futon, wall calendar (16 circled), LED clock. params.cam: 'ozu' | 'tv' | 'over' | 'window'
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

function canvasTex(P, w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  return P.flatTex(c);
}

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'night'];
  const root = new THREE.Scene();
  const scene = new THREE.Group(); root.add(scene);
  P.U.uFogColor.value.set('#0B1026'); P.U.uFogNear.value = 30; P.U.uFogFar.value = 80;
  P.U.uPeriod.value = params.period || 8;
  const tvLight = new THREE.Vector3(0.15, 0.35, 1.0).normalize();         // light comes from the TV (front wall)
  P.U.uLightDir.value.copy(tvLight);
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  const RW = 3.6, RD = 2.7, RH = 2.4;
  const wallMat = P.ink(params.wall || '#3F5F8F', { shade: '#141A33', ambient: 0.25 });
  const floorTex = canvasTex(P, 512, 384, (g, w, h) => {
    g.fillStyle = '#5E6E86'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#1E2550'; g.lineWidth = 6;
    const cells = [[0, 0, 256, 192], [256, 0, 256, 192], [0, 192, 170, 192], [170, 192, 171, 192], [341, 192, 171, 192]];
    for (const [x, y, cw, ch] of cells) g.strokeRect(x + 3, y + 3, cw - 6, ch - 6);
    g.fillStyle = 'rgba(20,26,51,0.18)';
    for (let i = 0; i < w; i += 5) g.fillRect(i, 0, 1, h);
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(RW, RD), floorTex); floor.rotation.x = -Math.PI / 2; scene.add(floor);
  const back = box(RW, RH, 0.05, wallMat); back.position.set(0, RH / 2, -RD / 2); scene.add(back);
  const left = box(0.05, RH, RD, wallMat); left.position.set(-RW / 2, RH / 2, 0); scene.add(left);
  const ceil = box(RW, 0.05, RD, P.ink('#1E2550', { ambient: 0.4 })); ceil.position.set(0, RH, 0); scene.add(ceil);
  // right wall with a window (two wall pieces + sill), outside: night railway lights
  const rwMat = wallMat;
  const r1 = box(0.05, RH, 0.7, rwMat); r1.position.set(RW / 2, RH / 2, -RD / 2 + 0.35); scene.add(r1);
  const r2 = box(0.05, RH, 0.7, rwMat); r2.position.set(RW / 2, RH / 2, RD / 2 - 0.35); scene.add(r2);
  const r3 = box(0.05, 0.8, RD - 1.4, rwMat); r3.position.set(RW / 2, 0.4, 0); scene.add(r3);
  const r4 = box(0.05, 0.5, RD - 1.4, rwMat); r4.position.set(RW / 2, RH - 0.25, 0); scene.add(r4);
  const outside = new THREE.Mesh(new THREE.PlaneGeometry(6, 3), canvasTex(P, 600, 300, (g, w, h) => {
    g.fillStyle = '#141A33'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#26345E'; g.fillRect(0, 160, w, 140);
    g.fillStyle = '#F0B45A'; for (let i = 0; i < 9; i++) g.fillRect(40 + i * 62, 150 + (i % 3) * 6, 14, 10);
    g.fillStyle = '#EDE3CF'; g.beginPath(); g.arc(470, 70, 26, 0, 7); g.fill();
  }));
  outside.position.set(RW / 2 + 1.2, 1.3, 0); outside.rotation.y = -Math.PI / 2; scene.add(outside);
  // curtain: thin plane that breathes
  const curtainMat = P.ink('#C9D3DC', { shade: '#5E6E86', ambient: 0.45, side: THREE.DoubleSide, grain: 0.18 });
  const curtain = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1.3, 12, 1), curtainMat);
  curtain.position.set(RW / 2 - 0.08, 1.45, 0.45); curtain.rotation.y = -Math.PI / 2; scene.add(curtain);
  const cBase = curtain.geometry.attributes.position.array.slice();
  // CRT TV on a low cabinet against the back wall
  const cab = P.outlined(box(1.0, 0.45, 0.45, P.ink('#5A3E36', { shade: '#2A1C1A' })), '#120C10', 0.015);
  cab.position.set(-0.6, 0.225, -RD / 2 + 0.3); scene.add(cab);
  const tvBody = P.outlined(box(0.72, 0.56, 0.5, P.ink('#2A2A35', { shade: '#141018', hi: '#8E95A6' })), '#0A080C', 0.015);
  tvBody.position.set(-0.6, 0.45 + 0.28, -RD / 2 + 0.3); scene.add(tvBody);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.54, 0.4), P.ink('#7FC8B8', { emissive: 1.0 }));
  screen.position.set(-0.62, 0.73, -RD / 2 + 0.556); scene.add(screen);
  const tvGlow = P.glow('#7FC8B8', 1.3, { strength: 0.42 }); tvGlow.position.set(-0.62, 0.74, -RD / 2 + 0.75); scene.add(tvGlow);
  for (const s of [-1, 1]) {   // rabbit-ear antenna
    const a = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.6, 4), P.ink('#C9D3DC', { flat: 1 }));
    a.position.set(-0.6 + s * 0.12, 1.25, -RD / 2 + 0.3); a.rotation.z = -s * 0.45; scene.add(a);
  }
  // oscillating fan
  const fanGrp = new THREE.Group(); fanGrp.position.set(0.55, 0, -RD / 2 + 0.45); scene.add(fanGrp);
  const fanMat = P.ink('#C9D3DC', { shade: '#3F5F8F', hi: '#FFFFFF' });
  const fbase = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 0.06, 18), fanMat); fbase.position.y = 0.03; fanGrp.add(fbase);
  const fpole = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.75, 8), fanMat); fpole.position.y = 0.4; fanGrp.add(fpole);
  const head = new THREE.Group(); head.position.y = 0.8; fanGrp.add(head);
  const cage = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.008, 6, 32), fanMat); head.add(cage);
  const blades = new THREE.Mesh(new THREE.CircleGeometry(0.15, 24), P.ink('#7FA7C9', { flat: 0.6, grain: 0.35, side: THREE.DoubleSide }));
  blades.position.z = 0.01; head.add(blades);
  const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.12, 12), fanMat); motor.rotation.x = Math.PI / 2; motor.position.z = -0.08; head.add(motor);
  // futon + pillow
  const futon = P.outlined(box(1.0, 0.09, 1.9, P.ink('#EDE3CF', { shade: '#7FA7C9', grain: 0.12 })), '#1A1416', 0.012);
  futon.position.set(0.6, 0.045, 0.25); scene.add(futon);
  const blanket = P.outlined(box(1.02, 0.05, 1.0, P.ink('#7FC8B8', { shade: '#2C4C9A', grain: 0.2 })), '#1A1416', 0.012);
  blanket.position.set(0.6, 0.11, 0.55); scene.add(blanket);
  const pillow = P.outlined(box(0.5, 0.1, 0.32, P.ink('#F2C9A0', { shade: '#8C6E63' })), '#1A1416', 0.01);
  pillow.position.set(0.6, 0.14, -0.55); scene.add(pillow);
  // wall calendar: June, 16 circled in red
  const cal = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.56), canvasTex(P, 420, 560, (g, w, h) => {
    g.fillStyle = '#EDE3CF'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#141A33'; g.font = 'bold 92px serif'; g.fillText('6', 24, 110);
    g.font = '22px serif'; g.fillText('JUNE', 90, 104);
    g.font = '24px serif';
    let d = 1;
    for (let r = 0; r < 5; r++) for (let c = 0; c < 7; c++) {
      if (r === 0 && c < 3) continue; if (d > 30) break;
      g.fillStyle = c === 0 ? '#D9402B' : '#141A33';
      g.fillText(String(d), 22 + c * 56, 190 + r * 70);
      if (d === 16) { g.strokeStyle = '#D9402B'; g.lineWidth = 5; g.beginPath(); g.ellipse(36 + c * 56, 181 + r * 70, 28, 24, 0, 0, 7); g.stroke(); }
      d++;
    }
  }));
  cal.position.set(1.15, 1.6, -RD / 2 + 0.03); scene.add(cal);
  // LED clock on the floor by the pillow
  const clockFace = document.createElement('canvas'); clockFace.width = 256; clockFace.height = 96;
  const clockMat = P.flatTex(clockFace);
  const clock = new THREE.Mesh(new THREE.PlaneGeometry(0.2, 0.075), clockMat);
  clock.position.set(0.1, 0.07, -0.6); clock.rotation.y = 0.5; scene.add(clock);
  const clockBody = box(0.22, 0.09, 0.07, P.ink('#141018', { flat: 0.8 })); clockBody.position.set(0.1, 0.045, -0.63); clockBody.rotation.y = 0.5; scene.add(clockBody);
  function drawClock(str) {
    const g = clockFace.getContext('2d'); g.fillStyle = '#100808'; g.fillRect(0, 0, 256, 96);
    g.fillStyle = '#FF3B30'; g.font = 'bold 74px monospace'; g.fillText(str, 18, 76);
    clockMat.map.needsUpdate = true;
  }
  drawClock(params.clock || '23:59');

  const camera = new THREE.PerspectiveCamera(params.fov || 42, 16 / 9, 0.02, 100);
  const cam = params.cam || 'ozu';
  function update(t, pulse) {
    const pathed = params.path ? applyPath(camera, params.path, t, false) : false;
    head.rotation.y = Math.sin(t * 0.7) * 0.75;
    blades.rotation.z = t * 40.0;
    const pos = curtain.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = cBase[i * 3], y = cBase[i * 3 + 1];
      const k = (y + 0.65) / 1.3;
      pos.array[i * 3 + 2] = Math.sin(t * 1.3 + x * 4.0) * 0.05 * (1 - k) + Math.sin(t * 0.6) * 0.07 * (1 - k);
    }
    pos.needsUpdate = true;
    if (params.clockFlip && t >= params.clockFlip[0]) drawClock(params.clockFlip[1]);
    if (pathed) {} else if (cam === 'ozu') { camera.position.set(1.45, 0.42, 1.25); camera.lookAt(-0.4, 0.55, -1.0); }
    else if (cam === 'tv') { const k = Math.min(1, t / 6); camera.position.set(-0.6 + 0.3 * (1 - k), 0.75, 0.2 - k * 0.4); camera.lookAt(-0.62, 0.73, -1.35); }
    else if (cam === 'over') { camera.position.set(0.65, 1.9, 0.6); camera.lookAt(0.55, 0.0, -0.1); }
    else if (cam === 'window') { camera.position.set(-1.2, 1.0, 1.2); camera.lookAt(1.8, 1.2, -0.2); }
  }
  const sc = (x, y, z) => new THREE.Vector3(x, y, z);
  const anchors = () => ({ tv: [sc(-0.89, 0.93, -RD / 2 + 0.556), sc(-0.35, 0.93, -RD / 2 + 0.556), sc(-0.35, 0.53, -RD / 2 + 0.556), sc(-0.89, 0.53, -RD / 2 + 0.556)] });
  return { scene: root, camera, update, anchors };
}
