/**
 * M3.4.3 -- Multimodal Input Bar
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md SS7.1
 * [R10 §voice cascade] Voice 3-tier degradation
 * [RISK-11] Voice never goes to cloud without consent
 * [RISK-12] URL content stripped via M2.3 before LLM
 */

import React, { useRef, useState } from "react";
import { FileAttachmentPreview } from "./FileAttachmentPreview";
import { routeVoiceTranscription } from "./useVoiceInput";

interface Props {
  onSend: (message: string, attachments: File[]) => void;
  onWorkflowOpen: () => void;
  voiceCloudConsent?: boolean;
  voiceRouter?: (blob: Blob) => Promise<{ transcript: string }>;
  disabled?: boolean;
}

export function MultimodalInputBar({
  onSend,
  onWorkflowOpen,
  voiceCloudConsent = false,
  voiceRouter,
  disabled = false,
}: Props) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [recording, setRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const handleSend = () => {
    if (!text.trim() && attachments.length === 0) return;
    onSend(text, attachments);
    setText("");
    setAttachments([]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setAttachments((prev) => [...prev, ...files]);
    e.target.value = "";
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          let transcript: string;
          if (voiceRouter) {
            const result = await voiceRouter(blob);
            transcript = result.transcript;
          } else {
            transcript = await routeVoiceTranscription(blob, voiceCloudConsent);
          }
          // Fill input box -- user confirms before sending
          if (transcript) setText((prev) => prev + (prev ? " " : "") + transcript);
        } catch {
          alert("語音轉錄失敗，請改為文字輸入");
        }
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      alert("無法存取麥克風");
    }
  };

  const stopRecording = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  return (
    <div className="border-t bg-white px-3 py-2">
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-1">
          {attachments.map((f, i) => (
            <FileAttachmentPreview
              key={i}
              file={f}
              onRemove={() => setAttachments((prev) => prev.filter((_, j) => j !== i))}
            />
          ))}
        </div>
      )}

      <div className="flex items-end gap-1">
        {/* Attachment */}
        <button
          data-testid="attachment-btn"
          onClick={() => fileInputRef.current?.click()}
          className="p-2 text-gray-400 hover:text-gray-600"
          title="附件"
        >
          +
        </button>
        <input
          data-testid="file-upload-input"
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          onChange={handleFileChange}
        />

        {/* URL (treated as text -- M2.3 strips it server-side) */}
        <button
          data-testid="url-btn"
          className="p-2 text-gray-400 hover:text-gray-600"
          title="貼上網址"
        >
          🔗
        </button>

        {/* Workflow */}
        <button
          data-testid="workflow-btn"
          onClick={onWorkflowOpen}
          className="p-2 text-gray-400 hover:text-gray-600"
          title="工作流設定"
        >
          workflow▸
        </button>

        {/* Text input */}
        <textarea
          data-testid="chat-input"
          className="flex-1 resize-none rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-300"
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="輸入訊息..."
          disabled={disabled}
        />

        {/* Voice */}
        <button
          data-testid="mic-btn"
          onClick={recording ? stopRecording : startRecording}
          className={`p-2 rounded-full ${recording ? "bg-red-100 text-red-600 animate-pulse" : "text-gray-400 hover:text-gray-600"}`}
          title={recording ? "停止錄音" : "語音輸入"}
        >
          🎤
        </button>

        {/* Send */}
        <button
          data-testid="send-btn"
          onClick={handleSend}
          disabled={!text.trim() && attachments.length === 0}
          className="p-2 bg-indigo-600 text-white rounded-lg disabled:opacity-40 hover:bg-indigo-700"
        >
          ▷
        </button>
      </div>
    </div>
  );
}
