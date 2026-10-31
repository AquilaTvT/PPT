// S3: festival street / shotengai (+ S6 underwater when world = 'underwater').
// params: shutterT (all shutters roll up), litT (lanterns ignite, staggered), crowdT (dot crowd appears),
//         heroT [10 times] (hero lanterns light one by one), floatT (underwater: lanterns drift up).
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'festival'];
  const uw = (params.world === 'underwater');
  const R = P.rng(params.seed || 5);
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = uw ? 8 : 40; P.U.uFogFar.value = uw ? 70 : 220;
  P.U.uLightDir.value.set(...Wd.light).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: Wd.stars, band: Wd.skyBand }));
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  const L = params.length || 180, SW = 7.0;
  const road = box(SW + 4, 0.2, L, P.ink(Wd.road, { shade: Wd.roadShade, ambient: 0.6, grain: 0.14 })); road.position.set(0, -0.1, L / 2 - 10); root.add(road);
  const shutterTex = document.createElement('canvas'); shutterTex.width = 64; shutterTex.height = 128;
  { const g = shutterTex.getContext('2d'); g.fillStyle = '#8E95A6'; g.fillRect(0, 0, 64, 128); g.fillStyle = '#4A5878'; for (let y = 0; y < 128; y += 8) g.fillRect(0, y, 64, 2); }
  const shutterMat = P.flatTex(shutterTex);
  const houseM = [P.ink(Wd.house, { shade: Wd.houseShade }), P.ink(Wd.wall, { shade: Wd.wallShade })];
  const shopM = P.ink(Wd.window, { emissive: 1.0 });
  const shutters = [];
  for (const side of [-1, 1]) {
    for (let z = -8; z < L; z += 6.5) {
      const h = 6 + R() * 3;
      const hs = P.outlined(box(5, h, 6.2, houseM[Math.floor(R() * 2)]), Wd.ink, 0.03); hs.position.set(side * (SW / 2 + 2.6), h / 2, z); root.add(hs);
      const eave = box(1.6, 0.18, 6.4, P.ink(Wd.roof, { ambient: 0.5 })); eave.position.set(side * (SW / 2 + 0.3), 3.3, z); eave.rotation.z = side * 0.25; root.add(eave);
      const shop = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 2.6), shopM); shop.position.set(side * (SW / 2 + 0.08), 1.3, z); shop.rotation.y = -side * Math.PI / 2; root.add(shop);
      const sh = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 2.6), shutterMat); sh.position.set(side * (SW / 2 + 0.1), 1.3, z); sh.rotation.y = -side * Math.PI / 2; root.add(sh);
      shutters.push(sh);
      if (R() < 0.45 && !uw) { const banner = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 2.6), P.ink(['#D9402B', '#F5C842', '#2C4C9A', '#EDE3CF'][Math.floor(R() * 4)], { flat: 0.8, side: THREE.DoubleSide }));
        banner.position.set(side * (SW / 2 - 0.4), 2.2, z + 2); banner.rotation.y = Math.PI / 2; root.add(banner); }
    }
  }
  // surrounding town (seen from the crane / aerial shots): blocks with tiled roofs and a few lit windows
  if (params.surround) {
    const bM = [P.ink(Wd.house, { shade: Wd.houseShade }), P.ink(Wd.wall, { shade: Wd.wallShade })];
    const rM = P.ink(Wd.roof, { ambient: 0.5 }), wM = P.ink(Wd.window, { emissive: 1.0 });
    for (const side of [-1, 1]) for (let x = SW / 2 + 9; x < 70; x += 9) for (let z = -20; z < L + 20; z += 9) {
      if (R() < 0.15) continue;
      const w = 6 + R() * 2, d = 6 + R() * 2, h = 4 + R() * 4;
      const b = box(w, h, d, bM[Math.floor(R() * 2)]); b.position.set(side * (x + R() * 2), h / 2, z + R() * 2); root.add(b);
      const sh = new THREE.Shape(); sh.moveTo(-w / 2 - 0.3, 0); sh.lineTo(w / 2 + 0.3, 0); sh.lineTo(0, w * 0.3); sh.closePath();
      const rg = new THREE.ExtrudeGeometry(sh, { depth: d + 0.4, bevelEnabled: false }); rg.translate(0, 0, -(d + 0.4) / 2);
      const rf = new THREE.Mesh(rg, rM); rf.position.set(b.position.x, h, b.position.z); rf.rotation.y = R() < 0.5 ? 0 : Math.PI / 2; root.add(rf);
      if (R() < 0.35) { const wi = box(1.0, 0.8, 0.05, wM); wi.position.set(b.position.x, h * 0.6, b.position.z + d / 2 + 0.03); root.add(wi); }
    }
  }
  // yatai stalls on the street edges
  const awnTex = document.createElement('canvas'); awnTex.width = 64; awnTex.height = 16;
  { const g = awnTex.getContext('2d'); for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? '#EDE3CF' : '#D9402B'; g.fillRect(i * 8, 0, 8, 16); } }
  const awnMat = P.flatTex(awnTex);
  for (const [side, z] of [[-1, 18], [1, 30], [-1, 46], [1, 62], [-1, 80], [1, 96]]) {
    const counter = P.outlined(box(1.4, 1.0, 3.2, P.ink('#5A3E36', { shade: '#2A1C1A' })), Wd.ink, 0.02); counter.position.set(side * (SW / 2 - 1.0), 0.5, z); root.add(counter);
    const awn = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 3.4), awnMat); awn.position.set(side * (SW / 2 - 1.0), 2.3, z); awn.rotation.set(-Math.PI / 2, 0, 0); awn.rotation.y = side * 0.3; root.add(awn);
    if (!uw) { const g = P.glow('#F5C842', 3.0, { strength: 0.55 }); g.position.set(side * (SW / 2 - 1.8), 1.6, z); root.add(g); }
  }
  // lantern wires across the street every 8 m; 7 lanterns each
  const lanternGeo = new THREE.SphereGeometry(0.32, 12, 10); lanternGeo.scale(1, 1.25, 1);
  const lanterns = [];
  const WS = params.wireSpacing || 8, WZ0 = params.wireZ0 ?? 4;
  for (let z = WZ0, row = 0; z < L; z += WS, row++) {
    const a = new THREE.Vector3(-SW / 2 - 0.2, 5.6, z), b = new THREE.Vector3(SW / 2 + 0.2, 5.6, z);
    const pts = P.catenary(a, b, 0.7, 14); root.add(P.line(pts, Wd.ink));
    for (let k = 1; k <= 7; k++) {
      const p = pts[k * 2 - 1 + (k > 6 ? 0 : 0)] || pts[pts.length - 2];
      const onM = P.ink(Wd.lantern || '#E8452E', { emissive: 1.0 }), offM = P.ink(Wd.lanternOff || '#8E6A65', { ambient: 0.55 });
      const m = new THREE.Mesh(lanternGeo, offM); m.position.copy(p).add(new THREE.Vector3(0, -0.45, 0)); root.add(m);
      const gl = P.glow(Wd.lantern || '#E8452E', 1.8, { strength: 0.7 }); gl.position.copy(m.position); gl.visible = false; root.add(gl);
      lanterns.push({ m, onM, offM, gl, row, k, base: m.position.clone(), ph: R() * 6.28 });
    }
  }
  // dot crowd (instanced): bodies + heads, two directions
  const N = uw ? 0 : (params.crowd || 600);
  const bodyGeo = new THREE.CylinderGeometry(0.2, 0.26, 1.1, 8), headGeo = new THREE.SphereGeometry(0.17, 10, 8);
  const inks = ['#2C4C9A', '#D9402B', '#EDE3CF', '#F5C842', '#7FC8B8', '#141018'];
  const crowd = [];
  for (let c = 0; c < inks.length; c++) {
    const bm = new THREE.InstancedMesh(bodyGeo, P.ink(inks[c], { ambient: 0.5 }), Math.ceil(N / inks.length));
    const hm = new THREE.InstancedMesh(headGeo, P.ink('#141018', { ambient: 0.5 }), Math.ceil(N / inks.length));
    bm.count = 0; hm.count = 0; bm.frustumCulled = false; hm.frustumCulled = false; root.add(bm); root.add(hm); crowd.push({ bm, hm, list: [] });
  }
  const lane = params.crowdLane || 0;
  for (let i = 0; i < N; i++) {
    let x = (R() - 0.5) * (SW - 0.8);
    if (lane && Math.abs(x) < lane) x = Math.sign(x || 1) * (lane + R() * 0.6);
    crowd[i % inks.length].list.push({ x, z: R() * L, dir: R() < 0.5 ? 1 : -1, v: 0.6 + R() * 0.6, ph: R() * 6 });
  }
  const camera = new THREE.PerspectiveCamera(params.fov || 42, 16 / 9, 0.05, 2000);
  const m4 = new THREE.Matrix4();
  const heroIdx = [3, 10, 17, 24, 31, 38, 45, 52, 59, 66];          // middle lanterns of rows 0..9
  function update(t, pulse) {
    const sk = params.shutterT == null ? 1 : Math.min(1, Math.max(0, (t - params.shutterT) / 0.3));
    shutters.forEach(s => { s.scale.y = Math.max(0.001, 1 - sk); s.position.y = 1.3 + 1.3 * sk; });
    lanterns.forEach((L, i) => {
      let on = params.litT != null && t >= params.litT + (L.row * 0.02);
      const h = heroIdx.indexOf(i);
      if (h >= 0 && params.heroT) on = t >= params.heroT[h];
      if (uw) on = false;
      L.m.material = on ? L.onM : L.offM; L.gl.visible = on;
      const sway = Math.sin(t * 1.6 + L.ph) * 0.06;
      L.m.position.set(L.base.x + sway, L.base.y + (uw && params.floatT != null ? Math.max(0, t - params.floatT) * (0.4 + (i % 5) * 0.12) : 0), L.base.z);
      L.gl.position.copy(L.m.position);
    });
    const ck = params.crowdT == null ? 1 : (t >= params.crowdT ? 1 : 0);
    for (const c of crowd) {
      let n = 0;
      if (ck) for (const a of c.list) {
        const z = ((a.z + a.dir * a.v * t) % L + L) % L, bob = Math.abs(Math.sin(t * 6 + a.ph)) * 0.05;
        m4.makeTranslation(a.x, 0.55 + bob, z); c.bm.setMatrixAt(n, m4);
        m4.makeTranslation(a.x, 1.28 + bob, z); c.hm.setMatrixAt(n, m4); n++;
      }
      c.bm.count = n; c.hm.count = n; c.bm.instanceMatrix.needsUpdate = true; c.hm.instanceMatrix.needsUpdate = true;
    }
    if (!(params.path && applyPath(camera, params.path, t))) { camera.position.set(0.5, 1.7, -6); camera.lookAt(0, 3.2, 30); }
  }
  const anchors = () => ({ hero: heroIdx.map(i => lanterns[i] ? lanterns[i].m.position.clone() : new THREE.Vector3()),
                           heroTop: heroIdx.map(i => lanterns[i] ? lanterns[i].m.position.clone().add(new THREE.Vector3(0, 0.4, 0)) : new THREE.Vector3()) });
  return { scene: root, camera, update, anchors };
}
