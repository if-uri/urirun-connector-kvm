// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Brama kontraktowa w Rust — CZWARTY czytnik tego samego neutralnego contracts.json.
// Pointa: liczba czytników nie jest ograniczona do trzech. Atut Rust: serde_json::Value::Number
// ROZRÓŻNIA is_i64()/is_f64() natywnie, więc token `int` jest tu CZYSTSZY niż w JS/Go
// (gdzie trzeba ręcznie sprawdzać całkowitość float). Walidacja po dynamicznym Value —
// jak w py/js/go — żeby „klucz nieobecny" był wykrywalny (semantyka ?optional).
//
//   produce <route>        — wypisz złotą kopertę ok jako JSON
//   consume <prod> <cons>  — wczytaj JSON ze stdin, zbuduj wejście konsumenta, zwaliduj
//   conform                — asercje konformansu na całym contracts.json
//   serve [--lie]          — serwer RPC (JSON-lines/stdio)
//   serve-http [--lie]     — ten sam handler za HTTP (std::net), wypisuje "READY <port>"

use serde_json::{json, Map, Value};
use std::collections::HashSet;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::sync::OnceLock;

static DOC: OnceLock<Value> = OnceLock::new();

fn doc() -> &'static Value {
    DOC.get().expect("contracts.json nie załadowany")
}
fn contracts() -> &'static Map<String, Value> {
    doc()["contracts"].as_object().unwrap()
}
fn wires() -> &'static Vec<Value> {
    doc()["wires"].as_array().unwrap()
}

fn load_doc() {
    let mut candidates: Vec<std::path::PathBuf> = vec![];
    if let Ok(exe) = std::env::current_exe() {
        if let Some(d) = exe.parent() {
            candidates.push(d.join("contracts.json"));
        }
    }
    candidates.push("xlang/contracts.json".into());
    candidates.push("contracts.json".into());
    for p in candidates {
        if let Ok(raw) = std::fs::read(&p) {
            let parsed: Value = serde_json::from_slice(&raw).expect("zły JSON");
            DOC.set(parsed).ok();
            return;
        }
    }
    eprintln!("nie znaleziono contracts.json");
    std::process::exit(2);
}

