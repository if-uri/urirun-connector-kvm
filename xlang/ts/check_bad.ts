// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// To samo kłamstwo na drucie co w runtime (screen jako STRINGI) — ale złapane w CZASIE KOMPILACJI.
// tsc MUSI to odrzucić: 'string[]' nie jest przypisywalne do 'number[]'. Ten plik NIE może się skompilować;
// typescript_proof.sh traktuje udaną kompilację jako PORAŻKĘ (brak zębów).
import type { Out_abs_command_click } from "./contracts";

export const lie: Out_abs_command_click = {
  action: "click-abs",
  screen: ["2560", "1440"], // ← stringi zamiast number[]: błąd typu w czasie kompilacji
  ok: true,
  connector: "kvm",
  did: "click@(0,0)",
};
