// One-car local train (Showa diesel railcar look) with lit windows and an LED destination board texture.
export function makeTrain(THREE, P, Wd, { body = '#EDE3CF', band = '#D9402B', windowInk = null, led = 'ワンマン 海岸線', length = 18,
                                         bigBoard = false, boardSize = null, headColor = '#FFF6DC', headSize = 3.2 } = {}) {
  const g = new THREE.Group();
  const box = (w, h, d, m) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  const bodyMat = P.ink(body, { shade: Wd.wallShade || '#5E6E86', hi: '#FFFFFF', ambient: 0.4 });
  const car = P.outlined(box(2.8, 2.7, length, bodyMat), Wd.ink, 0.03); car.position.y = 2.15; g.add(car);
  const bandM = P.ink(band, { ambient: 0.5 });
  for (const s of [-1, 1]) {
    const b = box(0.02, 0.32, length - 0.4, bandM); b.position.set(s * 1.41, 1.25, 0); g.add(b);
  }
  const roof = P.outlined(box(2.6, 0.25, length - 0.2, P.ink('#8E95A6', { shade: '#3A3F55' })), Wd.ink, 0.02);
  roof.position.y = 3.6; g.add(roof);
  const winMat = P.ink(windowInk || Wd.window || '#F0B45A', { emissive: 1.0 });
  const windows = [];
  for (const s of [-1, 1]) for (let k = 0; k < 7; k++) {
    const w = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.95), winMat);
    w.position.set(s * 1.415, 2.55, -length / 2 + 1.9 + k * 2.3); w.rotation.y = s * Math.PI / 2; g.add(w);
    windows.push(w);
    if (k % 2 === 0) { const gl = P.glow(Wd.window || '#F0B45A', 2.4, { strength: 0.5 }); gl.position.set(s * 1.9, 2.5, w.position.z); g.add(gl); }
  }
  // front: windshield + headlight + LED board
  const fh = boardSize ? Math.max(0.5, boardSize[2] - boardSize[1] / 2 - 2.0) : (bigBoard ? 0.8 : 0.9);
  const front = new THREE.Mesh(new THREE.PlaneGeometry(2.2, fh), P.ink(Wd.roadShade || '#26345E', { flat: 0.7 }));
  front.position.set(0, boardSize ? 1.95 + fh / 2 : (bigBoard ? 2.55 : 2.75), length / 2 + 0.01); g.add(front);
  const c = document.createElement('canvas'); c.width = 384; c.height = 48;
  const ctx = c.getContext('2d'); ctx.fillStyle = '#0B1414'; ctx.fillRect(0, 0, 384, 48);
  ctx.fillStyle = '#7FC8B8'; ctx.font = 'bold 34px monospace'; ctx.fillText(led, 10, 36);
  const ledM = P.flatTex(c);
  const [bw, bh, by] = boardSize || (bigBoard ? [1.9, 0.42, 3.2] : [1.6, 0.2, 3.38]);
  const board = new THREE.Mesh(new THREE.PlaneGeometry(bw, bh), bigBoard ? P.ink('#0B1414', { flat: 1 }) : ledM);
  board.position.set(0, by, length / 2 + 0.02); g.add(board);
  const corners = [[-bw / 2, bh / 2], [bw / 2, bh / 2], [bw / 2, -bh / 2], [-bw / 2, -bh / 2]].map(([x, y]) => new THREE.Vector3(x, by + y, length / 2 + 0.03));
  const head = P.glow(headColor, headSize, { strength: 1.0 }); head.position.set(0, 1.4, length / 2 + 0.4); g.add(head);
  const lamp = new THREE.Mesh(new THREE.CircleGeometry(0.16, 16), P.ink(headColor, { emissive: 1 })); lamp.position.set(0, 1.4, length / 2 + 0.03); g.add(lamp);
  return { group: g, windows, board, headGlow: head, boardCorners: corners, headPos: new THREE.Vector3(0, 1.4, length / 2 + 0.05) };
}