// ── walidator mini-języka schematu (port 1:1; serde rozróżnia int/float natywnie) ──
fn type_name(v: &Value) -> &'static str {
    match v {
        Value::Null => "null",
        Value::Bool(_) => "bool",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

fn type_ok(tok: &str, v: &Value) -> bool {
    match tok {
        "str" => v.is_string(),
        "int" => v.is_i64() || v.is_u64(), // czystsze niż JS/Go: serde sam odróżnia całkowite od f64
        "num" => v.is_number(),
        "bool" => v.is_boolean(),
        "obj" => v.is_object(),
        "list" => v.is_array(),
        "any" => true,
        _ => false,
    }
}

fn const_value(lit: &str) -> Value {
    match lit {
        "true" => json!(true),
        "false" => json!(false),
        _ => json!(lit),
    }
}

fn root(wh: &str) -> String {
    if wh.is_empty() {
        "<root>".into()
    } else {
        wh.into()
    }
}
fn dot(wh: &str, key: &str) -> String {
    if wh.is_empty() {
        key.into()
    } else {
        format!("{}.{}", wh, key)
    }
}

fn check(schema: &Value, value: &Value, wh: &str) -> Result<(), String> {
    if let Value::Object(m) = schema {
        if m.len() == 1 {
            if let Some(Value::Array(branches)) = m.get("oneOf") {
                let mut errs = vec![];
                for (i, br) in branches.iter().enumerate() {
                    match check(br, value, wh) {
                        Ok(()) => return Ok(()),
                        Err(e) => errs.push(format!("wariant {}: {}", i, e)),
                    }
                }
                return Err(format!(
                    "{}: nie pasuje do żadnego wariantu oneOf [{}]",
                    root(wh),
                    errs.join("; ")
                ));
            }
        }
        let vm = match value {
            Value::Object(vm) => vm,
            _ => return Err(format!("{}: oczekiwano obiektu", root(wh))),
        };
        for (key, sub) in m {
            let optional = matches!(sub, Value::String(s) if s.starts_with('?'));
            let loc = dot(wh, key);
            match vm.get(key) {
                None => {
                    if optional {
                        continue;
                    }
                    return Err(format!("{}: brak wymaganego klucza", loc));
                }
                Some(vv) => {
                    if optional {
                        if let Value::String(s) = sub {
                            check(&Value::String(s[1..].to_string()), vv, &loc)?;
                        }
                    } else {
                        check(sub, vv, &loc)?;
                    }
                }
            }
        }
        return Ok(());
    }
    if let Value::Array(arr) = schema {
        let vl = match value {
            Value::Array(vl) => vl,
            _ => return Err(format!("{}: oczekiwano listy", root(wh))),
        };
        if let Some(first) = arr.first() {
            for (i, it) in vl.iter().enumerate() {
                check(first, it, &format!("{}[{}]", wh, i))?;
            }
        }
        return Ok(());
    }
    if let Value::String(s0) = schema {
        let tok = s0.strip_prefix('?').unwrap_or(s0);
        if let Some(lit) = tok.strip_prefix("const:") {
            let expected = const_value(lit);
            if value != &expected {
                return Err(format!("{}: oczekiwano literału {}, jest {}", wh, expected, value));
            }
            return Ok(());
        }
        if let Some(en) = tok.strip_prefix("enum:") {
            let allowed: Vec<&str> = en.split('|').collect();
            if let Value::String(sv) = value {
                if allowed.contains(&sv.as_str()) {
                    return Ok(());
                }
            }
            return Err(format!("{}: {} spoza enum {:?}", wh, value, allowed));
        }
        if !type_ok(tok, value) {
            return Err(format!(
                "{}: oczekiwano {}, jest {} ({})",
                wh,
                tok,
                type_name(value),
                value
            ));
        }
        return Ok(());
    }
    Err(format!("{}: nieznany kształt schematu", wh))
}

// ── kompozycja ────────────────────────────────────────────────────────────────
fn dig<'a>(value: &'a Value, dotted: &str) -> Result<&'a Value, String> {
    let mut cur = value;
    for seg in dotted.split('.') {
        match cur {
            Value::Array(a) => {
                let idx: usize = seg
                    .parse()
                    .map_err(|_| format!("{}: brak segmentu {}", dotted, seg))?;
                cur = a
                    .get(idx)
                    .ok_or_else(|| format!("{}: brak segmentu {}", dotted, seg))?;
            }
            Value::Object(o) => {
                cur = o
                    .get(seg)
                    .ok_or_else(|| format!("{}: brak segmentu {}", dotted, seg))?;
            }
            _ => return Err(format!("{}: brak segmentu {}", dotted, seg)),
        }
    }
    Ok(cur)
}

fn find_wire(producer: &str, consumer: &str) -> &'static Value {
    for w in wires() {
        if w["producer"].as_str() == Some(producer) && w["consumer"].as_str() == Some(consumer) {
            return w;
        }
    }
    eprintln!("brak krawędzi {} -> {}", producer, consumer);
    std::process::exit(2);
}

fn wire_payload(wire: &Value, env: &Value) -> Map<String, Value> {
    let mut out = Map::new();
    if let Some(mapping) = wire["mapping"].as_object() {
        for (field, path) in mapping {
            if let Some(p) = path.as_str() {
                if let Ok(v) = dig(env, p) {
                    out.insert(field.clone(), v.clone());
                }
            }
        }
    }
    out
}

fn consumer_input_check(consumer: &str, payload: &Map<String, Value>, wire: &Value) -> (String, Vec<String>) {
    let inp = contracts()[consumer]["inp"].as_object().unwrap();
    let required: HashSet<&str> = inp
        .iter()
        .filter(|(_, v)| !matches!(v, Value::String(s) if s.starts_with('?')))
        .map(|(k, _)| k.as_str())
        .collect();
    let carried: HashSet<&str> = wire["mapping"].as_object().unwrap().keys().map(String::as_str).collect();
    let mut problems = vec![];
    let required_subset = required.iter().all(|k| carried.contains(k));
    if required_subset {
        let mut missing: Vec<&str> = required.iter().copied().filter(|k| !payload.contains_key(*k)).collect();
        missing.sort();
        if !missing.is_empty() {
            problems.push(format!("pełny handoff, ale wariant producenta nie dostarczył: {:?}", missing));
        }
        let pv = Value::Object(payload.clone());
        if let Err(e) = check(&Value::Object(inp.clone()), &pv, "consumer.inp") {
            problems.push(e);
        }
        return ("full".into(), problems);
    }
    let mut arrived: Vec<&str> = carried.iter().copied().filter(|k| payload.contains_key(*k)).collect();
    arrived.sort();
    for field in arrived {
        let sub = &inp[field];
        let sub_t = match sub {
            Value::String(s) if s.starts_with('?') => Value::String(s[1..].to_string()),
            other => other.clone(),
        };
        if let Err(e) = check(&sub_t, &payload[field], &format!("consumer.inp.{}", field)) {
            problems.push(e);
        }
    }
    ("partial".into(), problems)
}

