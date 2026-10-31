// S9: a T-junction on the coast road at noon (MV-B chorus1-01 / chorus1-06): wooden houses with tiled roofs, a vending
// machine, a bus-stop sign, wires, and curve mirrors on orange poles. Mirror faces are flat discs whose content is
// composited in 2D (anchors give each mirror's centre and two rim points). params.mirrors: [{pos, yaw, tilt, r, pole}]
// params.forest: N extra mirrors scattered along the road (the mirror forest). params.path: camera keys.
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'noon'];
  const R = P.rng(params.seed || 11);
  const root = new THREE.Scene();
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = params.fogNear || 60; P.U.uFogFar.value = params.fogFar || 380;
  P.U.uLightDir.value.set(...Wd.light).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: 0, band: Wd.skyBand }));
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  // ground: asphalt cross (main road along z, side road along -x), pavement, sea beyond +x
  const asph = P.ink(Wd.road, { shade: Wd.roadShade, ambient: 0.62 });
  const main = box(7.4, 0.2, 400, asph); main.position.set(0, -0.1, 0); root.add(main);
  const side = box(200, 0.2, 6.4, asph); side.position.set(-103.7, -0.1, 0); root.add(side);
  const pave = P.ink(Wd.wall, { shade: Wd.wallShade, ambient: 0.6 });
  const ground = box(400, 0.1, 400, pave); ground.position.set(0, -0.25, 0); root.add(ground);
  const line = P.ink(Wd.line, { flat: 1 });
  for (let z = -200; z < 200; z += 6) { if (Math.abs(z) < 5) continue; const d = box(0.15, 0.02, 3.0, line); d.position.set(0, 0.01, z); root.add(d); }
  const stop = box(6.4, 0.02, 0.35, line); stop.position.set(-3.9, 0.01, 0); stop.rotation.y = Math.PI / 2; root.add(stop);
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), P.ink(Wd.sea, { flat: 1, grain: 0.1 }));
  sea.rotation.x = -Math.PI / 2; sea.position.set(1012, -1.2, 0); root.add(sea);
  const wall = P.outlined(box(0.6, 1.0, 400, P.ink(Wd.wall, { shade: Wd.wallShade, ambient: 0.5 })), Wd.ink, 0.02); wall.position.set(5.6, 0.5, 0); root.add(wall);
  // houses with tiled roofs on the land side (-x), both sides of the side road
  const houseMat = P.ink(Wd.house, { shade: Wd.houseShade, ambient: 0.35 });
  const roofMat = P.ink(Wd.roof, { shade: Wd.ink, ambient: 0.5 });
  const winMat = P.ink(Wd.window, { flat: 0.6 });
  for (const sgn of [-1, 1]) for (let z = 4.5; z < 160; z += 8.5 + R() * 4) {
    const w = 6 + R() * 3, d = 6 + R() * 2, h = 3.4 + R() * 2.4, x = -6.5 - w / 2 - R() * 2;
    const hz = sgn * (z + d / 2);
    const hs = P.outlined(box(w, h, d, houseMat), Wd.ink, 0.03); hs.position.set(x, h / 2, hz); root.add(hs);
    const sh = new THREE.Shape(); sh.moveTo(-w / 2 - 0.5, 0); sh.lineTo(w / 2 + 0.5, 0); sh.lineTo(0, w * 0.3); sh.closePath();
    const rg = new THREE.ExtrudeGeometry(sh, { depth: d + 0.7, bevelEnabled: false }); rg.translate(0, 0, -(d + 0.7) / 2);
    const roof = P.outlined(new THREE.Mesh(rg, roofMat), Wd.ink, 0.03); roof.position.set(x, h, hz); root.add(roof);
    for (let k = 0; k < 2; k++) { const wi = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 0.9), winMat);
      wi.position.set(x + w / 2 + 0.03, 1.5 + k * 1.5, hz + (R() - 0.5) * d * 0.5); wi.rotation.y = Math.PI / 2; root.add(wi); }
  }
  // vending machine + bus-stop sign at the corner
  const vend = P.outlined(box(1.0, 1.85, 0.75, P.ink(Wd.vend, { emissive: 0.8 })), Wd.ink, 0.025); vend.position.set(-4.6, 0.92, 7.5); root.add(vend);
  const bsPole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 2.4, 8), P.ink(Wd.pole, { ambient: 0.6 })); bsPole.position.set(-4.3, 1.2, -6.0); root.add(bsPole);
  const bs = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.06, 24), P.ink('#F6F2E7', { flat: 1 })), Wd.ink, 0.02);
  bs.rotation.z = Math.PI / 2; bs.position.set(-4.3, 2.45, -6.0); root.add(bs);
  // telephone poles + wires along the main road (land side)
  const poleM = P.ink(Wd.pole, { ambient: 0.6 });
  const tops = [];
  for (let z = -160; z < 160; z += 16.3) {
    const p = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.16, 8.6, 8), poleM), Wd.ink, 0.02); p.position.set(-5.4, 4.3, z + 8); root.add(p);
    tops.push(new THREE.Vector3(-5.4, 8.4, z + 8));
  }
  for (let i = 0; i + 1 < tops.length; i++) for (const dx of [-0.6, 0.6]) {
    const a = tops[i].clone().add(new THREE.Vector3(dx, 0, 0)), b = tops[i + 1].clone().add(new THREE.Vector3(dx, 0, 0));
    root.add(P.line(P.catenary(a, b, 0.5), Wd.ink));
  }
  // curve mirrors
  const mpMat = P.ink(Wd.mirrorPole, { ambient: 0.55 });
  const faceMat = P.ink('#C9D3DC', { flat: 1 });
  const mirrors = [];
  const list = (params.mirrors || []).slice();
  if (params.forest) { for (let i = 0; i < params.forest; i++) {
    const z = -6 + i * 4.2 + R() * 1.5, side = i % 2 ? 1 : -1;
    list.push({ pos: [side * (2.2 + R() * 2.0), 2.4 + R() * 1.4, z], yaw: (side > 0 ? -1 : 1) * (0.4 + R() * 0.8) + Math.PI, tilt: 0.1, r: 0.5 + R() * 0.15, pole: true });
  } }
  for (const m of list) {
    const g = new THREE.Group(); g.position.set(...m.pos); g.rotation.order = 'YXZ'; g.rotation.y = m.yaw || 0; g.rotation.x = m.tilt || 0;
    const r = m.r || 0.55;
    const face = new THREE.Mesh(new THREE.CircleGeometry(r, 40), faceMat); face.position.z = 0.02; g.add(face);
    const rim = P.outlined(new THREE.Mesh(new THREE.TorusGeometry(r + 0.04, 0.06, 8, 40), mpMat), Wd.ink, 0.02); g.add(rim);
    const back = new THREE.Mesh(new THREE.CircleGeometry(r + 0.05, 40), mpMat); back.rotation.y = Math.PI; back.position.z = -0.03; g.add(back);
    const hood = new THREE.Mesh(new THREE.CylinderGeometry(r + 0.1, r + 0.1, 0.22, 24, 1, true, -Math.PI / 2, Math.PI), mpMat);
    hood.rotation.x = Math.PI / 2; hood.position.z = 0.05; g.add(hood);
    root.add(g);
    if (m.pole !== false) {
      const ph = m.pos[1] + 0.2;
      const pole = P.outlined(new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, ph, 8), mpMat), Wd.ink, 0.02); pole.position.set(m.pos[0], ph / 2 - 0.3, m.pos[2]); root.add(pole);
    }
    mirrors.push({ g, r });
  }
  const camera = new THREE.PerspectiveCamera(params.fov || 40, 16 / 9, 0.05, 3000);
  function update(t) { applyPath(camera, params.path, t); }
  const anchors = () => {
    const c = [], ex = [], ey = [];
    for (const { g, r } of mirrors) {
      g.updateMatrixWorld(true);
      c.push(g.localToWorld(new THREE.Vector3(0, 0, 0.03)));
      ex.push(g.localToWorld(new THREE.Vector3(r, 0, 0.03)));
      ey.push(g.localToWorld(new THREE.Vector3(0, r, 0.03)));
    }
    return { mirrors: c, mirrorX: ex, mirrorY: ey };
  };
  return { scene: root, camera, update, anchors };
}
