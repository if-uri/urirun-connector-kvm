// Author: Tom Sapletta · https://tom.sapletta.com
// Part of the ifURI solution.
//
// Konsument TS na WYGENEROWANYCH typach. Złoty kształt: screen to liczby — MUSI się skompilować.
// Klucze nadmiarowe koperty (ok/connector/did) są dozwolone przez indeks [k: string]: unknown.
import type { Out_abs_command_click, Out_screen_query_capture } from "./contracts";

export const click: Out_abs_command_click = {
  action: "click-abs",
  screen: [2560, 1440],
  ok: true,
  connector: "kvm",
  did: "click@(840,612)",
};

// Wariant sukcesu unii capture (oneOf→union): niesie path + fullSize.
export const shot: Out_screen_query_capture = {
  kind: "screenshot",
  path: "/home/u/.urirun/artifacts/s.png",
  bytes: 204931,
  fullSize: [2560, 1440],
  via: "grim",
  ok: true,
};
