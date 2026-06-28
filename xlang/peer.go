// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Brama kontraktowa w Go — TRZECI czytnik tego samego neutralnego contracts.json.
// Go ma dwie pułapki, których py/js nie mają, i obie rozbrajamy świadomie:
//
//  1. ZERO-VALUES: brakujący `int` w strukturze deserializuje się do 0, nieodróżnialnego
//     od jawnego zera — semantyka `?optional` by zginęła. Dlatego walidujemy
//     map[string]interface{} (NIE struct): "klucz nieobecny" jest realnie wykrywalny,
//     dokładnie jak w wersji dynamicznej py/js.
//  2. LICZBY: encoding/json daje każdą liczbę jako float64, więc token `int` MUSI
//     sprawdzać całkowitość (v == trunc(v)), inaczej 2560.0 i 2560 byłyby nieodróżnialne.
//
//   produce <route>        — wypisz złotą kopertę ok jako JSON      (proces producenta)
//   consume <prod> <cons>  — wczytaj JSON ze stdin, zbuduj wejście konsumenta, zwaliduj
//   conform               — uruchom asercje konformansu na całym contracts.json
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type violation struct{ msg string }

func (v violation) Error() string { return v.msg }

var (
	contracts map[string]map[string]interface{}
	wires     []map[string]interface{}
)

func loadDoc() {
	exe, _ := os.Executable()
	// szukamy contracts.json obok źródła; w `go run` exe jest w temp, więc próbujemy też CWD-relatywnie.
	candidates := []string{
		filepath.Join(filepath.Dir(exe), "contracts.json"),
		"xlang/contracts.json",
		"contracts.json",
	}
	var raw []byte
	var err error
	for _, p := range candidates {
		raw, err = os.ReadFile(p)
		if err == nil {
			break
		}
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "nie znaleziono contracts.json:", err)
		os.Exit(2)
	}
	var doc map[string]interface{}
	if err := json.Unmarshal(raw, &doc); err != nil {
		fmt.Fprintln(os.Stderr, "zły JSON:", err)
		os.Exit(2)
	}
	contracts = map[string]map[string]interface{}{}
	for route, c := range doc["contracts"].(map[string]interface{}) {
		contracts[route] = c.(map[string]interface{})
	}
	for _, w := range doc["wires"].([]interface{}) {
		wires = append(wires, w.(map[string]interface{}))
	}
}

// ── walidator mini-języka schematu (port 1:1; numery jako float64) ───────────
func typeOK(tok string, v interface{}) bool {
	switch tok {
	case "str":
		_, ok := v.(string)
		return ok
	case "int":
		f, ok := v.(float64) // JSON: każda liczba to float64; bool to bool, nie float64
		return ok && f == math.Trunc(f)
	case "num":
		_, ok := v.(float64)
		return ok
	case "bool":
		_, ok := v.(bool)
		return ok
	case "obj":
		_, ok := v.(map[string]interface{})
		return ok
	case "list":
		_, ok := v.([]interface{})
		return ok
	case "any":
		return true
	}
	return false
}

func constValue(tok string) interface{} {
	lit := tok[len("const:"):]
	if lit == "true" {
		return true
	}
	if lit == "false" {
		return false
	}
	return lit
}

func root(where string) string {
	if where == "" {
		return "<root>"
	}
	return where
}

func dotKey(where, key string) string {
	if where == "" {
		return key
	}
	return where + "." + key
}

