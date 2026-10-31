// Print-style (silkscreen / risograph) materials for three.js: flat inks, screen-locked 45-degree halftone
// shading, halftone fog, halftone glows, inverted-hull ink outlines, halftone sky.
import * as THREE from '/node_modules/three/build/three.module.js';

export const U = {               // shared uniforms (one object -> every material sees the same values)
  uPeriod: { value: 8.0 },      // halftone cell size in device px (reference: ~7-9 px)
  uAngle: { value: Math.PI / 4 },
  uJitter: { value: new THREE.Vector2(0, 0) },
  uLightDir: { value: new THREE.Vector3(0.4, 0.8, 0.45).normalize() },
  uFogColor: { value: new THREE.Color('#1E2550') },
  uFogNear: { value: 40.0 },
  uFogFar: { value: 260.0 },
  uPulse: { value: 0.0 },        // beat pulse 0..1 (emissives and glows swell)
  uTime: { value: 0.0 },
};

const DOT = /* glsl */`
float htDot(float tone, vec2 frag, float period, float angle) {
  float c = cos(angle), s = sin(angle);
  vec2 p = mat2(c, s, -s, c) * frag / period;
  vec2 cell = fract(p) - 0.5;
  float d = length(cell);
  float r = sqrt(clamp(tone, 0.0, 1.0)) * 0.64;
  float aa = 0.75 / period;
  return (tone <= 0.004) ? 0.0 : smoothstep(r + aa, r - aa, d);
}
`;

const VERT = /* glsl */`
varying vec3 vN; varying vec3 vW; varying float vDepth;
void main() {
#ifdef USE_INSTANCING
  vec4 w = modelMatrix * instanceMatrix * vec4(position, 1.0);
  vN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal);
#else
  vec4 w = modelMatrix * vec4(position, 1.0);
  vN = normalize(mat3(modelMatrix) * normal);
#endif
  vW = w.xyz;
  vec4 mv = viewMatrix * w;
  vDepth = -mv.z;
  gl_Position = projectionMatrix * mv;
}`;

