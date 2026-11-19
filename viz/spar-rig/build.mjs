import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../kit/iso-kit.mjs";
import { kitScript } from "../scripts/inline-kit.mjs";

// SPAR proving range — RED fires probes, BLUE wall carries the patches,
// the JUDGE dial reads the exercise score. Every number below is true:
// they come from out/spar-juice/spar.json (run of 2026-11-17).

const HERE = dirname(fileURLToPath(import.meta.url));
const theme = process.argv.includes("--light") ? "light" : "dark";

const WIDTH = 660;
const HEIGHT = 420;

// ----- true numbers from the spar run -----
const SCORES = { total: 83, attack: 75, defense: 92 };
const FINDINGS = [
  { short: "service fingerprint", sev: "info", fix: "p1 loopback + allowlist" },
  { short: "wildcard CORS", sev: "low", fix: "p1 CORS allowlist" },
  { short: "missing CSP", sev: "low", fix: "p1 deploy CSP" },
  { short: "/ftp disclosed", sev: "info", fix: "p2 close /ftp" },
];

// ----- world layout (x: turret -> wall -> target, z: up) -----
const PLATE = { x: -170, y: -92, w: 380, d: 184, r: 8 };
const PLATE_H = 12;
const FOOT_H = 5;

// target kiosk (Juice Shop storefront) at the +x end, face toward the turret
const SHOP = { x: 96, y: -40, w: 60, d: 80, r: 3 };
const SHOP_H = 58;
const AWNING_Z = 44;
const HOLE_X = SHOP.x;               // face plane facing the turret
const HOLES = [
  { y: -26, z: 30 }, { y: -8, z: 24 }, { y: 10, z: 30 }, { y: 28, z: 22 },
];

// BLUE armor wall, mid-range, standing across y
const WALL = { x: 18, y: -46, w: 7, d: 92, r: 1.5 };
const WALL_Z0 = 8;
const WALL_H = 72;
const PATCH_X = WALL.x - 1.6;        // face toward the turret
const PATCHES = [
  { y: -34, z: 52 }, { y: -16, z: 60 }, { y: 2, z: 52 }, { y: 20, z: 44 }, { y: 36, z: 58 },
];

// RED turret at the -x end
const TBASE = { x: -156, y: -34, w: 46, d: 68, r: 4 };
const TBASE_H = 10;
const PIVOT = [-136, 0];
const BARREL_Z = 46;
const MUZZLE_X = -96;
const RACK = { x: -112, y: 26, w: 30, d: 10, r: 1 };

// JUDGE scoreboard, back right of the kiosk
const JPOST = [110, 64];
const JDIAL = [110, 64];
const JDIAL_Z = 74;
const JDIAL_R = 23;

const P = k.fitProjection(
  [
    ...k.boxCorners(PLATE, -PLATE_H - FOOT_H, 0),
    [PIVOT[0], PIVOT[1], BARREL_Z + 8],
    [SHOP.x + SHOP.w, 0, AWNING_Z + 14],
    [JDIAL[0] + JDIAL_R, JDIAL[1], JDIAL_Z + JDIAL_R + 4],
    [WALL.x + 4, WALL.y + WALL.d, WALL_Z0 + WALL_H],
  ],
  WIDTH,
  HEIGHT,
  { pad: 26, azimuth: 44 },
);