func check(schema interface{}, value interface{}, where string) error {
	switch s := schema.(type) {
	case map[string]interface{}:
		if branches, ok := s["oneOf"]; ok && len(s) == 1 {
			var errs []string
			for i, br := range branches.([]interface{}) {
				if err := check(br, value, where); err == nil {
					return nil
				} else {
					errs = append(errs, fmt.Sprintf("wariant %d: %s", i, err))
				}
			}
			return violation{fmt.Sprintf("%s: nie pasuje do żadnego wariantu oneOf [%s]", root(where), strings.Join(errs, "; "))}
		}
		vm, ok := value.(map[string]interface{})
		if !ok {
			return violation{fmt.Sprintf("%s: oczekiwano obiektu", root(where))}
		}
		for key, sub := range s {
			subStr, isStr := sub.(string)
			optional := isStr && strings.HasPrefix(subStr, "?")
			loc := dotKey(where, key)
			vv, present := vm[key]
			if !present {
				if optional {
					continue
				}
				return violation{fmt.Sprintf("%s: brak wymaganego klucza", loc)}
			}
			if err := check(sub, vv, loc); err != nil {
				return err
			}
		}
		return nil
	case []interface{}:
		vl, ok := value.([]interface{})
		if !ok {
			return violation{fmt.Sprintf("%s: oczekiwano listy", root(where))}
		}
		if len(s) > 0 {
			for i, it := range vl {
				if err := check(s[0], it, fmt.Sprintf("%s[%d]", where, i)); err != nil {
					return err
				}
			}
		}
		return nil
	case string:
		tok := s
		if strings.HasPrefix(tok, "?") {
			if value == nil {
				return nil
			}
			return check(tok[1:], value, where)
		}
		if strings.HasPrefix(tok, "const:") {
			expected := constValue(tok)
			if value != expected {
				return violation{fmt.Sprintf("%s: oczekiwano literału %v, jest %v", where, expected, value)}
			}
			return nil
		}
		if strings.HasPrefix(tok, "enum:") {
			allowed := strings.Split(tok[len("enum:"):], "|")
			sv, _ := value.(string)
			for _, a := range allowed {
				if a == sv {
					return nil
				}
			}
			return violation{fmt.Sprintf("%s: %v spoza enum %v", where, value, allowed)}
		}
		if !typeOK(tok, value) {
			return violation{fmt.Sprintf("%s: oczekiwano %s, jest %T (%v)", where, tok, value, value)}
		}
		return nil
	}
	return violation{fmt.Sprintf("%s: nieznany kształt schematu %T", where, schema)}
}

// ── kompozycja ───────────────────────────────────────────────────────────────
func dig(value interface{}, dotted string) (interface{}, error) {
	cur := value
	for _, seg := range strings.Split(dotted, ".") {
		switch c := cur.(type) {
		case []interface{}:
			idx, err := strconv.Atoi(seg)
			if err != nil || idx < 0 || idx >= len(c) {
				return nil, fmt.Errorf("%s: brak segmentu %s", dotted, seg)
			}
			cur = c[idx]
		case map[string]interface{}:
			vv, ok := c[seg]
			if !ok {
				return nil, fmt.Errorf("%s: brak segmentu %s", dotted, seg)
			}
			cur = vv
		default:
			return nil, fmt.Errorf("%s: brak segmentu %s", dotted, seg)
		}
	}
	return cur, nil
}

func findWire(producer, consumer string) map[string]interface{} {
	for _, w := range wires {
		if w["producer"] == producer && w["consumer"] == consumer {
			return w
		}
	}
	fmt.Fprintf(os.Stderr, "brak krawędzi %s -> %s\n", producer, consumer)
	os.Exit(2)
	return nil
}

func wirePayload(wire map[string]interface{}, env interface{}) map[string]interface{} {
	out := map[string]interface{}{}
	for field, path := range wire["mapping"].(map[string]interface{}) {
		if v, err := dig(env, path.(string)); err == nil {
			out[field] = v // źródło nieobecne w tym wariancie — pomiń (pole opcjonalne dostanie default)
		}
	}
	return out
}

func consumerInputCheck(consumer string, payload map[string]interface{}, wire map[string]interface{}) (string, []string) {
	inp := contracts[consumer]["inp"].(map[string]interface{})
	required := map[string]bool{}
	for k, v := range inp {
		s, ok := v.(string)
		if !(ok && strings.HasPrefix(s, "?")) {
			required[k] = true
		}
	}
	carried := map[string]bool{}
	for k := range wire["mapping"].(map[string]interface{}) {
		carried[k] = true
	}
	var problems []string
	requiredSubsetCarried := true
	for k := range required {
		if !carried[k] {
			requiredSubsetCarried = false
		}
	}
	if requiredSubsetCarried {
		var missing []string
		for k := range required {
			if _, ok := payload[k]; !ok {
				missing = append(missing, k)
			}
		}
		if len(missing) > 0 {
			sort.Strings(missing)
			problems = append(problems, fmt.Sprintf("pełny handoff, ale wariant producenta nie dostarczył: %v", missing))
		}
		// w trybie full walidujemy CAŁY schemat wejścia względem payloadu
		pany := map[string]interface{}{}
		for k, v := range payload {
			pany[k] = v
		}
		if err := check(inp, pany, "consumer.inp"); err != nil {
			problems = append(problems, err.Error())
		}
		return "full", problems
	}
	var arrived []string
	for k := range carried {
		if _, ok := payload[k]; ok {
			arrived = append(arrived, k)
		}
	}
	sort.Strings(arrived)
	for _, field := range arrived {
		sub := inp[field]
		if err := check(sub, payload[field], "consumer.inp."+field); err != nil {
			problems = append(problems, err.Error())
		}
	}
	return "partial", problems
}

