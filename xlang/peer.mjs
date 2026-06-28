// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Brama kontraktowa w JavaScripcie. NIE definiuje kontraktów — czyta ten sam neutralny
// contracts.json, co Python i Go. Dowód architektury "jedno źródło, N czytników":
// walidator (~80 linii) i asercje konformansu są identyczne co do logiki, bo operują na
// neutralnych danych, a nie na obiektach konkretnego języka.
//
//   produce <route>        — wypisz złotą kopertę ok jako JSON      (proces producenta)
//   consume <prod> <cons>  — wczytaj JSON ze stdin, zbuduj wejście konsumenta, zwaliduj
//   conform               — uruchom asercje konformansu na całym contracts.json

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline";

const HERE = dirname(fileURLToPath(import.meta.url));
const DOC = JSON.parse(readFileSync(join(HERE, "contracts.json"), "utf8"));
const CONTRACTS = DOC.contracts;
const WIRES = DOC.wires;

class ContractViolation extends Error {}

// ── walidator mini-języka schematu (port 1:1 z Pythona) ──────────────────────
const TYPES = {
  str: (v) => typeof v === "string",
  int: (v) => typeof v === "number" && Number.isInteger(v),   // JSON: liczba całkowita; bool nie jest number
  num: (v) => typeof v === "number",
  bool: (v) => typeof v === "boolean",
  obj: (v) => v !== null && typeof v === "object" && !Array.isArray(v),
  list: (v) => Array.isArray(v),
  any: () => true,
};

function constValue(token) {
  const lit = token.slice("const:".length);
  if (lit === "true") return true;
  if (lit === "false") return false;
  return lit;
}

function check(schema, value, where = "") {
  if (typeof schema === "string" && schema.startsWith("?")) {
    if (value === null || value === undefined) return;
    check(schema.slice(1), value, where);
    return;
  }
  if (schema && typeof schema === "object" && !Array.isArray(schema)
      && Object.keys(schema).length === 1 && "oneOf" in schema) {
    const errs = [];
    for (let i = 0; i < schema.oneOf.length; i++) {
      try { check(schema.oneOf[i], value, where); return; }
      catch (e) { errs.push(`wariant ${i}: ${e.message}`); }
    }
    throw new ContractViolation(`${where || "<root>"}: nie pasuje do żadnego wariantu oneOf [${errs.join("; ")}]`);
  }
  if (schema && typeof schema === "object" && !Array.isArray(schema)) {
    if (value === null || typeof value !== "object" || Array.isArray(value))
      throw new ContractViolation(`${where || "<root>"}: oczekiwano obiektu`);
    for (const [key, sub] of Object.entries(schema)) {
      const optional = typeof sub === "string" && sub.startsWith("?");
      const loc = where ? `${where}.${key}` : key;
      if (!(key in value)) {
        if (optional) continue;
        throw new ContractViolation(`${loc}: brak wymaganego klucza`);
      }
      check(sub, value[key], loc);
    }
    return;
  }
  if (Array.isArray(schema)) {
    if (!Array.isArray(value)) throw new ContractViolation(`${where || "<root>"}: oczekiwano listy`);
    if (schema.length) value.forEach((it, i) => check(schema[0], it, `${where}[${i}]`));
    return;
  }
  const s = schema;
  if (s.startsWith("const:")) {
    const expected = constValue(s);
    if (value !== expected) throw new ContractViolation(`${where}: oczekiwano literału ${JSON.stringify(expected)}, jest ${JSON.stringify(value)}`);
    return;
  }
  if (s.startsWith("enum:")) {
    const allowed = s.slice("enum:".length).split("|");
    if (!allowed.includes(value)) throw new ContractViolation(`${where}: ${JSON.stringify(value)} spoza enum ${JSON.stringify(allowed)}`);
    return;
  }
  const test = TYPES[s];
  if (!test) throw new ContractViolation(`${where}: nieznany token schematu ${JSON.stringify(s)}`);
  if (!test(value)) throw new ContractViolation(`${where}: oczekiwano ${s}, jest ${typeof value} (${JSON.stringify(value)})`);
}

