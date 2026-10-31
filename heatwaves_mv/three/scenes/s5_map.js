// S5: the town as a printed map (oblique/top-down): blocks, streets, coast, single-track coastal railway with
// stations, lighthouse cape, stamp-rally route (lights up along params.routeK), sea. Labels/glyphs are 2D (anchors).
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'night'];
  const R = P.rng(params.seed || 3);
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = 900; P.U.uFogFar.value = 2600;
  P.U.uLightDir.value.set(0.35, 0.85, 0.4).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: Wd.stars, band: Wd.skyBand }));
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  // paper ground + sea: coastline is a wobbly curve x = coast(z)
  const coast = (z) => 120 + 40 * Math.sin(z / 140) + 18 * Math.sin(z / 47 + 1);
  const land = P.ink('#EDE3CF', { flat: 1, grain: 0.06 });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600), land); ground.rotation.x = -Math.PI / 2; root.add(ground);
  const seaShape = new THREE.Shape(); seaShape.moveTo(coast(-800), -800);
  for (let z = -800; z <= 800; z += 20) seaShape.lineTo(coast(z), z);
  seaShape.lineTo(1400, 800); seaShape.lineTo(1400, -800); seaShape.closePath();
  const seaMat = P.ink(Wd.sea, { flat: 1, grain: 0.22, shade: Wd.skyTop });
  const sea = new THREE.Mesh(new THREE.ShapeGeometry(seaShape), seaMat); sea.rotation.x = Math.PI / 2; sea.position.y = 0.2; root.add(sea);
  // coastline ink + railway (dashed) parallel to the coast
  const coastPts = [], railPts = [];
  for (let z = -800; z <= 800; z += 10) { coastPts.push(new THREE.Vector3(coast(z), 0.6, z)); railPts.push(new THREE.Vector3(coast(z) - 16, 0.7, z)); }
  root.add(P.line(coastPts, Wd.ink));
  const railCurve = new THREE.CatmullRomCurve3(railPts);
  const rail = new THREE.Mesh(new THREE.TubeGeometry(railCurve, 400, 1.6, 6, false), P.ink('#141018', { flat: 1 })); root.add(rail);
  const sleeperM = P.ink('#EDE3CF', { flat: 1 });
  for (let i = 0; i < 160; i++) { const p = railCurve.getPointAt(i / 160); const s = box(4.2, 0.4, 1.0, sleeperM); s.position.copy(p).add(new THREE.Vector3(0, 0.4, 0)); root.add(s); }
  // street grid + blocks (only on land)
  const roadM = P.ink('#C9B98F', { flat: 1 });
  const blockM = [P.ink(Wd.house, { shade: Wd.houseShade, ambient: 0.4 }), P.ink(Wd.wall, { shade: Wd.wallShade, ambient: 0.4 }),
                  P.ink(Wd.roof, { ambient: 0.5 })];
  const winM = P.ink(Wd.window, { emissive: 1 });
  const lit = [];
  for (let x = -600; x < 100; x += 36) for (let z = -700; z < 700; z += 36) {
    if (x + 30 > coast(z) - 24) continue;
    if (R() < 0.12) continue;          // parks / empty lots
    const n = 1 + Math.floor(R() * 3);
    for (let k = 0; k < n; k++) {
      const w = 8 + R() * 10, d = 8 + R() * 10, h = 3 + R() * (x > -200 ? 10 : 6);
      const b = P.outlined(box(w, h, d, blockM[Math.floor(R() * 3)]), Wd.ink, 0.25);
      b.position.set(x + 6 + R() * 16, h / 2, z + 6 + R() * 16); root.add(b);
      if (R() < 0.5) { const wdw = box(w * 0.5, 0.3, d * 0.5, winM); wdw.position.set(b.position.x, h + 0.2, b.position.z); root.add(wdw); lit.push(wdw); }
    }
  }
  for (let x = -606; x < 110; x += 36) { const r = box(4, 0.15, 1400, roadM); r.position.set(x, 0.08, 0); root.add(r); }
  for (let z = -706; z < 710; z += 36) { const r = box(700, 0.15, 4, roadM); r.position.set(-250, 0.08, z); root.add(r); }
  // stations (5 stamps) + lighthouse cape at the far end
  const stamps = params.stamps || [[-520, 0.08], [-260, 0.32], [-20, 0.5], [240, 0.7], [470, 0.86]];
  const stM = P.ink('#D9402B', { flat: 1 });
  const stationPos = stamps.map(([z, u]) => { const p = railCurve.getPointAt(u); const s = P.outlined(box(10, 4, 18, stM), Wd.ink, 0.3); s.position.copy(p).add(new THREE.Vector3(-10, 2, 0)); root.add(s); return s.position.clone(); });
  const capeZ = 640, capeX = coast(capeZ) + 30;
  const cape = new THREE.Mesh(new THREE.CylinderGeometry(40, 55, 6, 18), P.ink('#8E95A6', { shade: '#3A3F55' })); cape.position.set(capeX, 3, capeZ); root.add(cape);
  const lh = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(3, 4.5, 28, 16), P.ink('#EDE3CF', { shade: '#8E95A6' })), Wd.ink, 0.3);
  lh.position.set(capeX, 20, capeZ); root.add(lh);
  const lamp = P.glow(Wd.lamp, 60, { strength: 0.9 }); lamp.position.set(capeX, 36, capeZ); root.add(lamp);
  // stamp-rally route: from station 0 along the rail to the lighthouse; lights up to params.routeK(t)
  const routePts = [];
  for (let i = 0; i <= 200; i++) routePts.push(railCurve.getPointAt(0.05 + i / 200 * 0.85).add(new THREE.Vector3(-6, 1.2, 0)));
  routePts.push(new THREE.Vector3(capeX, 1.2, capeZ));
  const routeCurve = new THREE.CatmullRomCurve3(routePts);
  const routeGeo = new THREE.TubeGeometry(routeCurve, 600, 2.2, 6, false);
  const routeMat = new THREE.ShaderMaterial({ uniforms: { ...P.U, uK: { value: 0 }, uC: { value: new THREE.Color(params.routeColor || '#F08A3C') }, uOff: { value: new THREE.Color(Wd.houseShade) } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform float uK, uPulse; uniform vec3 uC, uOff; varying vec2 vUv;
      void main(){ float on = step(vUv.x, uK); float dash = step(0.5, fract(vUv.x * 160.0));
        if (on < 0.5 && dash < 0.5) discard; gl_FragColor = vec4(mix(uOff, uC * (1.0 + 0.3 * uPulse), on), 1.0); }` });
  root.add(new THREE.Mesh(routeGeo, routeMat));
  const head = P.glow('#FFF6DC', 40, { strength: 1.0 }); root.add(head);
  const camera = new THREE.PerspectiveCamera(params.fov || 35, 16 / 9, 1, 5000);
  const rk = params.route || [[0, 0], [1, 0]];
  const routeK = (t) => { for (let i = 0; i + 1 < rk.length; i++) if (t <= rk[i + 1][0]) { const [t0, k0] = rk[i], [t1, k1] = rk[i + 1]; return k0 + (k1 - k0) * Math.min(1, Math.max(0, (t - t0) / (t1 - t0))); } return rk[rk.length - 1][1]; };
  const dark = params.windowsOff || null;   // [t0, t1]: windows go dark progressively (dawn)
  function update(t) {
    const k = routeK(t); routeMat.uniforms.uK.value = k;
    head.position.copy(routeCurve.getPointAt(Math.min(0.999, Math.max(0.001, k)))).add(new THREE.Vector3(0, 6, 0));
    head.visible = !!params.headDot;
    if (dark) { const f = Math.min(1, Math.max(0, (t - dark[0]) / (dark[1] - dark[0]))); lit.forEach((w, i) => { w.visible = (i / lit.length) >= f; }); }
    if (!(params.path && applyPath(camera, params.path, t))) { camera.position.set(-420, 260, -420); camera.lookAt(-60, 0, 120); }
  }
  const anchors = () => ({ stations: stationPos, lighthouse: [new THREE.Vector3(capeX, 36, capeZ)], head: [head.position.clone()] });
  return { scene: root, camera, update, anchors };
}
