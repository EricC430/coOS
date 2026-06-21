/**
 * M3.4 -- LaTeX & Markdown Renderer
 *
 * Parses $inline$ and $$display$$ math in message content.
 * Renders Markdown content using marked.
 * Uses KaTeX for rendering math; falls back to original text on error.
 */

import React from "react";
import katex from "katex";
import { marked } from "marked";
import "katex/dist/katex.min.css";

interface LatexRendererProps {
  content: string;
}

// Configure marked options
marked.setOptions({
  gfm: true,
  breaks: true,
});

/**
 * Parses LaTeX display and inline equations, replaces them with unique tokens,
 * runs the Markdown parser, and then substitutes KaTeX-rendered HTML back.
 */
function renderMarkdownWithKatex(content: string): string {
  const inlineFormulas: string[] = [];
  const displayFormulas: string[] = [];

  // Temporarily replace display math ($$...$$)
  let processed = content.replace(/\$\$([\s\S]+?)\$\$/g, (_, formula) => {
    displayFormulas.push(formula);
    return `LATEXDISPLAYTOKEN${displayFormulas.length - 1}LATEXDISPLAYTOKEN`;
  });

  // Temporarily replace inline math ($...$)
  processed = processed.replace(/\$([^$\n]+?)\$/g, (_, formula) => {
    inlineFormulas.push(formula);
    return `LATEXINLINETOKEN${inlineFormulas.length - 1}LATEXINLINETOKEN`;
  });

  // Parse Markdown using marked
  let html = "";
  try {
    html = marked.parse(processed, { async: false }) as string;
  } catch (e) {
    html = processed;
  }

  // Restore display formulas
  html = html.replace(/LATEXDISPLAYTOKEN(\d+)LATEXDISPLAYTOKEN/g, (_, idxStr) => {
    const idx = parseInt(idxStr, 10);
    const formula = displayFormulas[idx];
    try {
      const rendered = katex.renderToString(formula, {
        displayMode: true,
        throwOnError: false,
        output: "html",
      });
      return `<div class="katex-display-block" style="display: block; text-align: center; margin: 0.5em 0; overflow-x: auto;">${rendered}</div>`;
    } catch {
      return `$$${formula}$$`;
    }
  });

  // Restore inline formulas
  html = html.replace(/LATEXINLINETOKEN(\d+)LATEXINLINETOKEN/g, (_, idxStr) => {
    const idx = parseInt(idxStr, 10);
    const formula = inlineFormulas[idx];
    try {
      return katex.renderToString(formula, {
        displayMode: false,
        throwOnError: false,
        output: "html",
      });
    } catch {
      return `$${formula}$`;
    }
  });

  return html;
}

export function LatexRenderer({ content }: LatexRendererProps) {
  const htmlContent = renderMarkdownWithKatex(content);

  return (
    <div
      className="chat-markdown"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}
