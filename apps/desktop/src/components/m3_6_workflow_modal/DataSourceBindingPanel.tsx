/**
 * M3.6.2 -- Data Source Binding Panel
 * [RISK-12] GitHub webhook payload must NOT go directly to cloud LLM
 * Privacy notice displayed inline
 */

import React, { useState } from "react";

export type SourceType = "github" | "obsidian" | "browser";

export interface DataSource {
  type: SourceType;
  status: "connected" | "disconnected";
  config?: Record<string, string>;
}

interface Props {
  sources: DataSource[];
  onBind: (sourceType: SourceType, config: Record<string, string>) => Promise<void>;
}

const SOURCE_ICONS: Record<SourceType, string> = {
  github: "⬡",
  obsidian: "🔮",
  browser: "🌐",
};

const SOURCE_LABELS: Record<SourceType, string> = {
  github: "GitHub Repo",
  obsidian: "Obsidian Vault",
  browser: "瀏覽器紀錄",
};

export function DataSourceBindingPanel({ sources, onBind }: Props) {
  const [githubRepo, setGithubRepo] = useState("");
  const [loading, setLoading] = useState<SourceType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sourceMap = Object.fromEntries(sources.map((s) => [s.type, s]));

  const connectGithub = async () => {
    if (!githubRepo.trim()) return;
    setLoading("github");
    setError(null);
    try {
      await onBind("github", { repo: githubRepo.trim() });
    } catch {
      setError("GitHub 連線失敗");
    } finally {
      setLoading(null);
    }
  };

  const types: SourceType[] = ["github", "obsidian", "browser"];

  return (
    <div className="space-y-3">
      <div className="text-sm font-medium text-gray-600">connect to</div>
      <div className="flex gap-2">
        {types.map((type) => {
          const src = sourceMap[type];
          return (
            <div
              key={type}
              data-testid={`source-${type}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm cursor-pointer"
              style={{
                background: src?.status === "connected" ? "#dcfce7" : undefined,
                borderColor: src?.status === "connected" ? "#16a34a" : undefined,
              }}
            >
              {SOURCE_ICONS[type]} {SOURCE_LABELS[type]}
              {src?.status === "connected" && (
                <span data-testid={`source-${type}-badge`} className="text-xs text-green-700 ml-1">
                  已連線
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* GitHub detail form */}
      <div className="space-y-1">
        <input
          data-testid="github-repo-input"
          className="w-full border rounded px-2 py-1 text-sm"
          placeholder="user/my-repo"
          value={githubRepo}
          onChange={(e) => setGithubRepo(e.target.value)}
        />
        <button
          data-testid="connect-github-btn"
          onClick={connectGithub}
          disabled={!githubRepo.trim() || loading === "github"}
          className="px-3 py-1 text-sm bg-gray-800 text-white rounded disabled:opacity-40"
        >
          {loading === "github" ? "連線中..." : "連線 GitHub"}
        </button>
        {/* [RISK-12] Privacy notice */}
        <p className="text-xs text-gray-400">
          ⓘ 僅事件觸發，原始 commit 訊息不上雲 LLM
        </p>
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
