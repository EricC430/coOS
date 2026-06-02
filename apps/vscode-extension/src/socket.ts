/**
 * M1.3.1 Named Pipe client
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md §7.2
 * Connects to \\.\pipe\coos_telemetry (Windows Named Pipe provided by Tauri/FastAPI).
 * On disconnect: buffers up to MAX_BUFFER events, exponential backoff reconnect.
 */

import * as net from 'net';
import type { CodeActivityEvent } from './types';

const PIPE_PATH = '\\\\.\\pipe\\coos_telemetry';
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

  send(event: CodeActivityEvent): void {
    if (this.connected && this.socket) {
      const line = JSON.stringify(event) + '\n';
      this.socket.write(line);
    } else {
      // Buffer while disconnected, evict oldest if full
      if (this.buffer.length >= MAX_BUFFER) {
        this.buffer.shift();
      }
      this.buffer.push(event);
    }
  }

  dispose(): void {
    this.socket?.destroy();
    this.socket = null;
    this.connected = false;
  }

  get bufferCount(): number {
    return this.buffer.length;
  }

  private flushBuffer(): void {
    while (this.buffer.length > 0 && this.connected && this.socket) {
      const event = this.buffer.shift()!;
      const line = JSON.stringify(event) + '\n';
      this.socket.write(line);
    }
  }

  private scheduleReconnect(): void {
    setTimeout(() => this.connect(), this.reconnectDelay);
    // Exponential backoff, capped at 30s
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, RECONNECT_MAX_MS);
  }
}
