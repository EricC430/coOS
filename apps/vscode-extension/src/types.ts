/**
 * M1.3.1 TypeScript interfaces
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md §3 Outputs
 * Research: [R02: 源碼變更熵 §1.1] [R02: 時間動力學 §1.2]
 */

export interface CodeActivityPayload {
  entropy: number;            // Shannon Entropy [0,1], 5-min sliding window
  files_touched: number;      // distinct files in window
  save_interval_s: number;    // seconds between last two Ctrl+S
  human_typed_chars: number;  // heuristic: chars inserted by human
  ai_generated_chars: number; // heuristic: chars inserted by AI block paste
  copilot_ratio: number;      // ai_generated_chars / (human + ai) [0,1]
  churn_index: number;        // Agent churn loop indicator [0,1]
}

export interface FileStayPayload {
  files: string[];            // relative workspace paths only
  stay_s: number;             // dwell time in seconds
  lines_changed: number;      // lines changed during stay
  stay_mode: 'active_edit' | 'active_review' | 'passive_read';
  file_ext: string;           // primary file extension e.g. ".py"
}

export interface CodeActivityEvent {
  module: 'M1.3.1';
  action: 'edit_burst' | 'file_stay' | 'ide_focus_leave';
  payload: CodeActivityPayload | FileStayPayload | Record<string, never>;
  timestamp: string;          // ISO 8601 UTC
  id: string;                 // UUID v4
  level: 'INFO' | 'WARNING';
  role_id: string;
}

export interface EditChunk {
  insertedChars: number;
  deletedChars: number;
  timeDeltaMs: number;
}

export type CollaborationType = 'HUMAN_TYPING' | 'AI_GENERATION' | 'BULK_DELETE';
