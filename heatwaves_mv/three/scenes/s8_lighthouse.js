// S8: the white lighthouse on its cape at sunrise (MV-B outro). Tower with halftone shading, red cap, lamp room,
// red wooden stamp box by the door, rotating halftone beam that fades, wrap-around word bands (one segment per
// word, each facing the camera at its sung time), a paper-cut sun as a camera-facing disc, sea with a sun path.
// params: world, path, sun: {pos:[x,y,z], r}, beamFade: [t0, t1], words: [{text, theta, y, t}], doorTheta
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'dawnprint'];
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = 120; P.U.uFogFar.value = 1400;
  P.U.uLightDir.value.set(...Wd.light).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: 0, band: Wd.skyBand }));
  // sea + sun path glints
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(1800, 1800), P.ink(Wd.sea, { flat: 1, grain: 0.12 }));
  sea.rotation.x = -Math.PI / 2; sea.position.y = -1.5; root.add(sea);
  const sunP = new THREE.Vector3(...(params.sun ? params.sun.pos : [300, 60, -500]));
  const glintMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { ...P.U, uCol: { value: new THREE.Color(Wd.seaHi) } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 uCol; uniform float uPeriod, uAngle, uTime; uniform vec2 uJitter; varying vec2 vUv;
      void main(){ float across = abs(vUv.x - 0.5) * 2.0;
        float w = sin(vUv.y * 900.0 - uTime * 3.0 + 1.3 * sin(vUv.x * 5.0 + vUv.y * 60.0));
        float tone = 0.85 * smoothstep(1.0, 0.1, across) * smoothstep(-0.1, 0.8, w) * (0.35 + 0.65 * vUv.y);
        vec2 f = gl_FragCoord.xy + uJitter; float c = cos(uAngle), s = sin(uAngle);
        vec2 q = fract(mat2(c, -s, s, c) * f / uPeriod) - 0.5;
        if (length(q) > sqrt(max(tone, 0.0)) * 0.62) discard; gl_FragColor = vec4(uCol, 1.0); }` });
  const sd = new THREE.Vector3(sunP.x, 0, sunP.z).normalize();
  const glint = new THREE.Mesh(new THREE.PlaneGeometry(60, 900), glintMat);
  glint.rotation.x = -Math.PI / 2; glint.rotation.z = Math.atan2(sd.x, -sd.z) * -1;
  glint.position.set(sd.x * 470, -1.4, sd.z * 470); root.add(glint);
  // cape: rock platform + a few boulders
  const rock = P.ink('#E8B07A', { shade: '#2C4C9A', ambient: 0.66, shadeGain: 0.55 });
  const cape = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(17, 22, 5, 14), rock), Wd.ink, 0.06); cape.position.y = -2.5; root.add(cape);
  const R = P.rng(8);
  for (let i = 0; i < 9; i++) { const a = R() * 6.28, d = 17 + R() * 6, s = 2 + R() * 3;
    const b = P.outlined(new THREE.Mesh(new THREE.DodecahedronGeometry(s, 0), rock), Wd.ink, 0.05); b.position.set(Math.sin(a) * d, -1.2, Math.cos(a) * d); b.rotation.set(R(), R(), R()); root.add(b); }
  // tower: base r 2.8 -> top r 2.0 over 16 m, white with halftone shading; gallery, lamp room, red cap
  const white = P.ink('#EDE3CF', { shade: '#8E95A6', hi: '#FFFFFF', ambient: 0.42, shadeGain: 0.9 });
  const tower = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.8, 16, 40), white), Wd.ink, 0.05); tower.position.y = 8; root.add(tower);
  const dark = P.ink('#1A1416', { flat: 1 });
  const gallery = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 0.3, 40), white), Wd.ink, 0.04); gallery.position.y = 16.15; root.add(gallery);
  for (let i = 0; i < 24; i++) { const a = i / 24 * 6.283; const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.9, 0.06), dark); p.position.set(Math.sin(a) * 2.5, 16.75, Math.cos(a) * 2.5); root.add(p); }
  const rail = new THREE.Mesh(new THREE.TorusGeometry(2.5, 0.05, 6, 48), dark); rail.rotation.x = Math.PI / 2; rail.position.y = 17.2; root.add(rail);
  const glass = new THREE.Mesh(new THREE.CylinderGeometry(1.45, 1.45, 2.0, 24), P.ink('#2C4C9A', { flat: 0.6 })); glass.position.y = 17.3; root.add(glass);
  for (let i = 0; i < 8; i++) { const a = i / 8 * 6.283; const p = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.0, 0.08), dark); p.position.set(Math.sin(a) * 1.47, 17.3, Math.cos(a) * 1.47); root.add(p); }
  const red = P.ink('#D9402B', { shade: '#7A2A22', ambient: 0.45 });
  const capm = P.outlined(new THREE.Mesh(new THREE.ConeGeometry(1.75, 1.3, 24), red), Wd.ink, 0.04); capm.position.y = 18.95; root.add(capm);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 8), dark); ball.position.y = 19.7; root.add(ball);
  const lamp = P.glow(Wd.lamp, 5, { strength: 1.0 }); lamp.position.y = 17.3; root.add(lamp);
  // door + red wooden stamp box by the door
  const dth = (params.doorTheta ?? -60) * Math.PI / 180;
  const door = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 2.0), P.ink('#2C4C9A', { flat: 1 }));
  door.position.set(Math.sin(dth) * 2.79, 1.0, Math.cos(dth) * 2.79); door.lookAt(Math.sin(dth) * 10, 1.0, Math.cos(dth) * 10); root.add(door);
  const sb = P.outlined(new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.55, 0.5), red), Wd.ink, 0.03);
  const sbx = dth + 0.62; sb.position.set(Math.sin(sbx) * 3.5, 1.15, Math.cos(sbx) * 3.5); sb.lookAt(Math.sin(sbx) * 10, 1.15, Math.cos(sbx) * 10); root.add(sb);
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.9, 0.12), P.ink('#8A4A26', { ambient: 0.5 })); post.position.set(Math.sin(sbx) * 3.5, 0.45, Math.cos(sbx) * 3.5); root.add(post);
  // rotating halftone beam (two wedges) that fades out in daylight
  const beamMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { ...P.U, uCol: { value: new THREE.Color(Wd.lamp) }, uFade: { value: 1.0 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 uCol; uniform float uPeriod, uAngle, uFade; uniform vec2 uJitter; varying vec2 vUv;
      void main(){ float tone = uFade * (1.0 - vUv.y) * 0.75 * (1.0 - abs(vUv.x - 0.5) * 2.0);
        vec2 f = gl_FragCoord.xy + uJitter; float c = cos(uAngle), s = sin(uAngle);
        vec2 q = fract(mat2(c, -s, s, c) * f / (uPeriod * 1.4)) - 0.5;
        if (tone < 0.01 || length(q) > sqrt(tone) * 0.62) discard; gl_FragColor = vec4(uCol, 1.0); }` });
  const beamPivot = new THREE.Group(); beamPivot.position.y = 17.3; root.add(beamPivot);
  for (const sg of [1, -1]) { const b = new THREE.Mesh(new THREE.PlaneGeometry(9, 160), beamMat); b.geometry.translate(0, 80, 0); b.rotation.x = Math.PI / 2; b.rotation.z = sg > 0 ? 0 : Math.PI; beamPivot.add(b); }
  // wrap-around word bands
  const rAt = (y) => 2.8 - 0.8 * (y / 16) + 0.05;
  const words = (params.words || []).map(w => {
    const cv = document.createElement('canvas'); const n = w.text.length;
    cv.width = Math.max(256, n * 150); cv.height = 200;
    const g = cv.getContext('2d'); g.clearRect(0, 0, cv.width, 200);
    g.font = '800 150px "Shippori Mincho B1", "Shippori Mincho", serif'; g.textBaseline = 'middle'; g.textAlign = 'center';
    const sp = cv.width / n;
    for (let i = 0; i < n; i++) { g.fillStyle = '#D9402B'; g.fillText(w.text[i], sp * (i + 0.5) + 9, 109); }
    for (let i = 0; i < n; i++) { g.fillStyle = '#EDE3CF'; g.fillText(w.text[i], sp * (i + 0.5), 100); }
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.NoColorSpace; tex.anisotropy = 8;
    const r = rAt(w.y); const len = n * 0.56; const th = len / r;
    const geo = new THREE.CylinderGeometry(r, r, 0.82, 64, 1, true, w.theta * Math.PI / 180 - th / 2, th);
    const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: tex, transparent: true, alphaTest: 0.35, side: THREE.FrontSide }));
    m.position.y = w.y; m.visible = false; root.add(m); return { m, t: w.t, t1: w.t1 ?? 1e9 };
  });
  // the sun: a camera-facing paper-cut disc (exact screen size set by params.sun.r in world units)
  const sunR = params.sun ? params.sun.r : 80;
  const sunG = new THREE.Group(); sunG.position.copy(sunP); root.add(sunG);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(sunR, 96), P.ink('#FFF2C8', { flat: 1, emissive: 1, fog: 0 })); sunG.add(disc);
  const corona = P.glow(Wd.glow, sunR * 4.2, { strength: 0.9 }); corona.position.z = -sunR * 0.5; sunG.add(corona);
  const camera = new THREE.PerspectiveCamera(params.fov || 40, 16 / 9, 0.1, 3000);
  const fade = params.beamFade || [1e9, 1e9 + 1];
  function update(t) {
    applyPath(camera, params.path, t);
    beamPivot.rotation.y = t * 1.3;
    beamMat.uniforms.uFade.value = 1.0 - Math.min(1, Math.max(0, (t - fade[0]) / (fade[1] - fade[0])));
    words.forEach(w => { w.m.visible = t >= w.t && t < w.t1; });
    sunG.lookAt(camera.position);
  }
  const anchors = () => ({ door: [new THREE.Vector3(Math.sin(dth) * 3.3, 0.0, Math.cos(dth) * 3.3)],
                           doorFar: [new THREE.Vector3(Math.sin(dth - 0.55) * 8.0, 0.0, Math.cos(dth - 0.55) * 8.0)],
                           sun: [sunP.clone()], lamp: [new THREE.Vector3(0, 17.3, 0)] });
  return { scene: root, camera, update, anchors };
}