// ── konformans (parytet z peer.mjs conform) ──────────────────────────────────
func conform() int {
	failures := 0
	fail := func(msg string) { fmt.Fprintf(os.Stderr, "  FAIL %s\n", msg); failures++ }
	for route, c := range contracts {
		effect, _ := c["effect"].(string)
		if strings.Contains(route, "/query/") != (effect == "query") {
			fail(route + ": efekt nie zgadza się z czasownikiem URI")
		}
		if rev, _ := c["reversible"].(bool); rev {
			inv, _ := c["inverseRoute"].(string)
			ic, ok := contracts[inv]
			if !ok {
				fail(fmt.Sprintf("%s: inverseRoute %s nie istnieje", route, inv))
			} else if back, _ := ic["inverseRoute"].(string); back != route {
				fail(fmt.Sprintf("%s <-> %s nie jest wzajemne", route, inv))
			}
		}
		examples, _ := c["examples"].([]interface{})
		for i, exAny := range examples {
			ex := exAny.(map[string]interface{})
			if err := check(c["inp"], ex["payload"], fmt.Sprintf("%s#ex%d.payload", route, i)); err != nil {
				fail(err.Error())
			}
			result := ex["result"].(map[string]interface{})
			if okv, _ := result["ok"].(bool); okv {
				if err := check(c["out"], result, fmt.Sprintf("%s#ex%d.result", route, i)); err != nil {
					fail(err.Error())
				}
				if rev, _ := c["reversible"].(bool); rev {
					if _, hasInverse := result["inverse"]; hasInverse {
						inv, _ := c["inverseRoute"].(string)
						args := map[string]interface{}{}
						if inverse, ok := result["inverse"].(map[string]interface{}); ok {
							if a, ok := inverse["args"].(map[string]interface{}); ok {
								args = a
							}
						}
						if err := check(contracts[inv]["inp"], args, fmt.Sprintf("%s#ex%d.inverse.args -> %s", route, i, inv)); err != nil {
							fail(err.Error())
						}
					}
				}
			}
		}
	}
	if failures == 0 {
		fmt.Printf("  OK: %d kontraktów konformuje (walidator Go, wspólny contracts.json)\n", len(contracts))
		return 0
	}
	return 1
}

func okExample(route string) map[string]interface{} {
	examples, _ := contracts[route]["examples"].([]interface{})
	for _, exAny := range examples {
		ex := exAny.(map[string]interface{})
		result := ex["result"].(map[string]interface{})
		if okv, _ := result["ok"].(bool); okv {
			return result
		}
	}
	fmt.Fprintf(os.Stderr, "%s: brak złotej koperty ok\n", route)
	os.Exit(2)
	return nil
}

func cloneOkExample(route string) map[string]interface{} {
	raw, _ := json.Marshal(okExample(route))
	var out map[string]interface{}
	json.Unmarshal(raw, &out)
	return out
}

// ── prawdziwy handler trasy (stub) — node odpytywany przez zewnętrzny driver ──
func numOr(m map[string]interface{}, k string, d int) int {
	if v, ok := m[k].(float64); ok {
		return int(v)
	}
	return d
}

func strOr(m map[string]interface{}, k, d string) string {
	if v, ok := m[k].(string); ok {
		return v
	}
	return d
}

