// S4: small seaside station (one platform, shelter roof, name board, bench, lamps) + one-car train.
// params.train: {z0, speed, t0}  cam: 'platform' | 'low' | 'side' | 'chase'
import { WORLDS } from '/scenes/worlds.js';
import { applyPath } from '/engine/cam.js';
import { makeTrain } from '/scenes/train.js';

export async function build(THREE, P, params = {}) {
  const Wd = WORLDS[params.world || 'night'];
  const root = new THREE.Scene();
  const scene = new THREE.Group(); scene.scale.x = -1; root.add(scene);
  P.U.uFogColor.value.set(Wd.fog); P.U.uFogNear.value = 50; P.U.uFogFar.value = 380;
  P.U.uLightDir.value.set(...Wd.light).normalize(); P.U.uPeriod.value = params.period || 8;
  root.add(P.sky(Wd.skyTop, Wd.skyHor, { stars: Wd.stars, band: Wd.skyBand }));
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  const L = 600;
  // ground, sea beyond
  const ground = box(60, 0.2, L, P.ink(Wd.ballast, { ambient: 0.5 })); ground.position.set(-20, -0.1, 0); scene.add(ground);
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(3000, 3000), P.ink(Wd.sea, { flat: 1, grain: 0.06 }));
  sea.rotation.x = -Math.PI / 2; sea.position.set(1500, -1.0, 0); scene.add(sea);
  // rails
  const railMat = P.ink(Wd.rail, { flat: 0.6 });
  for (const x of [-0.72, 0.72]) { const r = box(0.08, 0.16, L, railMat); r.position.set(x, 0.18, 0); scene.add(r); }
  const sl = new THREE.InstancedMesh(new THREE.BoxGeometry(2.4, 0.08, 0.22), P.ink(Wd.roadShade, { ambient: 0.5 }), Math.floor(L / 0.7));
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < sl.count; i++) { m4.makeTranslation(0, 0.1, -L / 2 + i * 0.7); sl.setMatrixAt(i, m4); } scene.add(sl);
  // platform (left side of the track), shelter, bench, name board, lamps
  const platMat = P.ink(Wd.wall, { shade: Wd.wallShade, ambient: 0.35 });
  const plat = P.outlined(box(4.0, 1.0, 60, platMat), Wd.ink, 0.03); plat.position.set(-3.7, 0.5, 0); scene.add(plat);
  const edge = box(0.25, 0.02, 60, P.ink('#F5C842', { flat: 1 })); edge.position.set(-1.85, 1.01, 0); scene.add(edge);
  const roofM = P.ink(Wd.roof, { ambient: 0.5 });
  const roof = P.outlined(box(3.4, 0.15, 14, roofM), Wd.ink, 0.03); roof.position.set(-4.0, 3.7, 0); roof.rotation.z = 0.08; scene.add(roof);
  for (const z of [-6, 0, 6]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 2.7, 8), P.ink(Wd.pole, { ambient: 0.6 })); p.position.set(-4.9, 2.35, z); scene.add(p); }
  const bench = P.outlined(box(0.5, 0.45, 2.2, P.ink('#7A3E5A', { shade: '#2B2350' })), Wd.ink, 0.02); bench.position.set(-4.8, 1.22, 2.5); scene.add(bench);
  const nb = document.createElement('canvas'); nb.width = 512; nb.height = 160;
  const g = nb.getContext('2d'); g.fillStyle = '#EDE3CF'; g.fillRect(0, 0, 512, 160);
  g.fillStyle = '#141A33'; g.font = 'bold 74px serif'; g.textAlign = 'center'; g.fillText(params.stationName || 'うみべ', 256, 92);
  g.fillStyle = '#2C4C9A'; g.fillRect(0, 118, 512, 42); g.fillStyle = '#EDE3CF'; g.font = '26px serif'; g.fillText(params.stationRoman || 'UMIBE', 256, 148);
  const board = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 0.69), P.flatTex(nb)); board.position.set(-2.4, 3.0, 9); board.rotation.y = Math.PI / 2; scene.add(board);
  for (const z of [-14, 9, 22]) {
    const lp = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 3.4, 8), P.ink(Wd.pole, { ambient: 0.6 })); lp.position.set(-3.0, 2.7, z); scene.add(lp);
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.25), P.ink(Wd.lamp, { emissive: 1 })); head.position.set(-2.8, 4.4, z); scene.add(head);
    const gl = P.glow(Wd.glow, 3.0, { strength: 0.75 }); gl.position.set(-2.8, 4.2, z); scene.add(gl);
  }
  // train
  const tr = makeTrain(THREE, P, Wd, { led: params.led || 'ワンマン 海岸線' });
  scene.add(tr.group);
  const T = params.train || { z0: -120, speed: 0, t0: 0, decel: 0 };
  const cam = params.cam || 'platform';
  const camera = new THREE.PerspectiveCamera(params.fov || 40, 16 / 9, 0.05, 2000);
  function update(t) {
    const pathed = params.path ? applyPath(camera, params.path, t, true) : false;
    const dt = Math.max(0, t - (T.t0 || 0));
    tr.group.position.set(0, 0, (T.z0 || 0) + (T.speed || 0) * dt + 0.5 * (T.accel || 0) * dt * dt);
    if (pathed) {} else if (cam === 'platform') { camera.position.set(-3.2, 2.4, -12); camera.lookAt(-0.5, 2.0, 10); }
    else if (cam === 'low') { camera.position.set(-1.5, 1.2, 14); camera.lookAt(0, 2.2, -10); }
    else if (cam === 'side') { camera.position.set(-5.5, 2.4, tr.group.position.z * (params.follow ? 1 : 0)); camera.lookAt(0, 2.4, camera.position.z); }
    else if (cam === 'chase') { const z = tr.group.position.z; camera.position.set(4.5, 2.2, z - 6); camera.lookAt(0.5, 2.3, z + 8); }
  }
  const anchors = () => ({ windows: tr.windows.slice(7, 14).map(w => w.getWorldPosition(new THREE.Vector3())) });
  return { scene: root, camera, update, anchors };
}
