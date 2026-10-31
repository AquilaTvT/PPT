// S7: school outdoor pool (8 lanes, lane ropes, starting blocks, chain-link fence, LED scoreboard anchor),
// water with an animated caustic line-screen. worlds: noon | morning
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'noon'];
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = 80; P.U.uFogFar.value = 600;
  P.U.uLightDir.value.set(...Wd.light).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: 0, band: Wd.skyBand }));
  const sun = P.disc('#FFF6DC', '#F5C842', 22); sun.position.set(-120, 260, -420); sun.lookAt(0, 0, 0); root.add(sun);
  const sunGlow = P.glow('#FFF6DC', 220, { strength: 0.6 }); sunGlow.position.copy(sun.position).multiplyScalar(0.97); root.add(sunGlow);
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  const LW = 25, PW = 16;
  const deckMat = P.ink('#E6E0D2', { shade: '#8E95A6', ambient: 0.6, grain: 0.12 });
  for (const [w, d, x, z] of [[60, 21, 0, PW / 2 + 10.5], [60, 21, 0, -PW / 2 - 10.5], [17.5, PW, -LW / 2 - 8.75, 0], [17.5, PW, LW / 2 + 8.75, 0]]) {
    const dk = box(w, 0.4, d, deckMat); dk.position.set(x, -0.2, z); root.add(dk);
  }
  const floorB = box(LW, 0.2, PW, P.ink('#5FB8CC', { ambient: 0.6 })); floorB.position.set(0, -1.4, 0); root.add(floorB);
  // basin walls (light aqua tiles) + water
  const tile = P.ink('#9FD3E0', { shade: '#3F8FA8', ambient: 0.5 });
  const wl = box(0.3, 1.4, PW, tile); wl.position.set(-LW / 2, -0.7, 0); root.add(wl);
  const wr = box(0.3, 1.4, PW, tile); wr.position.set(LW / 2, -0.7, 0); root.add(wr);
  const waterMat = new THREE.ShaderMaterial({
    uniforms: { ...P.U, uA: { value: new THREE.Color('#2EC4D6') }, uB: { value: new THREE.Color('#E8FAFF') }, uDeep: { value: new THREE.Color('#1F8FB0') } },
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `
      uniform vec3 uA, uB, uDeep; uniform float uTime, uPeriod; uniform vec2 uJitter; varying vec3 vW;
      void main(){
        vec2 p = vW.xz * 0.9;
        float c = 0.0;
        c += sin(p.x * 2.1 + sin(p.y * 1.3 + uTime * 1.1) * 1.7 + uTime * 0.9);
        c += sin(p.y * 2.4 + sin(p.x * 1.1 - uTime * 0.8) * 1.9 - uTime * 0.7);
        c = abs(c) * 0.5;
        float line = step(c, 0.16);                       // caustic network as thin bright lines
        float lane = step(0.94, fract((vW.x + 12.5) / 3.125)) * step(abs(vW.z), 7.0);
        vec3 col = mix(uA, uDeep, lane * 0.85);
        float scr = step(0.5, fract((gl_FragCoord.y + uJitter.y) / (uPeriod * 0.75)));   // line-screen
        col = mix(col, uB, line * scr);
        gl_FragColor = vec4(col, 1.0);
      }` });
  const water = new THREE.Mesh(new THREE.PlaneGeometry(LW, PW), waterMat); water.rotation.x = -Math.PI / 2; water.position.y = -0.15; root.add(water);
  // lane ropes
  const ropeTex = document.createElement('canvas'); ropeTex.width = 64; ropeTex.height = 8;
  const rg = ropeTex.getContext('2d'); for (let i = 0; i < 8; i++) { rg.fillStyle = ['#D9402B', '#EDE3CF', '#2C4C9A', '#EDE3CF'][i % 4]; rg.fillRect(i * 8, 0, 8, 8); }
  const ropeMat = P.flatTex(ropeTex); ropeMat.map.wrapS = THREE.RepeatWrapping; ropeMat.map.repeat.set(40, 1);
  for (let k = 1; k < 8; k++) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, LW, 8), ropeMat);
    r.rotation.z = Math.PI / 2; r.position.set(0, -0.1, -PW / 2 + k * PW / 8); root.add(r);
  }
  // starting blocks at the near end (x = -LW/2)
  const blk = P.ink('#EDE3CF', { shade: '#8E95A6' });
  for (let k = 0; k < 8; k++) { const b = P.outlined(box(0.6, 0.7, 0.55, blk), Wd.ink, 0.015); b.position.set(-LW / 2 - 0.5, 0.35, -PW / 2 + (k + 0.5) * PW / 8); root.add(b); }
  // fence (chain link as a dotted line-screen plane)
  const fenceMat = new THREE.ShaderMaterial({ transparent: true, side: THREE.DoubleSide, uniforms: { ...P.U, uC: { value: new THREE.Color('#5A6070') } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform vec3 uC; varying vec2 vUv; void main(){ vec2 g = abs(fract(vec2(vUv.x*60.0 + vUv.y*15.0, vUv.x*60.0 - vUv.y*15.0)) - 0.5);
      float l = step(0.44, max(g.x, g.y)); if (l < 0.5) discard; gl_FragColor = vec4(uC, 1.0); }` });
  const fence = new THREE.Mesh(new THREE.PlaneGeometry(60, 3), fenceMat); fence.position.set(0, 1.5, -PW / 2 - 6); root.add(fence);
  // LED scoreboard at the far end on posts (x = +LW/2 + 4)
  const sbMat = P.ink('#141018', { flat: 0.8 });
  const sb = P.outlined(box(0.4, 4.2, 9.0, sbMat), Wd.ink, 0.02); sb.position.set(LW / 2 + 5, 5.0, 0); root.add(sb);
  for (const z of [-3.5, 3.5]) { const p = box(0.3, 3.0, 0.3, P.ink('#5A6070', { ambient: 0.6 })); p.position.set(LW / 2 + 5, 1.5, z); root.add(p); }
  const camera = new THREE.PerspectiveCamera(params.fov || 40, 16 / 9, 0.05, 3000);
  function update(t) {
    if (!(params.path && applyPath(camera, params.path, t))) { camera.position.set(-LW / 2 - 3, 2.2, 5); camera.lookAt(LW / 2, 2.5, -1); }
  }
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const x0 = LW / 2 + 4.79;
  const anchors = () => ({ scoreboard: [V(x0, 7.0, 4.4), V(x0, 7.0, -4.4), V(x0, 3.0, -4.4), V(x0, 3.0, 4.4)] });
  return { scene: root, camera, update, anchors };
}
