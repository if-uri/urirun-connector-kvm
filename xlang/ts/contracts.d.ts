// GENERATED z urirun_connector_kvm/contracts.py (dataclass) — nie edytuj ręcznie.
// Te same kontrakty co contracts.json/contracts.schema.json, ale jako typy czasu kompilacji.

export type In_screen_query_capture = {
  "monitor"?: number;
  "max_width"?: number;
  "base64"?: boolean;
  "cx"?: number;
  "cy"?: number;
  [k: string]: unknown;
};
export type Out_screen_query_capture = {
  "kind": "screenshot";
  "path": string;
  "bytes": number;
  "fullSize": number[];
  "via": string;
  [k: string]: unknown;
} | {
  "kind": "screenshot";
  "degraded": true;
  "degradedReason": string;
  "bytes": number;
  [k: string]: unknown;
};

export type In_abs_command_click = {
  "x": number;
  "y": number;
  "sw"?: number;
  "sh"?: number;
  "button"?: string;
  "do_click"?: boolean;
  [k: string]: unknown;
};
export type Out_abs_command_click = {
  "action": "click-abs";
  "screen": number[];
  [k: string]: unknown;
};

export type In_window_command_close = {
  "id"?: string;
  [k: string]: unknown;
};
export type Out_window_command_close = {
  "action": "window-close";
  "reversible": true;
  "snapshot": Record<string, unknown>;
  "inverse": {
    "path": "window/command/restore";
    "args": {
      "snapshot": Record<string, unknown>;
      [k: string]: unknown;
    };
    [k: string]: unknown;
  };
  [k: string]: unknown;
};

export type In_window_command_restore = {
  "snapshot": Record<string, unknown>;
  [k: string]: unknown;
};
export type Out_window_command_restore = {
  "action": "window-restore";
  "reversible": true;
  "inverse": {
    "path": "window/command/close";
    "args": {
      "id"?: string;
      [k: string]: unknown;
    };
    [k: string]: unknown;
  };
  [k: string]: unknown;
};

export type In_cdp_page_command_navigate = {
  "url": string;
  "ready_timeout"?: number;
  [k: string]: unknown;
};
export type Out_cdp_page_command_navigate = {
  "action": "cdp-navigate";
  "url": string;
  "ready": boolean;
  "inverse"?: Record<string, unknown>;
  [k: string]: unknown;
};

export type In_ui_command_fill = {
  "value": string;
  "text"?: string;
  "role"?: string;
  "name"?: string;
  "app"?: string;
  "verify"?: boolean;
  [k: string]: unknown;
};
export type Out_ui_command_fill = {
  "action": "ui-fill";
  "inverse"?: Record<string, unknown>;
  [k: string]: unknown;
};

export interface Contracts {
  "screen/query/capture": { input: In_screen_query_capture; output: Out_screen_query_capture };
  "abs/command/click": { input: In_abs_command_click; output: Out_abs_command_click };
  "window/command/close": { input: In_window_command_close; output: Out_window_command_close };
  "window/command/restore": { input: In_window_command_restore; output: Out_window_command_restore };
  "cdp/page/command/navigate": { input: In_cdp_page_command_navigate; output: Out_cdp_page_command_navigate };
  "ui/command/fill": { input: In_ui_command_fill; output: Out_ui_command_fill };
}