const at = (point) => k.iso(point, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

/* ---------------- base plate ---------------- */
function plate() {
  const out = [`<path class="iso-halo" d="${k.haloOf(PLATE, -PLATE_H - FOOT_H, PLATE_H, P)}"/>`];
  for (const [x, y] of byDepth(k.corners(PLATE, 22))) {
    out.push(S(k.cylinder(x, y, 7, -PLATE_H - FOOT_H, 1.6, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.4, -PLATE_H - FOOT_H + 1.6, FOOT_H - 1.6, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(PLATE, -PLATE_H, PLATE_H, P, 8, 1.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "mid" }));
  const screws = k.corners(PLATE, 10);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  const strip = { x: -150, y: PLATE.y + PLATE.d - 15, w: 310, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.8, 0.6, [2, 3.6], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  return out.join("");
}

/* ---------------- target kiosk ---------------- */
function kiosk() {
  const out = [];
  out.push(S(k.slabOf(SHOP, 0, 8, P, 3, 0.6), { tone: "mid" }));
  // corner posts
  for (const [x, y] of [[SHOP.x + 4, SHOP.y + 4], [SHOP.x + 4, SHOP.y + SHOP.d - 4]]) {
    out.push(S(k.cylinder(x, y, 3.2, 8, SHOP_H, P, 20), { tone: "mid", crease: "none" }));
  }
  // face wall toward the turret, with the four finding holes — the subject is lit
  const face = { x: HOLE_X - 3, y: SHOP.y + 6, w: 3, d: SHOP.d - 12, r: 1 };
  out.push(S(k.slabOf(face, 10, SHOP_H - 6, P, 1.5, 0.5), { tone: "hi", crease: "lo" }));
  out.push(L(k.planOutline(k.insetPlan(face, 1.2), SHOP_H - 6, P), { tone: "mid" }));
  for (let sz = 22; sz < SHOP_H - 10; sz += 12) {
    out.push(L(k.lineOnTop([HOLE_X - 3, SHOP.y + 8], [HOLE_X - 3, SHOP.y + SHOP.d - 8], sz, P), { tone: "lo" }));
  }
  // counter shelf along the face bottom + two bottles
  out.push(S(k.slabOf({ x: SHOP.x - 5, y: SHOP.y + 6, w: 5, d: SHOP.d - 12, r: 1 }, 10, 16, P, 1.5, 0.4), { tone: "mid" }));
  for (const [by, bz] of [[SHOP.y + 16, 18], [SHOP.y + 40, 18]]) {
    out.push(S(k.cylinder(HOLE_X - 3.5, by, 1.8, 16, bz, P, 16), { tone: "hi", crease: "none" }));
  }
  FINDINGS.forEach((f, i) => {
    const h = HOLES[i];
    const hole = { x: HOLE_X - 4.2, y: h.y - 5, w: 4.2, d: 10, r: 1 };
    const paths = [
      S(k.slabOf(hole, h.z - 6, h.z + 6, P, 1, 0.4), { tone: "lo", crease: "none" }),
      L(k.planOutline(hole, h.z + 6, P), { tone: "mid" }),
      D([at([HOLE_X - 1.5, h.y, h.z])], { size: 0.5, tone: "mid" }),
    ];
    out.push(`<g data-part="hole${i}">${paths.join("")}</g>`);
  });
  // awning
  out.push(S(k.slabOf({ x: SHOP.x - 6, y: SHOP.y - 4, w: SHOP.w + 10, d: SHOP.d + 8, r: 2 }, AWNING_Z, AWNING_Z + 5, P, 4, 0.8), { tone: "hi", crease: "lo" }));
  out.push(L(k.planOutline({ x: SHOP.x - 6, y: SHOP.y - 4, w: SHOP.w + 10, d: SHOP.d + 8, r: 2 }, AWNING_Z + 5, P, 2), { tone: "mid" }));
  for (let sy = SHOP.y; sy <= SHOP.y + SHOP.d; sy += 8) {
    out.push(L(k.lineOnTop([SHOP.x - 6, sy], [SHOP.x + SHOP.w + 4, sy], AWNING_Z + 5.2, P), { tone: "lo" }));
  }
  // sign plate on the roof
  out.push(S(k.slabOf({ x: SHOP.x + 14, y: -14, w: 3, d: 34, r: 1 }, AWNING_Z + 5, AWNING_Z + 17, P, 1.5, 0.4), { tone: "hi", crease: "lo" }));
  out.push(L(k.planOutline({ x: SHOP.x + 14, y: -14, w: 3, d: 34, r: 1 }, AWNING_Z + 17, P, 1), { tone: "faint" }));
  return out.join("");
}

/* ---------------- BLUE armor wall ---------------- */
function wall() {
  const out = [];
  for (const y of [WALL.y + 5, WALL.y + WALL.d - 5]) {
    out.push(S(k.cylinder(WALL.x + WALL.w / 2, y, 3.4, 0, WALL_Z0 + 2, P, 20), { tone: "mid", crease: "none" }));
  }
  out.push(S(k.slabOf(WALL, WALL_Z0, WALL_Z0 + WALL_H, P, 1.5, 0.5), { tone: "mid" }));
  out.push(L(k.planOutline(WALL, WALL_Z0 + WALL_H, P, 1), { tone: "mid" }));
  for (let wy = WALL.y + 8; wy < WALL.y + WALL.d; wy += 12) {
    out.push(L(k.lineOnTop([WALL.x + 1, wy], [WALL.x + 1, wy + 6], WALL_Z0 + WALL_H, P), { tone: "lo" }));
  }
  // five patch plates on the turret-facing side, one per defense action
  PATCHES.forEach((p, i) => {
    const plate = { x: PATCH_X - 3, y: p.y - 6.5, w: 3, d: 13, r: 1 };
    const paths = [
      S(k.slabOf(plate, p.z - 8, p.z + 8, P, 1, 0.4), { tone: "hi", crease: "lo" }),
      L(k.planOutline(plate, p.z + 8, P, 0.6), { tone: "mid" }),
      D([at([PATCH_X - 1.5, p.y - 4, p.z + 6]), at([PATCH_X - 1.5, p.y + 4, p.z + 6])], { size: 0.42 }),
    ];
    out.push(`<g data-part="patch${i}">${paths.join("")}</g>`);
  });
  // hinges on the back side (the wall lifts to reveal the holes)
  for (const y of [WALL.y + 12, WALL.y + WALL.d - 12]) {
    out.push(S(k.cylinder(WALL.x + WALL.w / 2, y, 2.2, WALL_Z0 + WALL_H, WALL_Z0 + WALL_H + 4, P, 16), { tone: "lo", crease: "none" }));
  }
  return out.join("");
}

/* ---------------- RED turret ---------------- */
function turret() {
  const out = [];
  out.push(S(k.slabOf(TBASE, 0, TBASE_H, P, 4, 0.6), { tone: "mid" }));
  out.push(D([[TBASE.x + 6, TBASE.y + 6], [TBASE.x + TBASE.w - 6, TBASE.y + 6], [TBASE.x + 6, TBASE.y + TBASE.d - 6], [TBASE.x + TBASE.w - 6, TBASE.y + TBASE.d - 6]].map(([x, y]) => at([x, y, TBASE_H])), { size: 0.42, tone: "lo" }));
  out.push(S(k.cylinder(PIVOT[0], PIVOT[1], 7, TBASE_H, TBASE_H + 6, P, 28), { tone: "mid" }));
  out.push(L(k.knurl(PIVOT[0], PIVOT[1], 7, TBASE_H, TBASE_H + 6, 30, P), { tone: "lo" }));
  // barrel: a boxy shroud + muzzle ring, pointing at the kiosk face
  out.push(S(k.slabOf({ x: PIVOT[0] - 2, y: -7, w: MUZZLE_X - PIVOT[0] + 6, d: 14, r: 2 }, BARREL_Z - 7, BARREL_Z + 7, P, 3, 0.6), { tone: "hi", crease: "lo" }));
  out.push(S(k.cylinder(MUZZLE_X, 0, 8.5, BARREL_Z - 9, BARREL_Z + 9, P, 32), { tone: "mid" }));
  out.push(L(k.ring(MUZZLE_X, 0, 8.5, BARREL_Z + 9, P, 32), { tone: "mid" }));
  // crank knob
  const knob = [PIVOT[0] - 4, TBASE.y + TBASE.d + 6];
  out.push(S(k.cylinder(knob[0], knob[1], 4.4, TBASE_H, TBASE_H + 7, P, 24), { tone: "mid" }));
  out.push(L(k.knurl(knob[0], knob[1], 4.4, TBASE_H, TBASE_H + 7, 22, P), { tone: "lo" }));
  // dart rack, three spares
  out.push(S(k.slabOf(RACK, 0, 3, P, 1.5, 0.4), { tone: "lo", crease: "none" }));
  for (let i = 0; i < 3; i++) {
    const x = RACK.x + 5 + i * 9;
    out.push(S(k.slabOf({ x, y: RACK.y + 2, w: 6, d: 5, r: 1 }, 3, 9, P, 1.5, 0.4), { tone: "hi", crease: "none" }));
    out.push(D([at([x + 3, RACK.y + 4.5, 9])], { size: 0.45 }));
  }
  return out.join("");
}

/* ---------------- JUDGE scoreboard ---------------- */
function judge() {
  const out = [];
  out.push(S(k.cylinder(JPOST[0], JPOST[1], 4, 0, 36, P, 24), { tone: "mid", crease: "none" }));
  out.push(S(k.slabOf({ x: JPOST[0] - 10, y: JPOST[1] - 5, w: 20, d: 10, r: 2 }, 36, 42, P, 3, 0.5), { tone: "mid" }));
  out.push(S(k.cylinder(JPOST[0], JPOST[1], 3, 42, JDIAL_Z - JDIAL_R, P, 20), { tone: "mid", crease: "none" }));
  out.push(S(k.cylinder(JDIAL[0], JDIAL[1], JDIAL_R, JDIAL_Z, 9, P, 64, 0.8), { tone: "hi", crease: "lo" }));
  out.push(L(k.ring(JDIAL[0], JDIAL[1], JDIAL_R - 2.2, JDIAL_Z + 9, P, 64), { tone: "lo" }));
  const ticks = k.radialTicks(JDIAL[0], JDIAL[1], JDIAL_R - 3, 36, 4, JDIAL_Z + 9, [1.3, 3], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));
  // the two true ticks: attack 75 and defense 92, plus the score mark 83
  for (const [share, tone] of [[0, "lo"], [1, "lo"], [0.5, "hi"]]) {
    const angle = (0.33 + share * 0.16) * Math.PI * 2;
    const x1 = JDIAL[0] + Math.sin(angle) * (JDIAL_R - 6), y1 = JDIAL[1] - Math.cos(angle) * (JDIAL_R - 6);
    const x2 = JDIAL[0] + Math.sin(angle) * (JDIAL_R - 1), y2 = JDIAL[1] - Math.cos(angle) * (JDIAL_R - 1);
    out.push(L(k.lineOnTop([x1, y1], [x2, y2], JDIAL_Z + 9, P), { tone, }));
  }
  out.push(k.faceTextSvg(k.topMatrix([JDIAL[0] - 6, JDIAL[1] + 3], JDIAL_Z + 9, P, "x"), "75", { size: 2.2, tone: "lo", anchor: "middle" }));
  out.push(k.faceTextSvg(k.topMatrix([JDIAL[0] + 6, JDIAL[1] + 3], JDIAL_Z + 9, P, "x"), "92", { size: 2.2, tone: "lo", anchor: "middle" }));
  out.push(S(k.slabOf({ x: JDIAL[0] + JDIAL_R - 1, y: JDIAL[1] - 2.4, w: 5, d: 4.8, r: 1.2 }, JDIAL_Z + 2, 5, P, 3), { tone: "mid" }));
  out.push(L(k.ring(JDIAL[0], JDIAL[1], 1.6, JDIAL_Z + 9, P, 16), { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([JDIAL[0], JDIAL[1] + 10], JDIAL_Z + 9, P, "x"), "SPAR 83", { size: 2.6, tone: "lo", anchor: "middle" }));
  return out.join("");
}

/* needle: share 0 = attack tick (75), 1 = defense tick (92); total 83 sits between */
const needleAt = (share) => {
  const turn = 0.33 + share * 0.16;
  const angle = turn * Math.PI * 2;
  const [x, y] = JDIAL;
  return k.lineOnTop([x - Math.sin(angle) * 3.4, y + Math.cos(angle) * 3.4], [x + Math.sin(angle) * (JDIAL_R - 4), y - Math.cos(angle) * (JDIAL_R - 4)], JDIAL_Z + 9.2, P);
};

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label:
    "A proving range for a red/blue security spar. A RED turret fires harmless probe darts down-range at a target kiosk (the web app); a BLUE armor wall between them carries one bolted patch plate per defense action; a JUDGE scoreboard dial reads the exercise score, 83, between the attack tick 75 and the defense tick 92. Lifting the wall reveals the four finding holes punched in the kiosk face.",
  body: [
    plate(),
    kiosk(),
    wall(),
    turret(),
    judge(),
    `<g data-part="dart" opacity="0.95"><path class="iso-halo" d="${k.haloOf({ x: MUZZLE_X - 4, y: -3.5, w: 9, d: 7, r: 1 }, BARREL_Z - 3.5, 7, P)}" style="filter:blur(3px)"/>${S(k.slabOf({ x: MUZZLE_X - 3, y: -3, w: 8, d: 6, r: 1 }, BARREL_Z - 3, BARREL_Z + 3, P, 1, 0.3), { tone: "hi", lit: true, crease: "none" })}</g>`,
    `<path data-part="needle" class="iso-line" data-tone="lit" data-free="start" d="${needleAt(0.45)}" style="stroke-width:1.5"/>`,
  ],
});

const live = `
const P = ${JSON.stringify(P)};
const HOLES = ${JSON.stringify(HOLES)};
const PATCHES = ${JSON.stringify(PATCHES)};
const SCORES = ${JSON.stringify(SCORES)};
const FINDINGS = ${JSON.stringify(FINDINGS)};
const MUZZLE_X = ${MUZZLE_X}, BARREL_Z = ${BARREL_Z}, HOLE_X = ${HOLE_X}, PATCH_X = ${PATCH_X};
const JDIAL = ${JSON.stringify(JDIAL)}, JDIAL_Z = ${JDIAL_Z}, JDIAL_R = ${JDIAL_R};
const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const dart = svg.querySelector('[data-part="dart"]');
const needle = svg.querySelector('[data-part="needle"]');
const readout = document.querySelector("[data-readout]");
const still = matchMedia("(prefers-reduced-motion: reduce)");
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const needleAt = ${needleAt.toString().replace("k.lineOnTop", "lineOnTop")};
const patchEls = PATCHES.map((p, i) => svg.querySelector('[data-part="patch' + i + '"]'));
const holeEls = FINDINGS.map((f, i) => svg.querySelector('[data-part="hole' + i + '"]'));
let idx = 0, target = 0, shown = 0, clock = 0, last = 0, touring = true, visible = false, idleTimer = 0, frame = 0;
function draw() {
  const hole = HOLES[idx];
  const t = clamp(shown, 0, 1);
  // dart flies from the muzzle to the hole of the selected finding (relative delta)
  const dx = ((HOLE_X - 4.2) - (MUZZLE_X - 3)) * t;
  const dy = (hole.y - (-3)) * t;
  const dz = ((hole.z - 3) - (BARREL_Z - 3)) * t;
  dart.setAttribute("transform", translateAlong(P, [dx, dy, dz]));
  dart.setAttribute("opacity", t > 0.02 && t < 0.98 ? "0.95" : "0.15");
  patchEls.forEach((el, i) => {
    const lift = i === idx ? 3.5 : 0;
    el.setAttribute("transform", translateAlong(P, [PATCH_X + lift, 0, 0]));
    el.setAttribute("opacity", i === idx ? "1" : "0.82");
  });
  holeEls.forEach((el, i) => el && el.setAttribute("opacity", i === idx ? "1" : "0.55"));
  needle.setAttribute("d", needleAt(clamp(0.35 + 0.65 * (SCORES.total - SCORES.attack) / (SCORES.defense - SCORES.attack) * (0.6 + 0.4 * t), 0, 1)));
  const f = FINDINGS[idx];
  const text = "finding " + (idx + 1) + "/4 · " + f.short + " (" + f.sev + ") · " + f.fix;
  if (readout.textContent !== text) readout.textContent = text;
  stage.setAttribute("aria-valuenow", String(idx + 1));
  stage.setAttribute("aria-valuetext", text);
}
function tick(now) {
  const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
  last = now;
  const calm = still.matches;
  if (touring) { clock += dt; if (clock > 2.6) { clock = 0; idx = (idx + 1) % 4; } }
  shown = calm ? target : shown + (target - shown) * (1 - Math.exp(-dt / 0.24));
  if (Math.abs(target - shown) < 0.01) shown = target;
  draw();
  const settled = !touring && Math.abs(target - shown) < 0.01;
  frame = visible && !settled ? requestAnimationFrame(tick) : 0;
}
const run = () => { if (!frame && visible) { last = 0; frame = requestAnimationFrame(tick); } };
const steer = (next) => { touring = false; idx = next; target = 1; shown = 0; clearTimeout(idleTimer); idleTimer = setTimeout(() => { touring = !still.matches; clock = 0; run(); }, 4200); draw(); run(); };
new IntersectionObserver((entries) => { visible = entries[entries.length - 1].isIntersecting; if (visible) run(); }, { rootMargin: "120px 0px" }).observe(stage);
if (still.matches) touring = false;
stage.addEventListener("pointermove", (event) => {
  const box = svg.getBoundingClientRect();
  const share = clamp((event.clientX - box.left) / box.width, 0, 0.999);
  steer(Math.floor(share * 4));
});
stage.addEventListener("click", () => { shown = 0; target = 1; touring = false; run(); });
stage.addEventListener("keydown", (event) => {
  if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); steer((idx + 1) % 4); }
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); steer((idx + 3) % 4); }
});
draw();
`;

const body = k.plateHtml({
  fig: "Fig 1",
  title: "SPAR proving range — red/blue security exercise",
  hint: "Hover to pick the finding a probe hits · click to fire",
  readout: "finding 1/4 · service fingerprint (info)",
  keys: [
    { mark: "lit", label: "Probe dart, active patch plate and judge needle: what moves" },
    { mark: "raised", label: "Target kiosk face with four finding holes; five bolted patch plates on the armor wall" },
  ],
  caption:
    "A proving range for the red/blue exercise of 2026-11-17 against the local Juice Shop. The RED turret (glm-5.3-flash) fired four read-only probes down-range; each found a hole in the target (service fingerprint, wildcard CORS, missing CSP, /ftp disclosure). The BLUE wall (minimax-m3.1-flash) carries five patch plates, one per defense action, hung over those holes; the JUDGE dial (nemotron-3.5-lightning) reads 83, between the attack tick 75 and the defense tick 92. Hover to choose which finding the dart strikes; the matching patch lifts to show it covers that hole.",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="Red/blue spar range: arrow keys step through the four findings" aria-valuemin="1" aria-valuemax="4" aria-valuenow="1">${svg}</div>`,
});

writeFileSync(
  join(HERE, theme === "light" ? "spar-rig-light.html" : "spar-rig.html"),
  k.pageHtml({ title: "SPAR proving range", theme, body, script: kitScript() + live }),
);
console.log("wrote", theme === "light" ? "spar-rig-light.html" : "spar-rig.html");