// ink: base colour, shade: halftone ink in shadow, hi: highlight dots (paper), emissive: 0..1 flat glow
export function ink(base, { shade = null, hi = null, ambient = 0.35, flat = 0.0, emissive = 0.0, fog = 1.0,
                            shadeGain = 1.0, side = THREE.FrontSide, grain = 0.10 } = {}) {
  const b = new THREE.Color(base);
  const s = shade ? new THREE.Color(shade) : b.clone().multiplyScalar(0.42);
  const h = hi ? new THREE.Color(hi) : null;
  return new THREE.ShaderMaterial({
    side,
    uniforms: {
      ...U,
      uInk: { value: b }, uShade: { value: s }, uHi: { value: h || b }, uHasHi: { value: h ? 1.0 : 0.0 },
      uAmbient: { value: ambient }, uFlat: { value: flat }, uEmissive: { value: emissive }, uFogAmt: { value: fog },
      uShadeGain: { value: shadeGain }, uGrain: { value: grain },
    },
    vertexShader: VERT,
    fragmentShader: /* glsl */`
      uniform vec3 uInk, uShade, uHi, uLightDir, uFogColor;
      uniform float uHasHi, uAmbient, uFlat, uEmissive, uFogAmt, uFogNear, uFogFar, uPeriod, uAngle, uPulse, uShadeGain, uGrain;
      uniform vec2 uJitter;
      varying vec3 vN; varying vec3 vW; varying float vDepth;
      ${DOT}
      void main() {
        vec2 frag = gl_FragCoord.xy + uJitter;
        vec3 n = normalize(vN);
        if (!gl_FrontFacing) n = -n;
        float ndl = max(dot(n, uLightDir), 0.0);
        float lit = mix(uAmbient + (1.0 - uAmbient) * ndl, 1.0, uFlat);
        float tone = clamp((0.92 - lit) * 1.45 * uShadeGain + uGrain * (1.0 - uEmissive), 0.0, 1.0);
        vec3 col = uInk;
        if (lit < 0.22) { col = uShade; }                 // deep shadow: solid shade ink (print band)
        else { col = mix(uInk, uShade, htDot(tone, frag, uPeriod, uAngle)); }
        if (uHasHi > 0.5) {
          float ht = clamp((lit - 0.93) * 9.0, 0.0, 1.0);
          col = mix(col, uHi, htDot(ht * 0.6, frag + 0.5 * uPeriod, uPeriod, uAngle));
        }
        if (uEmissive > 0.0) col = mix(col, uInk * (1.0 + 0.35 * uPulse), uEmissive);
        float f = clamp((vDepth - uFogNear) / (uFogFar - uFogNear), 0.0, 1.0) * uFogAmt;
        if (f > 0.0) {                                    // atmospheric perspective as fog-ink dots, then solid
          float fd = htDot(f * 1.15, frag + vec2(0.37, 0.71) * uPeriod, uPeriod, uAngle);
          col = mix(col, uFogColor, max(fd * step(f, 0.86), step(0.86, f)));
        }
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
}

// inverted-hull outline in ink colour (width in world units, scaled by distance in the shader)
export function outlined(mesh, color = '#141018', width = 0.035) {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    uniforms: { uCol: { value: new THREE.Color(color) }, uW: { value: width }, ...U },
    vertexShader: /* glsl */`
      uniform float uW; varying float vDepth;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        float w = uW * clamp(-mv.z * 0.06, 0.6, 4.0);
        vec3 nv = normalize(normalMatrix * normal);
        mv.xyz += nv * w;
        vDepth = -mv.z;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uCol, uFogColor; uniform float uFogNear, uFogFar; varying float vDepth;
      void main() {
        float f = clamp((vDepth - uFogNear) / (uFogFar - uFogNear), 0.0, 1.0);
        gl_FragColor = vec4(mix(uCol, uFogColor, f * f), 1.0);
      }`,
  });
  const hull = new THREE.Mesh(mesh.geometry, mat);
  hull.renderOrder = -1;
  mesh.add(hull);
  return mesh;
}

// halftone glow billboard: dots shrink with distance from the centre (reference: dots ~25px at the core)
export function glow(color, size, { strength = 1.0, period = null } = {}) {
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { ...U, uCol: { value: new THREE.Color(color) }, uStr: { value: strength },
                uP: { value: period || 0.0 } },
    vertexShader: /* glsl */`
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vec4 mv = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        vec2 scale = vec2(length(modelMatrix[0].xyz), length(modelMatrix[1].xyz));
        mv.xy += (uv - 0.5) * scale;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uCol; uniform float uStr, uP, uPeriod, uAngle, uPulse; uniform vec2 uJitter;
      varying vec2 vUv;
      ${DOT}
      void main() {
        float r = length(vUv - 0.5) * 2.0;
        float tone = exp(-r * r * 3.2) * uStr * (1.0 + 0.45 * uPulse);
        float per = uP > 0.0 ? uP : uPeriod * 1.6;
        float m = htDot(tone, gl_FragCoord.xy + uJitter + vec2(0.5) * per, per, uAngle);
        if (m < 0.02) discard;
        gl_FragColor = vec4(uCol, m);
      }`,
  });
  const sp = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
  sp.scale.set(size, size, 1);
  sp.renderOrder = 10;
  return sp;
}

// sky dome: vertical two-ink gradient expressed as dot density, plus star dots
export function sky(top, horizon, { stars = 0.0, band = null } = {}) {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { ...U, uTop: { value: new THREE.Color(top) }, uHor: { value: new THREE.Color(horizon) },
                uStars: { value: stars }, uBand: { value: new THREE.Color(band || horizon) } },
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform vec3 uTop, uHor, uBand; uniform float uStars, uPeriod, uAngle, uTime; uniform vec2 uJitter;
      varying vec3 vDir;
      ${DOT}
      float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      void main() {
        vec2 frag = gl_FragCoord.xy + uJitter;
        float y = clamp(vDir.y, -0.2, 1.0);
        float t = 1.0 - smoothstep(0.0, 0.55, y);                // 1 at the horizon
        vec3 col = mix(uTop, uHor, htDot(t * 0.95, frag, uPeriod * 1.35, uAngle));
        float b = exp(-pow(y / 0.05, 2.0));                       // thin glowing band at the horizon
        col = mix(col, uBand, htDot(b * 0.8, frag + 3.0, uPeriod * 0.9, uAngle));
        if (uStars > 0.0 && y > 0.12) {
          vec2 g = floor(vDir.xz / max(0.2, vDir.y) * 140.0);
          float s = step(1.0 - 0.012 * uStars, h21(g));
          float tw = 0.6 + 0.4 * sin(uTime * 3.0 + h21(g + 7.0) * 30.0);
          col = mix(col, vec3(0.93, 0.89, 0.81), s * tw);
        }
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(900, 48, 24), mat);
}

// paper-cut disc (moon / sun) with halftone craters
export function disc(color, shadeColor, radius) {
  const mat = new THREE.ShaderMaterial({
    depthWrite: false, transparent: true,
    uniforms: { ...U, uCol: { value: new THREE.Color(color) }, uSh: { value: new THREE.Color(shadeColor) } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);}`,
    fragmentShader: /* glsl */`
      uniform vec3 uCol, uSh; uniform float uPeriod, uAngle; uniform vec2 uJitter; varying vec2 vUv;
      ${DOT}
      float n2(vec2 p){ return fract(sin(dot(floor(p), vec2(12.9898,78.233))) * 43758.5453); }
      void main(){
        vec2 q = vUv - 0.5; float r = length(q) * 2.0;
        if (r > 1.0) discard;
        float cr = 0.0;
        for (int i = 0; i < 6; i++) {
          vec2 c = vec2(n2(vec2(float(i), 1.0)), n2(vec2(1.0, float(i)))) - 0.5;
          float rr = 0.08 + 0.12 * n2(vec2(float(i), 3.0));
          cr = max(cr, smoothstep(rr, rr * 0.6, length(q * 1.6 - c * 0.9)) * 0.55);
        }
        float rim = smoothstep(0.75, 1.0, r) * 0.45;
        vec3 col = mix(uCol, uSh, htDot(cr + rim, gl_FragCoord.xy + uJitter, uPeriod, uAngle));
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(radius * 2, radius * 2), mat);
  m.renderOrder = -5;
  return m;
}

export function line(points, color = '#141018') {
  const g = new THREE.BufferGeometry().setFromPoints(points);
  return new THREE.Line(g, new THREE.LineBasicMaterial({ color }));
}

export function catenary(a, b, sag = 0.6, n = 16) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = new THREE.Vector3().lerpVectors(a, b, t);
    p.y -= sag * 4 * t * (1 - t);
    pts.push(p);
  }
  return pts;
}

// deterministic random
export function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

// flat textured face (no shading): signs, vending fronts, posters, LED boards
export function flatTex(canvas) {
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.NoColorSpace;
  tex.anisotropy = 4;
  return new THREE.MeshBasicMaterial({ map: tex });
}

export function vendingFront(inkCol, ledCol, glowCol, seed = 1) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 460;
  const g = c.getContext('2d');
  const r = rng(seed);
  g.fillStyle = inkCol; g.fillRect(0, 0, 256, 460);
  g.fillStyle = '#141018'; g.fillRect(14, 16, 228, 250);
  const cans = ['#D9402B', '#2C4C9A', '#F5C842', '#7FC8B8', '#EDE3CF', '#F08A3C'];
  for (let row = 0; row < 3; row++) for (let k = 0; k < 6; k++) {
    g.fillStyle = cans[Math.floor(r() * cans.length)];
    g.fillRect(24 + k * 36, 30 + row * 80, 26, 52);
    g.fillStyle = '#EDE3CF'; g.fillRect(24 + k * 36, 88 + row * 80, 26, 6);
  }
  g.fillStyle = '#141018'; g.fillRect(14, 280, 228, 34);
  g.fillStyle = ledCol;
  for (let i = 0; i < 20; i++) for (let j = 0; j < 4; j++) if (r() < 0.45) g.fillRect(22 + i * 11, 286 + j * 6, 7, 4);
  g.fillStyle = '#141018'; g.fillRect(70, 360, 116, 56);
  return flatTex(c);
}
