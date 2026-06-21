/**
 * M1.3.1 VS Code Extension — main entry point
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md
 * Research:
 *   [R02: 源碼變更熵 §1.1] Track edit distribution → entropy
 *   [R02: 時間動力學 §1.2] Track save intervals → burst detection
 *
 * Privacy:
 *   - L1 plaintext (including document.getText()) can be sent to the local backend for local LLM consumption
 *   - Protected from leaving the local machine / entering cloud LLMs
 *   - File paths stored as relative workspace paths only
 *   - Source code content is sent locally but restricted to L1 storage and local models
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';
import { calculateChangeEntropy, analyzeCollaboration, calculateChurnIndex } from './collaboration';
import { TelemetrySocket } from './socket';
import type { CodeActivityEvent, EditChunk } from './types';

// Sliding window: 5 min, updated every 30s
const ENTROPY_WINDOW_MS = 5 * 60 * 1000;
const DEBOUNCE_MS = 500;

let socket: TelemetrySocket;
let editCounts: Map<string, number> = new Map();
let editChunks: EditChunk[] = [];
let windowStart = Date.now();
let lastSaveTime: number | null = null;
let lastActiveEditor: string | null = null;
let editorStayStart: number | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let lastEditTime: number | null = null;

export function activate(context: vscode.ExtensionContext): void {
  socket = new TelemetrySocket();
  socket.connect();

  // M1.3.1: onDidChangeTextDocument — 500ms debounce
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument(event => {
      const uri = event.document.uri;
      if (uri.scheme !== 'file') return;

      const relPath = toRelativePath(uri);
      const now = Date.now();

      for (const change of event.contentChanges) {
        const inserted = change.text.length;
        const deleted = change.rangeLength;
        const timeDelta = lastEditTime ? now - lastEditTime : 200;
        lastEditTime = now;

        // Accumulate edit counts per file
        editCounts.set(relPath, (editCounts.get(relPath) ?? 0) + inserted + deleted);

        // Track chunk for collaboration heuristics
        editChunks.push({ insertedChars: inserted, deletedChars: deleted, timeDeltaMs: timeDelta });
      }

      // Debounce: emit edit_burst every 500ms of silence
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => emitEditBurst(), DEBOUNCE_MS);

      // Roll window if > 5 min
      if (now - windowStart > ENTROPY_WINDOW_MS) {
        editCounts = new Map();
        editChunks = [];
        windowStart = now;
      }
    })
  );

  // M1.3.1: onDidChangeActiveTextEditor — file stay tracking
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(editor => {
      if (lastActiveEditor && editorStayStart !== null) {
        const stayMs = Date.now() - editorStayStart;
        emitFileStay(lastActiveEditor, stayMs);
      }
      lastActiveEditor = editor ? toRelativePath(editor.document.uri) : null;
      editorStayStart = editor ? Date.now() : null;
    })
  );

  // M1.3.1: onDidSaveTextDocument — save interval tracking
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(_doc => {
      const now = Date.now();
      const interval = lastSaveTime ? (now - lastSaveTime) / 1000 : 0;
      lastSaveTime = now;
      // Save interval is included in the next edit_burst payload
      (global as { _lastSaveInterval?: number })._lastSaveInterval = interval;
    })
  );

  // M1.3.1: window focus loss → ide_focus_leave
  context.subscriptions.push(
    vscode.window.onDidChangeWindowState(state => {
      if (!state.focused) {
        emit({
          module: 'M1.3.1',
          action: 'ide_focus_leave',
          payload: {},
          timestamp: new Date().toISOString(),
          id: crypto.randomUUID(),
          level: 'INFO',
          role_id: 'default',
        });
      }
    })
  );
}

export function deactivate(): void {
  socket?.dispose();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function emitEditBurst(): void {
  if (editCounts.size === 0) return;

  const activeEditor = vscode.window.activeTextEditor;
  const contentRaw = activeEditor ? activeEditor.document.getText().substring(0, 4000) : '';

  const entropy = calculateChangeEntropy(editCounts);
  const humanChars = editChunks
    .filter(c => analyzeCollaboration(c) === 'HUMAN_TYPING')
    .reduce((s, c) => s + c.insertedChars, 0);
  const aiChars = editChunks
    .filter(c => analyzeCollaboration(c) === 'AI_GENERATION')
    .reduce((s, c) => s + c.insertedChars, 0);
  const total = humanChars + aiChars;
  const churnIndex = calculateChurnIndex(editChunks);
  const saveInterval = (global as { _lastSaveInterval?: number })._lastSaveInterval ?? 0;

  emit({
    module: 'M1.3.1',
    action: 'edit_burst',
    payload: {
      entropy,
      files_touched: editCounts.size,
      save_interval_s: saveInterval,
      human_typed_chars: humanChars,
      ai_generated_chars: aiChars,
      copilot_ratio: total > 0 ? aiChars / total : 0,
      churn_index: churnIndex,
      content_raw: contentRaw,
      inference_mode: 'rule_based_fallback',
      privacy_tier: 'T1_OPTIN',
    },
    timestamp: new Date().toISOString(),
    id: crypto.randomUUID(),
    level: 'INFO',
    role_id: 'default',
  });
}

function emitFileStay(relPath: string, stayMs: number): void {
  const stayS = Math.floor(stayMs / 1000);
  if (stayS < 1) return;

  const ext = relPath.includes('.') ? '.' + relPath.split('.').pop()! : '';
  emit({
    module: 'M1.3.1',
    action: 'file_stay',
    payload: {
      files: [relPath],
      stay_s: stayS,
      lines_changed: 0,
      stay_mode: 'active_review',
      file_ext: ext,
    },
    timestamp: new Date().toISOString(),
    id: crypto.randomUUID(),
    level: 'INFO',
    role_id: 'default',
  });
}

function emit(event: CodeActivityEvent): void {
  socket.send(event);
}

/** Return path relative to workspace root, stripping absolute prefix. */
function toRelativePath(uri: vscode.Uri): string {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (workspaceFolders && workspaceFolders.length > 0) {
    const wsRoot = workspaceFolders[0].uri.fsPath;
    const full = uri.fsPath;
    if (full.startsWith(wsRoot)) {
      return full.slice(wsRoot.length).replace(/^[/\\]/, '');
    }
  }
  // Fallback: just the filename, never expose absolute path
  return uri.fsPath.split(/[/\\]/).pop() ?? 'unknown';
}