// ── konformans (parytet z peer.go/peer.mjs) ─────────────────────────────────────
fn conform() -> i32 {
    let mut fails: Vec<String> = vec![];
    for (route, c) in contracts() {
        let effect = c["effect"].as_str().unwrap_or("");
        if route.contains("/query/") != (effect == "query") {
            fails.push(format!("{}: efekt nie zgadza się z czasownikiem URI", route));
        }
        if c["reversible"].as_bool().unwrap_or(false) {
            let inv = c["inverseRoute"].as_str().unwrap_or("");
            match contracts().get(inv) {
                None => fails.push(format!("{}: inverseRoute {} nie istnieje", route, inv)),
                Some(ic) => {
                    if ic["inverseRoute"].as_str().unwrap_or("") != route {
                        fails.push(format!("{} <-> {} nie jest wzajemne", route, inv));
                    }
                }
            }
        }
        if let Some(examples) = c["examples"].as_array() {
            for (i, ex) in examples.iter().enumerate() {
                if let Err(e) = check(&c["inp"], &ex["payload"], &format!("{}#ex{}.payload", route, i)) {
                    fails.push(e);
                }
                let result = &ex["result"];
                if result["ok"].as_bool().unwrap_or(false) {
                    if let Err(e) = check(&c["out"], result, &format!("{}#ex{}.result", route, i)) {
                        fails.push(e);
                    }
                    if c["reversible"].as_bool().unwrap_or(false) && result.get("inverse").is_some() {
                        let inv = c["inverseRoute"].as_str().unwrap_or("");
                        let args = result["inverse"].get("args").cloned().unwrap_or(json!({}));
                        if let Err(e) = check(&contracts()[inv]["inp"], &args,
                            &format!("{}#ex{}.inverse.args -> {}", route, i, inv)) {
                            fails.push(e);
                        }
                    }
                }
            }
        }
    }
    for f in &fails {
        eprintln!("  FAIL {}", f);
    }
    if fails.is_empty() {
        println!("  OK: {} kontraktów konformuje (walidator Rust, wspólny contracts.json)", contracts().len());
        0
    } else {
        1
    }
}

// ── prawdziwy handler trasy (stub) — node odpytywany przez zewnętrzny driver ────
fn handle(route: &str, payload: &Value, lie: bool) -> Value {
    match route {
        "screen/query/capture" => json!({
            "ok": true, "connector": "kvm", "action": "capture", "kind": "screenshot",
            "path": "/home/u/.urirun/artifacts/s.png", "bytes": 204931,
            "fullSize": [2560, 1440], "via": "rs-serve"
        }),
        "abs/command/click" => {
            let sw = payload.get("sw").and_then(Value::as_i64).unwrap_or(1920);
            let sh = payload.get("sh").and_then(Value::as_i64).unwrap_or(1080);
            let x = payload.get("x").and_then(Value::as_i64).unwrap_or(0);
            let y = payload.get("y").and_then(Value::as_i64).unwrap_or(0);
            let screen = if lie {
                json!([sw.to_string(), sh.to_string()]) // --lie: int→string na drucie
            } else {
                json!([sw, sh])
            };
            json!({"ok": true, "connector": "kvm", "action": "click-abs",
                   "screen": screen, "did": format!("click@({},{})", x, y)})
        }
        "window/command/close" => {
            let id = payload.get("id").and_then(Value::as_str).unwrap_or("active");
            let snap = json!({"url": "https://example.test/x", "scrollX": 0, "scrollY": 240, "forms": [], "id": id});
            json!({"ok": true, "connector": "kvm", "action": "window-close",
                   "did": format!("close({})", id), "reversible": true, "snapshot": snap.clone(),
                   "inverse": {"path": "window/command/restore", "args": {"snapshot": snap}}})
        }
        "window/command/restore" => {
            let id = payload.get("snapshot").and_then(|s| s.get("id")).and_then(Value::as_str).unwrap_or("active");
            json!({"ok": true, "connector": "kvm", "action": "window-restore",
                   "did": format!("restore({})", id), "reversible": true,
                   "inverse": {"path": "window/command/close", "args": {"id": id}}})
        }
        "cdp/page/command/navigate" => {
            let url = payload.get("url").and_then(Value::as_str).unwrap_or("https://example.test/a");
            json!({"ok": true, "connector": "kvm", "action": "cdp-navigate", "url": url, "ready": true,
                   "inverse": {"path": "cdp/page/command/navigate", "args": {"url": "https://example.test/prev"}}})
        }
        "ui/command/fill" => {
            let text = payload.get("text").and_then(Value::as_str).unwrap_or("field");
            json!({"ok": true, "connector": "kvm", "action": "ui-fill",
                   "inverse": {"path": "ui/command/fill", "args": {"text": text, "value": "prev-value"}}})
        }
        _ => Value::Null,
    }
}

