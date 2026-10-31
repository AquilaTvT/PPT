// S5: the town as a printed map (oblique/top-down): blocks, streets, coast, single-track coastal railway with
// stations, lighthouse cape, stamp-rally route (lights up along params.routeK), sea. Labels/glyphs are 2D (anchors).
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'night'];
  const R = P.rng(params.seed || 3);
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(params.fogColor || Wd.fog); P.U.uFogNear.value = params.fogNear ?? 900; P.U.uFogFar.value = params.fogFar ?? 2600;
  P.U.uLightDir.value.set(0.35, 0.85, 0.4).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: Wd.stars, band: Wd.skyBand }));
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  // paper ground + sea: coastline is a wobbly curve x = coast(z)
  const coast = (z) => 120 + 40 * Math.sin(z / 140) + 18 * Math.sin(z / 47 + 1);
  const land = P.ink(params.land || '#EDE3CF', { flat: 1, grain: 0.06 });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600), land); ground.rotation.x = -Math.PI / 2; root.add(ground);
  const seaShape = new THREE.Shape(); seaShape.moveTo(coast(-800), -800);
  for (let z = -800; z <= 800; z += 20) seaShape.lineTo(coast(z), z);
  seaShape.lineTo(1400, 800); seaShape.lineTo(1400, -800); seaShape.closePath();
  const seaMat = P.ink(params.sea || Wd.sea, { flat: 1, grain: params.seaGrain ?? 0.22, shade: params.seaShade || Wd.skyTop, side: THREE.DoubleSide });
  const sea = new THREE.Mesh(new THREE.ShapeGeometry(seaShape), seaMat); sea.rotation.x = Math.PI / 2; sea.position.y = 0.2; root.add(sea);
  // halftone light on the ground plane (lighthouse beam / moon path): dots of uCol, density falls off along/across
  const dotsMat = (col, str, wave = 0) => new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { ...P.U, uCol: { value: new THREE.Color(col) }, uStr: { value: str }, uWave: { value: wave } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 uCol; uniform float uStr, uPeriod, uAngle, uWave, uTime; uniform vec2 uJitter; varying vec2 vUv;
      void main(){
        float across = abs(vUv.y - 0.5) * 2.0;
        float tone = uStr * pow(1.0 - vUv.x, 0.8) * smoothstep(1.0, 0.15, across);
        if (uWave > 0.0) {   // glitter on the swell: broken streaks that drift
          float w = sin(vUv.x * 520.0 - uTime * 3.0 + 1.2 * sin(vUv.y * 4.0 + vUv.x * 40.0));
          float br = sin(vUv.y * 23.0 + vUv.x * 170.0 + uTime * 0.7);
          tone *= mix(1.0, smoothstep(-0.1, 0.8, w) * smoothstep(-0.4, 0.5, br), uWave);
        }
        vec2 f = gl_FragCoord.xy + uJitter; float c = cos(uAngle), s = sin(uAngle);
        vec2 r = mat2(c, -s, s, c) * f / uPeriod; vec2 q = fract(r) - 0.5;
        if (length(q) > sqrt(max(tone, 0.0)) * 0.62) discard;
        gl_FragColor = vec4(uCol, 1.0);
      }` });
  const wedge = (len, w0, w1) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, -w0 / 2, 0, 0, w0 / 2, len, 0, w1 / 2, len, 0, -w1 / 2], 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 0, 1, 1, 1, 1, 0], 2));
    g.setIndex([0, 1, 2, 0, 2, 3]); return g;
  };
  if (params.moonPath) {
    const m = params.moonPath;   // {z, len, w, color, str}
    const strip = new THREE.Mesh(wedge(m.len || 700, m.w || 50, (m.w || 50) * 1.8), dotsMat(m.color || '#C9D3DC', m.str ?? 0.8, 1.0));
    strip.position.set(coast(m.z || 0) + 6, 0.9, m.z || 0); root.add(strip);
  }
  // coastline ink + railway (dashed) parallel to the coast
  const coastPts = [], railPts = [];
  for (let z = -800; z <= 800; z += 10) { coastPts.push(new THREE.Vector3(coast(z), 0.6, z)); railPts.push(new THREE.Vector3(coast(z) - 16, 0.7, z)); }
  root.add(P.line(coastPts, Wd.ink));
  const railCurve = new THREE.CatmullRomCurve3(railPts);
  const rail = new THREE.Mesh(new THREE.TubeGeometry(railCurve, 400, 1.6, 6, false), P.ink('#141018', { flat: 1 })); root.add(rail);
  const sleeperM = P.ink('#EDE3CF', { flat: 1 });
  for (let i = 0; i < 160; i++) { const p = railCurve.getPointAt(i / 160); const s = box(4.2, 0.4, 1.0, sleeperM); s.position.copy(p).add(new THREE.Vector3(0, 0.4, 0)); root.add(s); }
  // street grid + blocks (only on land)
  const roadM = P.ink(params.road || '#C9B98F', { flat: 1 });
  const bc = params.blocks || [Wd.house, Wd.wall, Wd.roof];
  const blockM = [P.ink(bc[0], { shade: params.blockShade || Wd.houseShade, ambient: 0.4 }), P.ink(bc[1], { shade: params.blockShade || Wd.wallShade, ambient: 0.4 }),
                  P.ink(bc[2], { ambient: 0.5 })];
  const winM = P.ink(params.window || Wd.window, { emissive: 1 });
  const litP = params.litP ?? 0.5;
  const lit = [];
  for (let x = -600; x < 100; x += 36) for (let z = -700; z < 700; z += 36) {
    if (x + 30 > coast(z) - 24) continue;
    if (R() < 0.12) continue;          // parks / empty lots
    const n = 1 + Math.floor(R() * 3);
    for (let k = 0; k < n; k++) {
      const w = 8 + R() * 10, d = 8 + R() * 10, h = 3 + R() * (x > -200 ? 10 : 6);
      const b = P.outlined(box(w, h, d, blockM[Math.floor(R() * 3)]), Wd.ink, 0.25);
      b.position.set(x + 6 + R() * 16, h / 2, z + 6 + R() * 16); root.add(b);
      const isLit = R() < litP, rank = R();         // always draw both numbers so towns match across palettes
      if (isLit) { const wdw = box(w * 0.5, 0.3, d * 0.5, winM); wdw.position.set(b.position.x, h + 0.2, b.position.z); wdw.userData.rank = rank; root.add(wdw); lit.push(wdw); }
    }
  }
  const XS = [], ZS = [];
  for (let x = -606; x < 110; x += 36) XS.push(x);
  for (let z = -706; z < 710; z += 36) ZS.push(z);
  let segs = null, segMesh = null;
  const walker = params.walker || null;    // {pts:[[x,z]...], times:[...]}: a dot walking the streets (anchor 'walker')
  if (params.reroute) {
    // streets as per-block segments so junctions can disconnect / reconnect on beats (instanced)
    segs = [];
    const onWalk = (mx, mz) => walker && walker.pts.some((p, i) => i > 0 && Math.abs((p[0] + walker.pts[i - 1][0]) / 2 - mx) < 1 && Math.abs((p[1] + walker.pts[i - 1][1]) / 2 - mz) < 1);
    XS.forEach(x => ZS.slice(0, -1).forEach(z => { if (x < coast(z + 18) - 12) segs.push({ x, z: z + 18, w: 4, d: 40, keep: onWalk(x, z + 18) }); }));
    ZS.forEach(z => XS.slice(0, -1).forEach(x => { if (x + 36 < coast(z) - 12) segs.push({ x: x + 18, z, w: 40, d: 4, keep: onWalk(x + 18, z) }); }));
    segMesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 0.15, 1), roadM, segs.length); segMesh.frustumCulled = false; root.add(segMesh);
  } else {
    for (const x of XS) { const r = box(4, 0.15, 1400, roadM); r.position.set(x, 0.08, 0); root.add(r); }
    for (const z of ZS) { const r = box(700, 0.15, 4, roadM); r.position.set(-250, 0.08, z); root.add(r); }
  }
  if (params.vend) {      // vending machines: tiny mint lights at street corners
    const vm = P.ink(params.vendColor || '#7FC8B8', { emissive: 1 });
    for (let i = 0; i < params.vend; i++) {
      const x = XS[Math.floor(R() * XS.length)] + 4, z = ZS[Math.floor(R() * ZS.length)] + 4;
      if (x > coast(z) - 20) continue;
      const v = box(3, 3, 3, vm); v.position.set(x, 1.5, z); root.add(v);
    }
  }
  // stations (5 stamps) + lighthouse cape at the far end
  const stamps = params.stamps || [[-520, 0.08], [-260, 0.32], [-20, 0.5], [240, 0.7], [470, 0.86]];
  const stM = P.ink('#D9402B', { flat: 1 });
  const stationPos = stamps.map(([z, u]) => { const p = railCurve.getPointAt(u); const s = P.outlined(box(10, 4, 18, stM), Wd.ink, 0.3); s.position.copy(p).add(new THREE.Vector3(-10, 2, 0)); root.add(s); return s.position.clone(); });
  const capeZ = 640, capeX = coast(capeZ) + 30;
  // headland: an irregular piece of land poking into the sea, inked outline
  const capeShape = new THREE.Shape(), capeLine = [];
  for (let i = 0; i <= 48; i++) {
    const a = i / 48 * Math.PI * 2, r = 50 + 9 * Math.sin(3 * a + 1) + 5 * Math.sin(7 * a + 2);
    const px = capeX + 8 + r * Math.cos(a) * 1.2, pz = capeZ + r * Math.sin(a);
    if (i === 0) capeShape.moveTo(px, pz); else capeShape.lineTo(px, pz);
    capeLine.push(new THREE.Vector3(px, 0.7, pz));
  }
  const cape = new THREE.Mesh(new THREE.ShapeGeometry(capeShape), P.ink(params.land || '#EDE3CF', { flat: 1, grain: 0.06, side: THREE.DoubleSide }));
  cape.rotation.x = Math.PI / 2; cape.position.y = 0.4; root.add(cape); root.add(P.line(capeLine, Wd.ink));
  const lhW = P.ink('#F6F2E7', { shade: '#8E95A6' }), lhR = P.ink('#D9402B', { shade: '#7A2A22' });
  const lh = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(4.5, 7, 40, 18), lhW), Wd.ink, 0.35); lh.position.set(capeX, 20, capeZ); root.add(lh);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(5.7, 6.0, 6, 18), lhR); band.position.set(capeX, 22, capeZ); root.add(band);
  const cap = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(6.5, 6.5, 5, 18), P.ink(Wd.ink || '#1A1416', { flat: 1 })), Wd.ink, 0.3);
  cap.position.set(capeX, 44, capeZ); root.add(cap);
  const lamp = P.glow(params.lampColor || Wd.lamp, params.lampSize || 70, { strength: 0.9 }); lamp.position.set(capeX, 46, capeZ); root.add(lamp);
  let beam = null;
  if (params.beam) {   // two opposite halftone wedges sweeping over sea and town
    const bm = params.beam; beam = new THREE.Group(); beam.position.set(capeX, 1.0, capeZ);
    for (const sgn of [1, -1]) { const w = new THREE.Mesh(wedge(bm.len || 700, 6, bm.width || 150), dotsMat(bm.color || Wd.lamp, bm.str ?? 0.75)); w.rotation.y = sgn > 0 ? 0 : Math.PI; beam.add(w); }
    root.add(beam);
  }
  // stamp-rally route: from station 0 along the rail to the lighthouse; lights up to params.routeK(t)
  const routePts = [];
  for (let i = 0; i <= 200; i++) routePts.push(railCurve.getPointAt(0.05 + i / 200 * 0.85).add(new THREE.Vector3(-6, 1.2, 0)));
  if (params.rings) {     // the six stamp circles (5 stations + lighthouse) printed on the map
    const rm = P.ink(params.ringColor || params.routeColor || '#F08A3C', { flat: 1, side: THREE.DoubleSide });
    for (const p of [...stationPos, new THREE.Vector3(capeX, 0, capeZ)]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(15, 18.5, 40), rm); ring.rotation.x = -Math.PI / 2; ring.position.set(p.x, 1.6, p.z); root.add(ring);
    }
  }
  routePts.push(new THREE.Vector3(capeX, 1.2, capeZ));
  const routeCurve = new THREE.CatmullRomCurve3(routePts);
  const routeGeo = new THREE.TubeGeometry(routeCurve, 600, 2.2, 6, false);
  const routeMat = new THREE.ShaderMaterial({ uniforms: { ...P.U, uK: { value: 0 }, uC: { value: new THREE.Color(params.routeColor || '#F08A3C') }, uOff: { value: new THREE.Color(params.routeOff || Wd.houseShade) } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform float uK, uPulse; uniform vec3 uC, uOff; varying vec2 vUv;
      void main(){ float on = step(vUv.x, uK); float dash = step(0.5, fract(vUv.x * 160.0));
        if (on < 0.5 && dash < 0.5) discard; gl_FragColor = vec4(mix(uOff, uC * (1.0 + 0.3 * uPulse), on), 1.0); }` });
  root.add(new THREE.Mesh(routeGeo, routeMat));
  const head = P.glow(params.headColor || '#FFF6DC', params.headSize || 40, { strength: 1.0 }); root.add(head);
  const camera = new THREE.PerspectiveCamera(params.fov || 35, 16 / 9, 1, 5000);
  const rk = params.route || [[0, 0], [1, 0]];
  const routeK = (t) => { for (let i = 0; i + 1 < rk.length; i++) if (t <= rk[i + 1][0]) { const [t0, k0] = rk[i], [t1, k1] = rk[i + 1]; return k0 + (k1 - k0) * Math.min(1, Math.max(0, (t - t0) / (t1 - t0))); } return rk[rk.length - 1][1]; };
  const dark = params.windowsOff || null;   // [t0, t1]: windows go dark progressively (dawn)
  const darkSteps = params.windowsOffSteps || null;   // [t...]: a group goes dark at each time
  const walkAt = (t) => {
    const P_ = walker.pts, T = walker.times;
    if (t <= T[0]) return P_[0];
    for (let i = 0; i + 1 < T.length; i++) if (t <= T[i + 1]) { const u = (t - T[i]) / Math.max(1e-6, T[i + 1] - T[i]); return [P_[i][0] + (P_[i + 1][0] - P_[i][0]) * u, P_[i][1] + (P_[i + 1][1] - P_[i][1]) * u]; }
    return P_[P_.length - 1];
  };
  const hash = (a) => { const x = Math.sin(a * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
  const mtx = new THREE.Matrix4(), q0 = new THREE.Quaternion(), v0 = new THREE.Vector3(), s0 = new THREE.Vector3();
  const labelPts = (params.labelT || []).map(tt => routeCurve.getPointAt(Math.min(0.999, Math.max(0.001, routeK(tt)))).clone().add(new THREE.Vector3(0, 2, 0)));
  function update(t) {
    const k = routeK(t); routeMat.uniforms.uK.value = k;
    head.position.copy(routeCurve.getPointAt(Math.min(0.999, Math.max(0.001, k)))).add(new THREE.Vector3(0, 6, 0));
    head.visible = !!params.headDot;
    if (dark) { const f = Math.min(1, Math.max(0, (t - dark[0]) / (dark[1] - dark[0]))); lit.forEach((w, i) => { w.visible = (i / lit.length) >= f; }); }
    if (darkSteps) { const f = darkSteps.filter(x => t >= x).length / (darkSteps.length + 1); lit.forEach(w => { w.visible = w.userData.rank >= f; }); }
    if (segs) {
      const rr = params.reroute, nb = rr.beats.filter(x => t >= x).length;
      segs.forEach((g, i) => {
        const off = !g.keep && nb > 0 && hash(i * 7.31 + nb * 101.7 + (rr.seed || 0)) < (rr.frac || 0.16);
        v0.set(g.x, 0.08, g.z); s0.set(off ? 1e-4 : g.w, 1, off ? 1e-4 : g.d); mtx.compose(v0, q0, s0); segMesh.setMatrixAt(i, mtx);
      });
      segMesh.instanceMatrix.needsUpdate = true;
    }
    if (beam) beam.rotation.y = (params.beam.phase || 0) * Math.PI / 180 + t * (params.beam.speed ?? 30) * Math.PI / 180;
    if (!(params.path && applyPath(camera, params.path, t))) { camera.position.set(-420, 260, -420); camera.lookAt(-60, 0, 120); }
  }
  let lastT = 0;
  const _upd = update;
  function update2(t) { lastT = t; _upd(t); }
  const anchors = () => {
    const a = { stations: stationPos, lighthouse: [new THREE.Vector3(capeX, 46, capeZ)], cape: [new THREE.Vector3(capeX, 0, capeZ)], head: [head.position.clone()] };
    if (walker) { const w = walkAt(lastT); a.walker = [new THREE.Vector3(w[0], 0.5, w[1])]; }
    if (params.marks) { a.marks = params.marks.map(m => new THREE.Vector3(m[0], m[2] ?? 0.5, m[1])); a.marksN = params.marks.map(m => new THREE.Vector3(m[0], m[2] ?? 0.5, m[1] + 12)); }
    if (labelPts.length) a.labels = labelPts;
    return a;
  };
  return { scene: root, camera, update: update2, anchors };
}
