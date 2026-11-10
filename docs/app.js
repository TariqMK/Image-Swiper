// Image Swiper product page: live app previews drawn in SVG, and download links from the latest GitHub release.
"use strict";

const REPO = "TariqMK/Image-Swiper";
const ASSET = { windows: /windows-x64\.zip$/i, macos: /macos-arm64\.zip$/i, linux: /linux-x64\.tar\.gz$/i };
const OS_LABEL = { windows: "Download for Windows", macos: "Download for Mac", linux: "Download for Linux" };
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

// ---- Sample photos: painted landscapes, so the page needs no image files ----

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const PALETTES = [
  // sky top, horizon, sun, near land, water
  ["#182c5c", "#f6a066", "#ffe2aa", "#1c1e2c", true],
  ["#3c7ac4", "#b2d6ee", "#fffcec", "#264a38", false],
  ["#121630", "#784a80", "#fad0d6", "#161424", true],
  ["#6096cc", "#e8dec4", "#fff6d6", "#56623e", false],
  ["#223a60", "#f0784c", "#ffcc80", "#281a22", false],
  ["#8cb4d6", "#e6ecf0", "#ffffff", "#3c5868", true],
  ["#2c5a8c", "#9cceDE", "#fffae6", "#184246", true],
  ["#402856", "#ec9678", "#ffdcaa", "#281e34", false],
];

function mix(a, b, t) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

let uid = 0;
function scene(seed, portrait = false) {
  const r = rng(seed * 9973 + 17);
  const [top, horizon, sun, near, water] = PALETTES[seed % PALETTES.length];
  const w = portrait ? 200 : 300, h = portrait ? 300 : 200;
  const id = "s" + uid++;
  const hy = h * (0.55 + r() * 0.12);
  const sx = w * (0.25 + r() * 0.5), sy = hy * (0.5 + r() * 0.35), sr = h * 0.06;
  let shapes = "";
  for (let i = 0; i < 4; i++) {
    const depth = i / 3;
    const colour = mix(mix(horizon, top, 0.35), near, 0.35 + 0.65 * depth);
    const base = hy - h * 0.16 * (1 - depth) + (water ? h * 0.05 : h * 0.12) * depth;
    let pts = [base + (r() - 0.5) * h * 0.2, base + (r() - 0.5) * h * 0.2];
    let spread = h * (0.1 - 0.05 * depth);
    for (let k = 0; k < 6; k++) {
      spread *= 0.55;
      const next = [];
      for (let j = 0; j < pts.length - 1; j++) next.push(pts[j], (pts[j] + pts[j + 1]) / 2 + (r() - 0.5) * 2 * spread);
      next.push(pts[pts.length - 1]);
      pts = next;
    }
    const step = w / (pts.length - 1);
    const line = pts.map((y, j) => `${(j * step).toFixed(1)},${y.toFixed(1)}`).join(" ");
    shapes += `<polygon points="${line} ${w},${h} 0,${h}" fill="${colour}"/>`;
  }
  let lake = "";
  if (water) {
    const wy = hy + h * 0.1;
    lake = `<rect x="0" y="${wy.toFixed(1)}" width="${w}" height="${(h - wy).toFixed(1)}" fill="url(#${id}w)"/>` +
      `<ellipse cx="${sx.toFixed(1)}" cy="${(wy + (wy - sy) * 0.6).toFixed(1)}" rx="${(sr * 0.9).toFixed(1)}" ry="${(sr * 0.5).toFixed(1)}" fill="${sun}" opacity="0.35"/>`;
    for (let g = 0; g < 7; g++) {
      const gy = wy + (h - wy) * (0.15 + r() * 0.8), len = w * (0.02 + r() * 0.05);
      const gx = sx + (r() - 0.5) * w * 0.2;
      lake += `<rect x="${(gx - len).toFixed(1)}" y="${gy.toFixed(1)}" width="${(len * 2).toFixed(1)}" height="1" rx="0.5" fill="${sun}" opacity="0.35"/>`;
    }
  }
  return `<svg viewBox="0 0 ${w} ${h}" style="aspect-ratio:${w}/${h}" aria-hidden="true">
<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="${(hy / h).toFixed(2)}" stop-color="${horizon}"/></linearGradient>
<radialGradient id="${id}g"><stop offset="0" stop-color="${sun}" stop-opacity="0.55"/><stop offset="1" stop-color="${sun}" stop-opacity="0"/></radialGradient>
<linearGradient id="${id}w" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mix(horizon, near, 0.45)}"/><stop offset="1" stop-color="${mix(top, near, 0.6)}"/></linearGradient></defs>
<rect width="${w}" height="${h}" fill="url(#${id})"/><circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="${(sr * 3.2).toFixed(1)}" fill="url(#${id}g)"/>
<circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="${sr.toFixed(1)}" fill="${sun}"/>${shapes}${lake}</svg>`;
}