fn ok_example(route: &str) -> Value {
    if let Some(examples) = contracts()[route]["examples"].as_array() {
        for ex in examples {
            if ex["result"]["ok"].as_bool().unwrap_or(false) {
                return ex["result"].clone();
            }
        }
    }
    eprintln!("{}: brak złotej koperty ok", route);
    std::process::exit(2);
}

fn main() {
    load_doc();
    let argv: Vec<String> = std::env::args().collect();
    let cmd = argv.get(1).map(String::as_str).unwrap_or("");
    let lie = argv.iter().any(|a| a == "--lie");
    match cmd {
        "produce" => {
            print!("{}", serde_json::to_string(&ok_example(&argv[2])).unwrap());
        }
        "consume" => {
            let (producer, consumer) = (argv[2].as_str(), argv[3].as_str());
            let mut input = String::new();
            std::io::stdin().read_to_string(&mut input).unwrap();
            let envelope: Value = serde_json::from_str(&input).unwrap();
            let wire = find_wire(producer, consumer);
            let payload = wire_payload(wire, &envelope);
            let (mode, problems) = consumer_input_check(consumer, &payload, wire);
            let ok = problems.is_empty();
            let out = json!({"ok": ok, "mode": mode, "builtInput": Value::Object(payload), "problems": problems});
            print!("{}", serde_json::to_string(&out).unwrap());
            std::process::exit(if ok { 0 } else { 1 });
        }
        "conform" => std::process::exit(conform()),
        "serve" => {
            let stdin = std::io::stdin();
            let stdout = std::io::stdout();
            for line in stdin.lock().lines() {
                let line = line.unwrap();
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                let req: Value = serde_json::from_str(line).unwrap();
                let route = req["route"].as_str().unwrap_or("");
                let payload = req.get("payload").cloned().unwrap_or(json!({}));
                let env = handle(route, &payload, lie);
                let out = serde_json::to_string(&json!({"id": req.get("id"), "envelope": env})).unwrap();
                let mut h = stdout.lock();
                writeln!(h, "{}", out).unwrap();
                h.flush().unwrap();
            }
        }
        "serve-http" => {
            let listener = TcpListener::bind("127.0.0.1:0").unwrap();
            let port = listener.local_addr().unwrap().port();
            println!("READY {}", port);
            std::io::stdout().flush().unwrap();
            for stream in listener.incoming() {
                let mut stream = match stream {
                    Ok(s) => s,
                    Err(_) => continue,
                };
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let mut line = String::new();
                if reader.read_line(&mut line).is_err() {
                    continue;
                }
                let mut content_length = 0usize;
                loop {
                    let mut h = String::new();
                    if reader.read_line(&mut h).unwrap_or(0) == 0 {
                        break;
                    }
                    if h == "\r\n" || h == "\n" {
                        break;
                    }
                    let lower = h.to_ascii_lowercase();
                    if let Some(v) = lower.strip_prefix("content-length:") {
                        content_length = v.trim().parse().unwrap_or(0);
                    }
                }
                let mut body = vec![0u8; content_length];
                reader.read_exact(&mut body).ok();
                let req: Value = serde_json::from_slice(&body).unwrap_or(json!({}));
                let route = req["route"].as_str().unwrap_or("");
                let payload = req.get("payload").cloned().unwrap_or(json!({}));
                let env = handle(route, &payload, lie);
                let resp_body = serde_json::to_string(&json!({"id": req.get("id"), "envelope": env})).unwrap();
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    resp_body.len(),
                    resp_body
                );
                stream.write_all(resp.as_bytes()).ok();
            }
        }
        other => {
            eprintln!("nieznany tryb {}", other);
            std::process::exit(2);
        }
    }
}
