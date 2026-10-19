/**
 * Small shared icon set (inline SVG, currentColor, 1.75px stroke).
 *
 * Replaces ad hoc emoji used as icons (🌿 🤖 ✨ 🔄 🎯 ✕ ...). Emoji render
 * inconsistently across OS/font and read as placeholder-quality next to the
 * app's glass-card treatment. Add new icons here rather than reaching for
 * another emoji.
 */
import type { SVGProps } from "react";

const base = {
  width: "1em",
  height: "1em",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function SparkleIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="M12 8l1.6 3.4L17 13l-3.4 1.6L12 18l-1.6-3.4L7 13l3.4-1.6z" />
    </svg>
  );
}

export function RefreshIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M3.5 12a8.5 8.5 0 0 1 14.5-6" />
      <path d="M20.5 12a8.5 8.5 0 0 1-14.5 6" />
      <path d="M18 6v-3M18 6h-3" />
      <path d="M6 18v3M6 18h3" />
    </svg>
  );
}

export function TargetIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.5" fill="currentColor" />
    </svg>
  );
}

export function SproutIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M12 21v-9" />
      <path d="M12 12c0-4 3-6 7-6 0 4-3 6-7 6Z" />
      <path d="M12 14c0-3.2-2.4-5-5.5-5-.2 3.2 2.3 5 5.5 5Z" />
    </svg>
  );
}

export function AssistantIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <rect x="4" y="8" width="16" height="12" rx="4" />
      <path d="M12 8V4" />
      <circle cx="12" cy="3" r="1" fill="currentColor" stroke="none" />
      <circle cx="9" cy="14" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="15" cy="14" r="1.2" fill="currentColor" stroke="none" />
      <path d="M2 13h2M20 13h2" />
    </svg>
  );
}

export function ChatIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M4 5h16v11H8l-4 4V5Z" />
    </svg>
  );
}

export function CloseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}
