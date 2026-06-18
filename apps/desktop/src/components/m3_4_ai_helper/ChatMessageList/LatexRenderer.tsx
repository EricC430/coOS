/**
 * M3.4 -- LaTeX Renderer
 *
 * Parses $inline$ and $$display$$ math in message content.
 * Uses KaTeX for rendering; falls back to original text on error.
 *
 * [FIX-07] Resolves LaTeX rendering failure in chat messages.
 */

import React from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

interface LatexRendererProps {
  content: string;
}

/**
 * Splits text into segments: plain text, inline math ($...$), and display math ($$...$$).
 */
function parseSegments(text: string): Array<{ type: "text" | "inline" | "display"; value: string }> {
  const segments: Array<{ type: "text" | "inline" | "display"; value: string }> = [];
  // Regex: match $$...$$ first (display), then $...$ (inline)
  const re = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      segments.push({ type: "text", value: text.slice(last, match.index) });
    }
    const raw = match[1];
    if (raw.startsWith("$$")) {
      segments.push({ type: "display", value: raw.slice(2, -2) });
    } else {
      segments.push({ type: "inline", value: raw.slice(1, -1) });
    }
    last = match.index + raw.length;
  }
  if (last < text.length) {
    segments.push({ type: "text", value: text.slice(last) });
  }
  return segments;
}

function renderKatex(formula: string, displayMode: boolean): string {
  try {
    return katex.renderToString(formula, {
      displayMode,
      throwOnError: false,
      output: "html",
    });
  } catch {
    return formula;
  }
}

export function LatexRenderer({ content }: LatexRendererProps) {
  const segments = parseSegments(content);

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "text") {
          return <span key={i}>{seg.value}</span>;
        }
        const html = renderKatex(seg.value, seg.type === "display");
        return (
          <span
            key={i}
            dangerouslySetInnerHTML={{ __html: html }}
            style={seg.type === "display" ? { display: "block", textAlign: "center", margin: "4px 0" } : undefined}
          />
        );
      })}
    </>
  );
}