func handle(route string, payload map[string]interface{}, lie bool) map[string]interface{} {
	switch route {
	case "screen/query/capture":
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "capture",
			"kind": "screenshot", "path": "/home/u/.urirun/artifacts/s.png", "bytes": 204931,
			"fullSize": []interface{}{2560, 1440}, "via": "go-serve"}
	case "abs/command/click":
		sw, sh := numOr(payload, "sw", 1920), numOr(payload, "sh", 1080)
		var screen []interface{}
		if lie {
			screen = []interface{}{fmt.Sprint(sw), fmt.Sprint(sh)} // --lie: int→string na drucie
		} else {
			screen = []interface{}{sw, sh}
		}
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "click-abs",
			"screen": screen, "did": fmt.Sprintf("click@(%d,%d)", numOr(payload, "x", 0), numOr(payload, "y", 0))}
	case "window/command/close":
		id := strOr(payload, "id", "active")
		snap := map[string]interface{}{"url": "https://example.test/x", "scrollX": 0,
			"scrollY": 240, "forms": []interface{}{}, "id": id}
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "window-close",
			"did": "close(" + id + ")", "reversible": true, "snapshot": snap,
			"inverse": map[string]interface{}{"path": "window/command/restore",
				"args": map[string]interface{}{"snapshot": snap}}}
	case "window/command/restore":
		id := "active"
		if snap, ok := payload["snapshot"].(map[string]interface{}); ok {
			id = strOr(snap, "id", "active")
		}
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "window-restore",
			"did": "restore(" + id + ")", "reversible": true,
			"inverse": map[string]interface{}{"path": "window/command/close",
				"args": map[string]interface{}{"id": id}}}
	case "cdp/page/command/navigate":
		url := strOr(payload, "url", "https://example.test/a")
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "cdp-navigate",
			"url": url, "ready": map[string]interface{}{"ok": true, "readyState": "complete"},
			"inverse": map[string]interface{}{"path": "cdp/page/command/navigate",
				"args": map[string]interface{}{"url": "https://example.test/prev"}}}
	case "ui/command/fill":
		text := strOr(payload, "text", "field")
		return map[string]interface{}{"ok": true, "connector": "kvm", "action": "ui-fill",
			"inverse": map[string]interface{}{"path": "ui/command/fill",
				"args": map[string]interface{}{"text": text, "value": "prev-value"}}}
	}
	if _, ok := contracts[route]; ok {
		return cloneOkExample(route)
	}
	return nil
}

func main() {
	loadDoc()
	args := os.Args[1:]
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "nieznany tryb")
		os.Exit(2)
	}
	switch args[0] {
	case "produce":
		out, _ := json.Marshal(okExample(args[1]))
		os.Stdout.Write(out)
	case "consume":
		producer, consumer := args[1], args[2]
		raw, _ := io.ReadAll(os.Stdin)
		var env interface{}
		if err := json.Unmarshal(raw, &env); err != nil {
			fmt.Fprintln(os.Stderr, "zły JSON na stdin:", err)
			os.Exit(2)
		}
		wire := findWire(producer, consumer)
		payload := wirePayload(wire, env)
		mode, problems := consumerInputCheck(consumer, payload, wire)
		if problems == nil {
			problems = []string{}
		}
		out, _ := json.Marshal(map[string]interface{}{
			"ok": len(problems) == 0, "mode": mode, "builtInput": payload, "problems": problems,
		})
		os.Stdout.Write(out)
		if len(problems) != 0 {
			os.Exit(1)
		}
	case "serve":
		lie := false
		for _, a := range args[1:] {
			if a == "--lie" {
				lie = true
			}
		}
		sc := bufio.NewScanner(os.Stdin)
		sc.Buffer(make([]byte, 1<<20), 1<<20)
		for sc.Scan() {
			line := strings.TrimSpace(sc.Text())
			if line == "" {
				continue
			}
			var req map[string]interface{}
			if err := json.Unmarshal([]byte(line), &req); err != nil {
				continue
			}
			route, _ := req["route"].(string)
			payload, _ := req["payload"].(map[string]interface{})
			if payload == nil {
				payload = map[string]interface{}{}
			}
			env := handle(route, payload, lie)
			out, _ := json.Marshal(map[string]interface{}{"id": req["id"], "envelope": env})
			os.Stdout.Write(out)
			os.Stdout.Write([]byte("\n"))
		}
	case "serve-http":
		lie := false
		for _, a := range args[1:] {
			if a == "--lie" {
				lie = true
			}
		}
		ln, err := net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		mux := http.NewServeMux()
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			body, _ := io.ReadAll(r.Body)
			var req map[string]interface{}
			json.Unmarshal(body, &req)
			route, _ := req["route"].(string)
			payload, _ := req["payload"].(map[string]interface{})
			if payload == nil {
				payload = map[string]interface{}{}
			}
			env := handle(route, payload, lie)
			out, _ := json.Marshal(map[string]interface{}{"id": req["id"], "envelope": env})
			w.Header().Set("Content-Type", "application/json")
			w.Write(out)
		})
		fmt.Printf("READY %d\n", ln.Addr().(*net.TCPAddr).Port)
		http.Serve(ln, mux)
	case "conform":
		os.Exit(conform())
	default:
		fmt.Fprintf(os.Stderr, "nieznany tryb %s\n", args[0])
		os.Exit(2)
	}
}
