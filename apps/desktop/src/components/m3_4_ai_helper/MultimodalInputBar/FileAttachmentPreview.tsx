/**
 * M3.4.3 -- File attachment preview chip
 */

import React from "react";

interface Props {
  file: File;
  onRemove: () => void;
}

export function FileAttachmentPreview({ file, onRemove }: Props) {
  return (
    <div
      data-testid="attachment-preview"
      className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs"
    >
      📎 {file.name}
      <button
        onClick={onRemove}
        className="ml-1 text-blue-400 hover:text-blue-600"
        aria-label="移除附件"
      >
        ×
      </button>
    </div>
  );
}
