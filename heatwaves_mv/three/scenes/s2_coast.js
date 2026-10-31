// S2: coastal road + seawall + single-track railway, telephone poles, curve mirrors, vending machines,
// houses, sea, lighthouse, moon. Camera: params.cam = 'fly' (default) | 'static' | keyframes.
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'night'];
  const R = P.rng(params.seed || 7);
  const root = new THREE.Scene();
  const scene = new THREE.Group(); scene.scale.x = -1; root.add(scene);   // +x on screen = sea side
  P.U.uFogColor.value.set(Wd.fog);
  P.U.uFogNear.value = params.fogNear || 60;
  P.U.uFogFar.value = params.fogFar || 420;
  P.U.uLightDir.value.set(...Wd.light).normalize();
  P.U.uPeriod.value = params.period || 8;

  const camera = new THREE.PerspectiveCamera(params.fov || 38, 16 / 9, 0.1, 2000);
  scene.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: Wd.stars, band: Wd.skyBand }));
  const moon = P.disc(Wd.moon, Wd.moonShade, 26);
  moon.position.set(260, 150, 720); moon.lookAt(0, 0, 0);
  scene.add(moon);
  const moonGlow = P.glow(Wd.moon, 180, { strength: 0.55 }); moonGlow.position.copy(moon.position).multiplyScalar(0.98);
  scene.add(moonGlow);

  const L = params.length || 900;
  const box = (w, h, d, inkMat) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), inkMat);
  const roadMat = P.ink(Wd.road, { shade: Wd.roadShade, ambient: 0.6 });
  const road = box(7.4, 0.2, L, roadMat); road.position.set(0, -0.1, L / 2 - 20); scene.add(road);
  // centre dashes
  const dashMat = P.ink(Wd.line, { flat: 1.0 });
  for (let z = -20; z < L; z += 9) { const d = box(0.16, 0.02, 4, dashMat); d.position.set(0, 0.01, z); scene.add(d); }
  for (const x of [-3.55, 3.55]) { const e = box(0.12, 0.02, L, dashMat); e.position.set(x, 0.01, L / 2 - 20); scene.add(e); }

  // seawall (right) + walkway + sea
  const wallMat = P.ink(Wd.wall, { shade: Wd.wallShade, ambient: 0.35 });
  const wall = P.outlined(box(1.2, 1.3, L, wallMat), Wd.ink, 0.03); wall.position.set(4.6, 0.45, L / 2 - 20); scene.add(wall);
  const seaMat = new THREE.ShaderMaterial({
    uniforms: { ...P.U, uSea: { value: new THREE.Color(Wd.sea) }, uHi: { value: new THREE.Color(Wd.seaHi) },
                uMoonX: { value: 0.0 } },
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `
      uniform vec3 uSea, uHi; uniform float uTime, uPeriod; uniform vec2 uJitter; varying vec3 vW;
      float h(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
      void main(){
        vec2 f = gl_FragCoord.xy + uJitter;
        float row = floor(f.y / (uPeriod * 0.9));
        float seg = floor((f.x + h(vec2(row, 1.0)) * 300.0 + uTime * 14.0 * (0.5 + h(vec2(row, 2.0)))) / (uPeriod * 3.5));
        float on = step(0.86, h(vec2(row, seg) + floor(uTime * 8.0) * 0.013));
        float lane = exp(-pow((vW.x - 4.0 - (vW.z) * 0.36) / 60.0, 2.0));   // moon path towards the moon
        float m = on * step(fract(f.y / (uPeriod * 0.9)), 0.28) * (0.25 + 0.75 * lane);
        gl_FragColor = vec4(mix(uSea, uHi, step(0.2, m)), 1.0);
      }` });
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), seaMat);
  sea.rotation.x = -Math.PI / 2; sea.position.set(2005, -1.2, 600); scene.add(sea);

  // railway (left)
  const balMat = P.ink(Wd.ballast, { ambient: 0.5 });
  const bal = box(4.2, 0.35, L, balMat); bal.position.set(-9, 0.0, L / 2 - 20); scene.add(bal);
  const railMat = P.ink(Wd.rail, { flat: 0.6 });
  for (const x of [-8.3, -9.7]) { const r = box(0.08, 0.16, L, railMat); r.position.set(x, 0.25, L / 2 - 20); scene.add(r); }
  const sleeperMat = P.ink(Wd.roadShade, { ambient: 0.5 });
  const sleeperGeo = new THREE.BoxGeometry(2.4, 0.08, 0.22);
  const sleepers = new THREE.InstancedMesh(sleeperGeo, sleeperMat, Math.floor(L / 0.7));
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < sleepers.count; i++) { m4.makeTranslation(-9, 0.2, -20 + i * 0.7); sleepers.setMatrixAt(i, m4); }
  scene.add(sleepers);

  // telephone poles + wires + lamps
  const poleMat = P.ink(Wd.pole, { ambient: 0.6 });
  const tops = [];
  for (let z = -10, i = 0; z < L; z += 30, i++) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.16, 9, 8), poleMat);
    pole.position.set(-5.4, 4.5, z); scene.add(pole);
    const arm = box(2.2, 0.12, 0.12, poleMat); arm.position.set(-5.4, 8.4, z); scene.add(arm);
    const arm2 = box(1.6, 0.1, 0.1, poleMat); arm2.position.set(-5.4, 7.7, z); scene.add(arm2);
    if (i % 3 === 1) { const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.8, 10), poleMat); tr.position.set(-5.0, 6.8, z); scene.add(tr); }
    tops.push([new THREE.Vector3(-6.4, 8.45, z), new THREE.Vector3(-4.4, 8.45, z), new THREE.Vector3(-5.9, 7.75, z), new THREE.Vector3(-4.9, 7.75, z)]);
    if (i % 2 === 0) {                                 // street lamp on the pole, over the road
      const la = box(1.6, 0.08, 0.08, poleMat); la.position.set(-4.6, 6.2, z); scene.add(la);
      const head = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.14, 0.24), P.ink(Wd.lamp, { emissive: 1.0 }));
      head.position.set(-3.85, 6.1, z); scene.add(head);
      const g = P.glow(Wd.glow, 3.6, { strength: 0.8 }); g.position.set(-3.85, 5.95, z); scene.add(g);
      const pool = new THREE.Mesh(new THREE.CircleGeometry(3.2, 24), P.ink(Wd.lamp, { flat: 1.0, grain: 0.55, shade: Wd.road }));
      pool.position.set(-2.6, 0.012, z); pool.rotation.x = -Math.PI / 2; scene.add(pool);
    }
  }
  for (let i = 0; i + 1 < tops.length; i++)
    for (let k = 0; k < 4; k++) scene.add(P.line(P.catenary(tops[i][k], tops[i + 1][k], 0.55 + 0.1 * k), Wd.ink));

  // houses beyond the railway
  const houseMat = P.ink(Wd.house, { shade: Wd.houseShade, ambient: 0.3 });
  const roofMat = P.ink(Wd.roof, { ambient: 0.5 });
  const winMat = P.ink(Wd.window, { emissive: 1.0 });
  for (let z = -15; z < L; z += 9 + R() * 7) {
    const w = 6 + R() * 4, d = 6 + R() * 4, h = 3.5 + R() * 3.5, x = -14 - w / 2 - R() * 10;
    const hs = P.outlined(box(w, h, d, houseMat), Wd.ink, 0.03); hs.position.set(x, h / 2, z); scene.add(hs);
    const sh = new THREE.Shape(); sh.moveTo(-w / 2 - 0.4, 0); sh.lineTo(w / 2 + 0.4, 0); sh.lineTo(0, w * 0.32); sh.closePath();
    const rg = new THREE.ExtrudeGeometry(sh, { depth: d + 0.6, bevelEnabled: false }); rg.translate(0, 0, -(d + 0.6) / 2);
    const roof = P.outlined(new THREE.Mesh(rg, roofMat), Wd.ink, 0.03); roof.position.set(x, h, z); scene.add(roof);
    const nw = 2 + Math.floor(R() * 3);
    for (let k = 0; k < nw; k++) {
      if (R() < 0.3) continue;
      const wi = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.8), winMat);
      wi.position.set(x + w / 2 + 0.03, 1.3 + Math.floor(R() * 2) * 1.6, z - d / 2 + (k + 0.5) * d / nw); wi.rotation.y = Math.PI / 2; scene.add(wi);
      if (R() < 0.5) { const g = P.glow(Wd.window, 3.2, { strength: 0.6 }); g.position.copy(wi.position).add(new THREE.Vector3(0.6, 0, 0)); scene.add(g); }
    }
  }

  // curve mirrors + vending machines along the road
  const mpMat = P.ink(Wd.mirrorPole, { ambient: 0.55 });
  const mirMat = P.ink(Wd.mirror, { hi: '#FFFFFF', flat: 0.4, shade: Wd.wallShade });
  const mirrors = [];
  for (const z of (params.mirrors || [70, 250, 430, 610])) {
    const mp = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.9, 8), mpMat), Wd.ink, 0.02);
    mp.position.set(-4.1, 1.45, z); scene.add(mp);
    const disc = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(0.52, 0.52, 0.08, 28), mirMat), Wd.ink, 0.03);
    disc.rotation.set(Math.PI / 2, 0, 0.0); disc.rotation.order = 'YXZ'; disc.rotation.y = -0.7;
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.06, 6, 28), mpMat);
    const grp = new THREE.Group(); grp.add(disc); disc.position.set(0, 0, 0); grp.add(rim);
    grp.position.set(-4.1, 3.0, z); grp.rotation.y = -0.7 + Math.PI; scene.add(grp);
    mirrors.push(grp);
  }
  const vendMat = P.ink(Wd.vend, { emissive: 0.85 });
  for (const z of (params.vending || [40, 205, 380, 555])) {
    const v = P.outlined(box(1.0, 1.85, 0.75, vendMat), Wd.ink, 0.025); v.position.set(-4.7, 0.92, z); scene.add(v);
    const face = new THREE.Mesh(new THREE.PlaneGeometry(0.72, 1.3), P.vendingFront(Wd.vend, Wd.led, Wd.vendGlow, Math.floor(z)));
    face.position.set(-4.19, 1.05, z); face.rotation.y = Math.PI / 2; scene.add(face);
    const led = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.1), P.ink(Wd.led, { emissive: 1.0 }));
    led.position.set(-4.18, 0.95, z); led.rotation.y = Math.PI / 2; scene.add(led);
    const g = P.glow(Wd.vendGlow, 2.2, { strength: 0.55 }); g.position.set(-3.9, 1.0, z); scene.add(g);
  }

  // lighthouse on a cape far ahead, rotating beam
  const lhMat = P.ink(Wd.wall, { shade: Wd.wallShade });
  const lh = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(2.2, 3.2, 26, 16), lhMat), Wd.ink, 0.04);
  lh.position.set(90, 13, L + 80); scene.add(lh);
  const cape = new THREE.Mesh(new THREE.ConeGeometry(60, 18, 9), P.ink(Wd.houseShade, { ambient: 0.5 }));
  cape.position.set(95, -4, L + 90); scene.add(cape);
  const lamp = P.glow(Wd.lamp, 30, { strength: 1.0 }); lamp.position.set(90, 27, L + 80); scene.add(lamp);
  const beamMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { ...P.U, uCol: { value: new THREE.Color(Wd.lamp) } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader: `
      uniform vec3 uCol; uniform float uPeriod, uAngle; uniform vec2 uJitter; varying vec2 vUv;
      float htDot(float tone, vec2 frag, float period, float angle){ float c=cos(angle), s=sin(angle);
        vec2 p = mat2(c,s,-s,c)*frag/period; float d = length(fract(p)-0.5); float r = sqrt(clamp(tone,0.,1.))*0.64;
        return tone<=0.004 ? 0.0 : smoothstep(r+0.75/period, r-0.75/period, d); }
      void main(){ float tone = (1.0 - vUv.y) * 0.55 * (1.0 - abs(vUv.x - 0.5) * 2.0);
        float m = htDot(tone, gl_FragCoord.xy + uJitter, uPeriod * 1.3, uAngle); if (m < 0.02) discard;
        gl_FragColor = vec4(uCol, m); }` });
  const beam = new THREE.Mesh(new THREE.PlaneGeometry(28, 420), beamMat);
  beam.geometry.translate(0, 210, 0);
  const beamPivot = new THREE.Group(); beamPivot.position.set(90, 27, L + 80); beamPivot.add(beam); beam.rotation.x = Math.PI / 2;
  scene.add(beamPivot);

  // camera
  const cam = params.cam || 'fly';
  const speed = params.speed || 11.0;
  const z0 = params.z0 || 0;
  function update(t, pulse) {
    const pathed = params.path ? applyPath(camera, params.path, t, true) : false;
    beamPivot.rotation.y = t * 0.9;
    if (pathed) {} else if (cam === 'fly') {
      const z = z0 + t * speed;
      camera.position.set(-(0.4 + Math.sin(t * 0.35) * 0.6), 1.7 + Math.sin(t * 0.9) * 0.08, z);
      camera.lookAt(-(0.2 + Math.sin(t * 0.3) * 1.5), 1.9, z + 40);
    } else if (cam === 'high') {
      const z = z0 + t * speed;
      camera.position.set(-14, 22, z - 30);
      camera.lookAt(2, 0, z + 30);
    } else if (cam === 'static') {
      const c = params.camPos || [0, 1.7, 0], l = params.lookAt || [0, 1.8, 40];
      camera.position.set(...c); camera.lookAt(...l);
    }
  }
  return { scene: root, camera, update };
}
