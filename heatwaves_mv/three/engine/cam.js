// Keyframed camera paths: params.path = [{t, pos:[x,y,z], look:[x,y,z], fov, roll, ease}]
// Positions/looks are interpolated with Catmull-Rom through the keys (C1-smooth), time is eased per segment.
export function easeInOut(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
export function easeOut(x) { return 1 - Math.pow(1 - x, 3); }
export function easeIn(x) { return x * x * x; }
const EASE = { linear: x => x, inout: easeInOut, out: easeOut, in: easeIn };

function cr(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}

export function samplePath(path, t) {
  if (!path || !path.length) return null;
  if (t <= path[0].t) return { pos: path[0].pos, look: path[0].look, fov: path[0].fov, roll: path[0].roll || 0, bank: path[0].bank || 0 };
  const last = path[path.length - 1];
  if (t >= last.t) return { pos: last.pos, look: last.look, fov: last.fov, roll: last.roll || 0, bank: last.bank || 0 };
  let i = 0;
  while (i < path.length - 2 && t > path[i + 1].t) i++;
  const a = path[i], b = path[i + 1];
  const e = EASE[b.ease || 'inout'];
  const u = e((t - a.t) / (b.t - a.t));
  const p0 = path[Math.max(0, i - 1)], p3 = path[Math.min(path.length - 1, i + 2)];
  const lerpV = (k) => [0, 1, 2].map(j => cr(p0[k][j], a[k][j], b[k][j], p3[k][j], u));
  const fa = a.fov ?? 40, fb = b.fov ?? fa;
  return { pos: lerpV('pos'), look: lerpV('look'), fov: fa + (fb - fa) * u, roll: (a.roll || 0) + ((b.roll || 0) - (a.roll || 0)) * u,
           bank: (a.bank || 0) + ((b.bank || 0) - (a.bank || 0)) * u };
}

export function applyPath(camera, path, t, mirrorX = false) {
  const s = samplePath(path, t);
  if (!s) return false;
  const sx = mirrorX ? -1 : 1;
  camera.position.set(s.pos[0] * sx, s.pos[1], s.pos[2]);
  camera.up.set(Math.sin(s.roll * Math.PI / 180), Math.cos(s.roll * Math.PI / 180), 0);
  camera.lookAt(s.look[0] * sx, s.look[1], s.look[2]);
  if (s.bank) camera.rotateZ(s.bank * Math.PI / 180 * sx);       // true roll about the view axis, any heading
  if (s.fov && camera.fov !== s.fov) { camera.fov = s.fov; camera.updateProjectionMatrix(); }
  return true;
}