// ── kompozycja: budowa wejścia konsumenta z koperty producenta ───────────────
function dig(value, dotted) {
  let cur = value;
  for (const seg of dotted.split(".")) {
    if (Array.isArray(cur) && /^\d+$/.test(seg)) cur = cur[Number(seg)];
    else if (cur && typeof cur === "object" && seg in cur) cur = cur[seg];
    else throw new Error(`${dotted}: brak segmentu ${seg}`);
  }
  return cur;
}

function findWire(producer, consumer) {
  const w = WIRES.find((w) => w.producer === producer && w.consumer === consumer);
  if (!w) throw new Error(`brak krawędzi ${producer} -> ${consumer}`);
  return w;
}

function wirePayload(wire, env) {
  const out = {};
  for (const [field, path] of Object.entries(wire.mapping)) {
    try { out[field] = dig(env, path); } catch { /* źródło nieobecne w tym wariancie — pomiń */ }
  }
  return out;
}

function consumerInputCheck(consumer, payload, wire) {
  const inp = CONTRACTS[consumer].inp;
  const required = new Set(Object.entries(inp).filter(([, v]) => !(typeof v === "string" && v.startsWith("?"))).map(([k]) => k));
  const carried = new Set(Object.keys(wire.mapping));
  const problems = [];
  const requiredSubsetCarried = [...required].every((k) => carried.has(k));
  if (requiredSubsetCarried) {
    const missing = [...required].filter((k) => !(k in payload));
    if (missing.length) problems.push(`pełny handoff, ale wariant producenta nie dostarczył: ${JSON.stringify(missing)}`);
    try { check(inp, payload, "consumer.inp"); } catch (e) { problems.push(e.message); }
    return ["full", problems];
  }
  for (const field of [...carried].filter((k) => k in payload).sort()) {
    const sub = inp[field];
    try { check(sub, payload[field], `consumer.inp.${field}`); }
    catch (e) { problems.push(e.message); }
  }
  return ["partial", problems];
}

// ── asercje konformansu (te same co w pytest, na neutralnych danych) ──────────
function conform() {
  let failures = 0;
  const fail = (msg) => { console.error(`  FAIL ${msg}`); failures++; };
  for (const [route, c] of Object.entries(CONTRACTS)) {
    if ((route.includes("/query/")) !== (c.effect === "query")) fail(`${route}: efekt nie zgadza się z czasownikiem URI`);
    if (c.reversible) {
      if (!CONTRACTS[c.inverseRoute]) fail(`${route}: inverseRoute ${c.inverseRoute} nie istnieje`);
      else if (CONTRACTS[c.inverseRoute].inverseRoute !== route) fail(`${route} <-> ${c.inverseRoute} nie jest wzajemne`);
    }
    for (let i = 0; i < c.examples.length; i++) {
      const ex = c.examples[i];
      try { check(c.inp, ex.payload, `${route}#ex${i}.payload`); } catch (e) { fail(e.message); }
      if (ex.result.ok) { try { check(c.out, ex.result, `${route}#ex${i}.result`); } catch (e) { fail(e.message); } }
      if (c.reversible && ex.result.ok && "inverse" in ex.result) {
        const args = (ex.result.inverse || {}).args || {};
        try { check(CONTRACTS[c.inverseRoute].inp, args, `${route}#ex${i}.inverse.args -> ${c.inverseRoute}`); }
        catch (e) { fail(e.message); }
      }
    }
  }
  const n = Object.keys(CONTRACTS).length;
  if (failures === 0) console.log(`  OK: ${n} kontraktów konformuje (walidator JS, wspólny contracts.json)`);
  return failures === 0 ? 0 : 1;
}