// ---- Shared helpers ----

const $ = (sel) => document.querySelector(sel);
function yearsAgo(year) {
  const n = new Date().getFullYear() - year;
  return n <= 0 ? "This year" : `${n} year${n === 1 ? "" : "s"} ago`;
}
function strip(el, count) {
  el.innerHTML = "<i></i>".repeat(count);
  return [...el.children];
}
function paintStrip(blocks, current, deleted) {
  blocks.forEach((b, i) => {
    b.className = i === current ? "current" : deleted.has(i) ? "deleted" : i < current ? "passed" : "";
  });
}
// Runs fn every ms, paused while the tab is hidden; with reduced motion, never.
function every(ms, fn) {
  if (reduceMotion) return;
  let timer = null;
  const start = () => { if (!timer) timer = setInterval(fn, ms); };
  const stop = () => { clearInterval(timer); timer = null; };
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
  if (!document.hidden) start();
}

// ---- Hero: the review loop ----

function heroDemo() {
  const COUNT = 48;
  const files = Array.from({ length: COUNT }, (_, i) => {
    const r = rng(i + 101);
    const day = 3 + Math.floor(i / 5);
    return {
      seed: i + 3,
      portrait: i % 7 === 4,
      name: `IMG_${4120 + i * 3}.jpg`,
      mb: 2.1 + r() * 4.2,
      date: { day, month: 7, year: 2019 },
    };
  });
  // A short story that repeats: keep, delete, change your mind, delete again.
  const SCRIPT = ["keep", "keep", "delete", "keep", "keep", "keep", "delete", "undo", "keep", "keep", "delete", "keep", "keep", "delete", "keep"];
  const blocks = strip($("#demo-strip"), COUNT);
  const btn = { keep: $("#demo-keep"), delete: $("#demo-delete"), undo: $("#demo-undo") };
  let index = 0, step = 0, deleted = new Set(), lastDeleted = null;

  function show() {
    const f = files[index];
    const photo = $("#demo-photo");
    photo.innerHTML = scene(f.seed, f.portrait);
    $("#demo-date").textContent = `${f.date.day} ${MONTHS[f.date.month]} ${f.date.year}`;
    $("#demo-ago").textContent = yearsAgo(f.date.year);
    $("#demo-meta").textContent = `${f.name}  ·  ${f.mb.toFixed(1)} MB  ·  Photo`;
    let freed = 0;
    deleted.forEach((i) => (freed += files[i].mb));
    $("#demo-stats").innerHTML = `${index + 1} / ${COUNT}<span class="wide">  ·  ${deleted.size} deleted  ·  ${freed.toFixed(1)} MB freed</span>`;
    btn.undo.classList.toggle("disabled", lastDeleted === null);
    paintStrip(blocks, index, deleted);
  }
  function press(name) {
    btn[name].classList.add("pressed");
    setTimeout(() => btn[name].classList.remove("pressed"), 220);
  }
  function advance() {
    const photo = $("#demo-photo");
    photo.classList.add("out");
    setTimeout(() => { show(); photo.classList.remove("out"); }, 180);
  }
  function act() {
    const action = SCRIPT[step++ % SCRIPT.length];
    press(action);
    if (action === "undo" && lastDeleted !== null) {
      deleted.delete(lastDeleted);
      index = lastDeleted;
      lastDeleted = null;
    } else if (action === "delete") {
      deleted.add(index);
      lastDeleted = index;
      index++;
    } else {
      index++;
    }
    if (index >= COUNT) { index = 0; deleted = new Set(); lastDeleted = null; }
    advance();
  }

  if (reduceMotion) {
    index = 11; deleted = new Set([2, 6, 9]); lastDeleted = 9;
  }
  show();
  every(1600, act);
}

// ---- Contact strip panel ----

