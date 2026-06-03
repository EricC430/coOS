/**
 * M3.3.1 -- Single day timeline group
 * Groups tasks by role_id within a single date.
 */

import React, { useState } from "react";
import { TimeCard } from "../TimeCard";
import { DraftApproveModal } from "../DraftApproveModal";
import type { DailyReflection } from "../DraftApproveModal/useApprovalGuard";

export interface TaskItem {
  id: string;
  roleId: string;
  roleName: string;
  title: string;
  status: "in_progress" | "completed";
  reflection?: DailyReflection;
}

interface Props {
  date: string;
  tasks: TaskItem[];
  currentRoleId?: string;
}

export function TimelineDay({ date, tasks, currentRoleId }: Props) {
  const [approveTarget, setApproveTarget] = useState<DailyReflection | null>(null);

  // Group by role
  const byRole: Record<string, TaskItem[]> = {};
  for (const t of tasks) {
    if (!byRole[t.roleId]) byRole[t.roleId] = [];
    byRole[t.roleId].push(t);
  }

  return (
    <div className="flex gap-4">
      {/* Left timeline */}
      <div className="w-16 flex-shrink-0 text-right text-xs text-gray-400 pt-1">
        {date}
      </div>

      {/* Right content */}
      <div className="flex-1 space-y-3">
        {Object.entries(byRole).map(([roleId, roleTasks]) => (
          <div
            key={roleId}
            className="border rounded-lg p-3 bg-white/50"
            data-testid={`role-group-${roleId}`}
          >
            <div className="text-xs font-semibold text-gray-500 mb-2">
              {roleTasks[0]?.roleName ?? roleId}
            </div>

            {roleTasks.map((task) => (
              <div
                key={task.id}
                data-testid="task-card"
                data-role-id={task.roleId}
                className="flex items-start justify-between py-1.5 border-b last:border-0"
              >
                <div className="flex-1">
                  <div className="text-sm font-medium">{task.title}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        task.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : "bg-yellow-100 text-yellow-700"
                      }`}
                    >
                      {task.status === "completed" ? "已完成" : "正在進行中"}
                    </span>
                    {task.id && <TimeCard taskId={task.id} />}
                  </div>
                  {task.reflection?.user_feeling && (
                    <div className="text-xs text-gray-500 mt-0.5">
                      學到了：{task.reflection.user_feeling}
                    </div>
                  )}
                </div>

                <button
                  className={`text-xs ml-2 px-2 py-1 rounded ${
                    task.reflection?.is_reviewed
                      ? "text-green-600"
                      : "text-blue-500 hover:bg-blue-50"
                  }`}
                  onClick={() => {
                    if (!task.reflection?.is_reviewed && task.reflection) {
                      setApproveTarget(task.reflection);
                    }
                  }}
                  data-testid={`review-btn-${task.id}`}
                >
                  {task.reflection?.is_reviewed ? "reviewed ✓" : "reviewed? click"}
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      {approveTarget && (
        <DraftApproveModal
          reflection={approveTarget}
          onApproved={() => setApproveTarget(null)}
          onClose={() => setApproveTarget(null)}
        />
      )}
    </div>
  );
}