// ── CLI ──────────────────────────────────────────────────────────────────────
function okExample(route) {
  const ex = CONTRACTS[route].examples.find((e) => e.result.ok);
  if (!ex) throw new Error(`${route}: brak złotej koperty ok`);
  return ex.result;
}

function cloneOkExample(route) {
  return JSON.parse(JSON.stringify(okExample(route)));
}

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString("utf8");
}

// ── prawdziwy handler trasy (stub) — node odpytywany przez zewnętrzny driver ──
function handle(route, payload, lie) {
  payload = payload || {};
  switch (route) {
    case "screen/query/capture":
      return { ok: true, connector: "kvm", action: "capture", kind: "screenshot",
        path: "/home/u/.urirun/artifacts/s.png", bytes: 204931, fullSize: [2560, 1440], via: "js-serve" };
    case "abs/command/click": {
      const sw = payload.sw ?? 1920, sh = payload.sh ?? 1080;
      const screen = lie ? [String(sw), String(sh)] : [sw, sh]; // --lie: int→string na drucie
      return { ok: true, connector: "kvm", action: "click-abs", screen,
        did: `click@(${payload.x ?? 0},${payload.y ?? 0})` };
    }
    case "window/command/close": {
      const snap = { url: "https://example.test/x", scrollX: 0, scrollY: 240, forms: [], id: payload.id ?? "active" };
      return { ok: true, connector: "kvm", action: "window-close", did: `close(${snap.id})`,
        reversible: true, snapshot: snap, inverse: { path: "window/command/restore", args: { snapshot: snap } } };
    }
    case "window/command/restore": {
      const snap = payload.snapshot || {};
      const id = snap.id ?? "active";
      return { ok: true, connector: "kvm", action: "window-restore", did: `restore(${id})`,
        reversible: true, inverse: { path: "window/command/close", args: { id } } };
    }
    case "cdp/page/command/navigate": {
      const url = payload.url ?? "https://example.test/a";
      return { ok: true, connector: "kvm", action: "cdp-navigate", url, ready: { ok: true, readyState: "complete" },
        inverse: { path: "cdp/page/command/navigate", args: { url: "https://example.test/prev" } } };
    }
    case "ui/command/fill": {
      const text = payload.text ?? "field";
      return { ok: true, connector: "kvm", action: "ui-fill",
        inverse: { path: "ui/command/fill", args: { text, value: "prev-value" } } };
    }
  }
  if (route in CONTRACTS) return cloneOkExample(route);
  throw new Error(`nieznana trasa ${route}`);
}

const [cmd, a, b] = process.argv.slice(2);
if (cmd === "produce") {
  process.stdout.write(JSON.stringify(okExample(a)));
} else if (cmd === "consume") {
  const env = JSON.parse(await readStdin());
  const wire = findWire(a, b);
  const payload = wirePayload(wire, env);
  const [mode, problems] = consumerInputCheck(b, payload, wire);
  process.stdout.write(JSON.stringify({ ok: problems.length === 0, mode, builtInput: payload, problems }));
  process.exit(problems.length === 0 ? 0 : 1);
} else if (cmd === "conform") {
  process.exit(conform());
} else if (cmd === "serve") {
  const lie = process.argv.slice(2).includes("--lie");
  const rl = createInterface({ input: process.stdin });
  for await (const line of rl) {
    const s = line.trim();
    if (!s) continue;
    const req = JSON.parse(s);
    const env = handle(req.route, req.payload, lie);
    process.stdout.write(JSON.stringify({ id: req.id, envelope: env }) + "\n");
  }
} else if (cmd === "serve-http") {
  const { createServer } = await import("node:http");
  const lie = process.argv.slice(2).includes("--lie");
  const server = createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      const r = JSON.parse(body || "{}");
      const env = handle(r.route, r.payload, lie);
      const out = JSON.stringify({ id: r.id, envelope: env });
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(out);
    });
  });
  server.listen(0, "127.0.0.1", () => console.log("READY " + server.address().port));
} else {
  console.error(`nieznany tryb ${cmd}`); process.exit(2);
}
