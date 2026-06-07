/**
 * M1.3.1 Named Pipe client
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md §7.2
 * Connects to \\.\pipe\coos_telemetry (Windows Named Pipe provided by Tauri/FastAPI).
 * On disconnect: buffers up to MAX_BUFFER events, exponential backoff reconnect.
 */

import * as net from 'net';
import * as os from 'os';
import * as path from 'path';
import type { CodeActivityEvent } from './types';

const PIPE_PATH = process.platform === 'win32'
  ? '\\\\.\\pipe\\coos_telemetry'
  : path.join(os.tmpdir(), 'coos_telemetry.sock');

const BACKEND_URL = 'http://127.0.0.1:8000/api/m1_1/event';
const MAX_BUFFER = 100;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export class TelemetrySocket {
  private socket: net.Socket | null = null;
  private buffer: CodeActivityEvent[] = [];
  private reconnectDelay = RECONNECT_BASE_MS;
  private connected = false;

  connect(): void {
    this.socket = net.createConnection(PIPE_PATH);

    this.socket.on('connect', () => {
      this.connected = true;
      this.reconnectDelay = RECONNECT_BASE_MS;
      this.flushBuffer();
    });

    this.socket.on('error', () => {
      this.connected = false;
      this.scheduleReconnect();
    });

    this.socket.on('close', () => {
      this.connected = false;
      this.scheduleReconnect();
    });
  }

  async send(event: CodeActivityEvent): Promise<void> {
    if (this.connected && this.socket) {
      try {
        const line = JSON.stringify(event) + '\n';
        this.socket.write(line);
        return;
      } catch (e) {
        this.connected = false;
      }
    }

    // Fallback: Attempt HTTP POST directly to sidecar
    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      });
      if (response.ok) {
        return;
      }
    } catch (e) {
      // Both socket and HTTP failed
    }

    // Buffer as last resort, evict oldest if full
    if (this.buffer.length >= MAX_BUFFER) {
      this.buffer.shift();
    }
    this.buffer.push(event);
  }

  dispose(): void {
    this.socket?.destroy();
    this.socket = null;
    this.connected = false;
  }

  get bufferCount(): number {
    return this.buffer.length;
  }

  private async flushBuffer(): Promise<void> {
    while (this.buffer.length > 0 && this.connected && this.socket) {
      const event = this.buffer.shift()!;
      try {
        const line = JSON.stringify(event) + '\n';
        this.socket.write(line);
      } catch (e) {
        this.connected = false;
        this.buffer.unshift(event);
        break;
      }
    }
  }

  private scheduleReconnect(): void {
    setTimeout(() => this.connect(), this.reconnectDelay);
    // Exponential backoff, capped at 30s
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, RECONNECT_MAX_MS);
  }
}