function stripDemo() {
  const COUNT = 120;
  const el = $("#big-strip");
  const blocks = strip(el, COUNT);
  const r = rng(42);
  const sizes = Array.from({ length: COUNT }, () => 1.8 + r() * 4.6);
  const willDelete = Array.from({ length: COUNT }, () => r() < 0.17);
  let current = 0, deleted = new Set();

  function render() {
    paintStrip(blocks, current, deleted);
    let freed = 0;
    deleted.forEach((i) => (freed += sizes[i]));
    $("#strip-reviewed").textContent = `${current} / ${COUNT}`;
    $("#strip-deleted").textContent = deleted.size;
    $("#strip-freed").textContent = `${freed.toFixed(1)} MB`;
  }
  function tick() {
    if (willDelete[current]) deleted.add(current);
    current++;
    if (current >= COUNT) { current = 0; deleted = new Set(); }
    render();
  }
  el.addEventListener("click", (e) => {
    const box = el.getBoundingClientRect();
    current = Math.max(0, Math.min(COUNT - 1, Math.floor(((e.clientX - box.left) / box.width) * COUNT)));
    render();
  });
  current = 46;
  for (let i = 0; i < current; i++) if (willDelete[i]) deleted.add(i);
  render();
  every(1000, tick);
}

// ---- On This Day panel ----

function otdDemo() {
  const AGES = [[2, 5, 8], [1, 4, 9], [3, 6, 11], [2, 7, 10]];
  const prints = $("#otd-prints");
  let offset = 0;

  function render() {
    const day = new Date();
    day.setDate(day.getDate() + offset);
    $("#otd-day").textContent = `${day.getDate()} ${MONTHS[day.getMonth()].slice(0, 3)}`;
    const ages = AGES[((offset % AGES.length) + AGES.length) % AGES.length];
    prints.innerHTML = ages.map((age, i) => {
      const year = new Date().getFullYear() - age;
      return `<figure class="print">${scene(day.getDate() * 7 + i * 3 + Math.abs(offset))}
        <figcaption><span class="when">${day.getDate()} ${MONTHS[day.getMonth()]} ${year}</span><span class="ago">${yearsAgo(year)}</span></figcaption></figure>`;
    }).join("");
  }
  const random = $("#otd-random");
  let jumped = false;
  render();
  every(4000, () => {
    // Step back through recent days, press Random Day once, then return to today.
    const jump = offset === -3 && !jumped;
    if (jump) {
      random.classList.add("press");
      setTimeout(() => random.classList.remove("press"), 500);
    }
    prints.classList.add("out");
    setTimeout(() => {
      if (jump) {
        offset = -(20 + Math.floor(Math.random() * 300));
        jumped = true;
      } else if (offset <= -3) {
        offset = 0;
        jumped = false;
      } else {
        offset -= 1;
      }
      render();
      prints.classList.remove("out");
    }, 240);
  });
}

// ---- Section strips: the teal block moves one step further down the page ----

function eyebrows() {
  document.querySelectorAll(".eyebrow").forEach((el) => {
    const step = Number(el.dataset.step);
    el.innerHTML = Array.from({ length: 7 }, (_, i) =>
      `<i class="${i + 1 === step ? "current" : i + 1 < step ? "passed" : ""}"></i>`).join("");
  });
}

// ---- Downloads ----

function detectOS() {
  const ua = navigator.userAgent;
  if (/Android|iPhone|iPad|iPod/i.test(ua)) return null;
  const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || ua;
  if (/Win/i.test(platform)) return "windows";
  if (/Mac/i.test(platform)) return "macos";
  if (/Linux|X11/i.test(platform)) return "linux";
  return null;
}

async function downloads() {
  const os = detectOS();
  if (os) {
    $("#hero-download-label").textContent = OS_LABEL[os];
    document.querySelector(`.card[data-os="${os}"]`).classList.add("match");
  }
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) return;
    const rel = await res.json();
    for (const [key, pattern] of Object.entries(ASSET)) {
      const asset = (rel.assets || []).find((a) => pattern.test(a.name));
      if (!asset) continue;
      const card = document.querySelector(`.card[data-os="${key}"]`);
      card.href = asset.browser_download_url;
      card.querySelector(".size").textContent = `${(asset.size / 1048576).toFixed(0)} MB`;
      if (key === os) $("#hero-download").href = asset.browser_download_url;
    }
    const tag = rel.tag_name;
    const date = new Date(rel.published_at);
    const when = `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
    $("#hero-meta").textContent = `${tag} · Free · Windows, macOS and Linux · Works offline`;
    $("#download-lede").textContent = `${tag}, released ${when}. Free. Extract the download to a folder you can write to, such as Documents, and keep everything in it together. Nothing else to install.`;
    document.querySelectorAll("[data-version]").forEach((el) => (el.textContent = tag.replace(/^v/, "")));
  } catch (err) {
    // Offline, rate-limited or no release yet: every link already points at the Releases page.
  }
}

eyebrows();
heroDemo();
stripDemo();
otdDemo();
downloads();
