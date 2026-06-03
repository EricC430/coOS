/**
 * M3.2.3 -- Context Header Aggregator (Short-Term Memory Recall)
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS1.1
 * Shows 4-slot header: Project | Role | Promises | Goal
 * [R08 SS1] Skeleton UI prevents layout shift during load
 * [RISK-06] Waits for ROLE_CONTEXT_SYNCED before showing real data
 */

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRoleContext } from "./useRoleContextCache";

interface ContextData {
  project?: { name: string };
  promises?: string[];
  goals?: string[];
  role?: { name: string };
}

interface Props {
  roleId: string;
  roleName?: string;
}

function SkeletonSlot() {
  return (
    <div
      data-testid="skeleton-loader"
      className="h-8 rounded-md bg-gray-200 animate-pulse"
    />
  );
}

export function ContextHeaderAggregator({ roleId, roleName }: Props) {
  const { data, isLoading, error } = useQuery<ContextData>({
    queryKey: ["role_context", roleId],
    queryFn: () => fetchRoleContext(roleId),
    staleTime: 60_000,
    retry: 2,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-3 px-4 py-3" data-testid="context-header">
        <SkeletonSlot />
        <SkeletonSlot />
        <SkeletonSlot />
        <SkeletonSlot />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-3 px-4 py-3 text-sm" data-testid="context-header">
      {/* Project slot */}
      <div data-testid="project-slot" className="bg-white/10 rounded-lg p-2">
        <div className="text-xs text-gray-400 uppercase tracking-wide">Project</div>
        <div className="font-medium truncate">{data?.project?.name ?? "—"}</div>
      </div>

      {/* Role slot -- most prominent */}
      <div data-testid="role-slot" className="bg-white/20 rounded-lg p-2 text-center">
        <div className="text-xs text-gray-400 uppercase tracking-wide">Role</div>
        <div className="font-bold text-base">{roleName ?? data?.role?.name ?? "—"}</div>
      </div>

      {/* Promises slot */}
      <div data-testid="promises-slot" className="bg-white/10 rounded-lg p-2">
        <div className="text-xs text-gray-400 uppercase tracking-wide">Promises</div>
        <div className="truncate">{data?.promises?.[0] ?? "—"}</div>
      </div>

      {/* Goal slot */}
      <div data-testid="goal-slot" className="bg-white/10 rounded-lg p-2">
        <div className="text-xs text-gray-400 uppercase tracking-wide">Goal</div>
        <div className="truncate">{data?.goals?.[0] ?? "—"}</div>
      </div>
    </div>
  );
}
