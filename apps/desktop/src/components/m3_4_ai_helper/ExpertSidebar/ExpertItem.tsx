/**
 * M3.4.1 -- Single expert sidebar item
 *
 * [FIX-03] Avatar: shows 🤖 for tool AI, expertName[0] for persona (no number corruption)
 * [FIX-06] All colours use CSS variables for dark mode
 */

import React from "react";
import type { Expert } from "../../../stores/m3_1_global_store";

interface Props {
  expert: Expert & { isToolType?: boolean };
  isActive: boolean;
  onClick: () => void;
  icon?: string;
  onDelete?: (expertId: string) => void;
}

export function ExpertItem({ expert, isActive, onClick, icon, onDelete }: Props) {
  const isToolType = expert.isToolType ?? false;

  // [FIX-03] Correctly determine avatar display:
  // - Tool AI: always 🤖 emoji
  // - Expert with avatarUrl: show image
  // - Expert without avatarUrl: show FIRST character of expertName (Chinese char like 志, 宏, etc.)
  let avatarContent: React.ReactNode;
  if (isToolType) {
    avatarContent = icon ?? "🤖";
  } else if (expert.avatarUrl) {
    avatarContent = (
      <img
        src={expert.avatarUrl}
        alt=""
        style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
      />
    );
  } else {
    // Use first character of expertName — for Chinese names this is the surname/first char
    avatarContent = expert.expertName.charAt(0) || "？";
  }

  return (
    <div
      data-testid="expert-item"
      data-type={isToolType ? "tool" : "persona"}
      className="expert-item"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        borderRadius: 8,
        cursor: "pointer",
        transition: "background 0.15s",
        margin: "2px 4px",
        position: "relative",
        // [FIX-06] Active state uses CSS vars; background-image for stripe pattern
        background: isActive ? "var(--role-primary-faint, rgba(99,102,241,0.12))" : "transparent",
        backgroundImage: isActive
          ? "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(99,102,241,0.07) 4px, rgba(99,102,241,0.07) 8px)"
          : undefined,
      }}
      onClick={onClick}
    >
      {/* Avatar circle */}
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          // [FIX-06] Tool AI gets a distinct bg, persona gets gold-accent
          background: isToolType ? "var(--glass-border)" : "var(--gold-accent)",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: isToolType ? 16 : 14,
          fontWeight: 700,
          color: "white",
          overflow: "hidden",
        }}
      >
        {avatarContent}
      </div>

      {/* Name & title */}
      <div style={{ minWidth: 0, flex: 1 }}>
        {expert.title && (
          <div style={{
            fontSize: 10,
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}>
            {expert.title}
          </div>
        )}
        <div style={{
          fontSize: 13,
          fontWeight: isActive ? 600 : 500,
          color: isActive ? "var(--role-primary, #6366f1)" : "var(--text-primary)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}>
          {expert.expertName}
        </div>
      </div>

      {/* Delete button */}
      {!isToolType && onDelete && (
        <button
          data-testid="expert-delete-btn"
          className="expert-delete-btn"
          style={{
            opacity: 0,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-muted)",
            fontSize: 12,
            padding: "0 4px",
            transition: "opacity 0.15s, color 0.15s",
          }}
          onClick={(e) => {
            e.stopPropagation();
            onDelete(expert.id);
          }}
          title="移除專家"
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = "1";
            (e.currentTarget as HTMLButtonElement).style.color = "#ef4444";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = "0";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
