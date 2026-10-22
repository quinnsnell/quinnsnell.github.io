// Screenshot parts of the guide with headless Chrome (no npm packages needed).
// Used for the slide PNGs and for checking the page by eye.
//
//   node shoot.mjs slides                  diagrams/<name>.png, each drawing in the sketch look, 2x
//   node shoot.mjs check <outdir> [w] [theme]   one PNG per section at width w (default 1280), light|dark
//
// Set CHROME=/path/to/chrome to pick the browser.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [mode = "slides", outArg, widthArg, theme = "light"] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "shoot-"))}`, "about:blank"], { stdio: "ignore" });

let ws, id = 0;
const pending = new Map(), errors = [];
async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) { ws = new WebSocket(page.webSocketDebuggerUrl); break; }
    } catch { /* not up yet */ }
    await sleep(200);
  }
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.text);
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") errors.push(JSON.stringify(msg.params.args));
  };
}
function send(method, params = {}) {
  return new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
}
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result?.result?.value;
}
async function shot(rect, file, scale = 1) {
  const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
    clip: { ...rect, scale } });
  writeFileSync(file, Buffer.from(r.result.data, "base64"));
}

try {
  await connect();
  await send("Runtime.enable");
  await send("Page.enable");
  const width = Number(widthArg) || (mode === "slides" ? 1280 : 1280);
  await send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
  await send("Page.navigate", { url: "file://" + resolve(HERE, "index.html") });
  await sleep(2500);

  if (mode === "slides") {
    const out = join(HERE, "diagrams");
    mkdirSync(out, { recursive: true });
    const figs = await evaluate(`[...document.querySelectorAll('.fig-box')].map(f => {
      f.closest('section').querySelector('details')?.setAttribute('open','');
      const r = f.getBoundingClientRect();
      return {name: f.innerHTML.match(/<!--svg:([a-z]+)-->/)[1],
              r: {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}};
    })`);
    for (const f of figs) await shot(f.r, join(out, `${f.name}.png`), 2);
    console.log(`wrote ${figs.length} PNGs to diagrams/`);
  } else {
    const out = resolve(outArg || "shots");
    mkdirSync(out, { recursive: true });
    const H = await evaluate("document.documentElement.scrollHeight");
    const W = await evaluate("document.documentElement.scrollWidth");
    console.log(`page ${W}x${H} (viewport ${width}); sideways scroll: ${W > width}`);
    for (let y = 0, n = 1; y < H; y += 1400, n++) {
      await shot({ x: 0, y, width, height: Math.min(1400, H - y) }, join(out, `p${String(n).padStart(2, "0")}.png`));
    }
  }
  console.log(errors.length ? "console errors:\n" + errors.join("\n") : "no console errors");
} finally {
  ws?.close();
  chrome.kill();
}
