/**
 * M3.4.4.2 -- Project Card with Endowed Progress Effect
 * [R01 §DDA] Non-zero initial progress bar activates Goal Gradient
 * Initial progress <= 30% to avoid misleading user
 */

import React from "react";

export interface ProjectInfo {
  id: string;
  name: string;
  intention?: string;
  summary?: string;
  deadline?: string;
  tasks?: unknown[];
  progress_override?: number;
}

function computeInitialProgress(project: ProjectInfo): number {
  // [R01 §DDA] Goal Gradient: non-zero start
  let progress = 10;
  if (project.deadline) progress += 5;
  progress += Math.min((project.tasks?.length ?? 0), 10) * 3;
  return Math.min(progress, 30);
}

interface Props {
  project: ProjectInfo;
}

export function ProjectCard({ project }: Props) {
  const progress = project.progress_override ?? computeInitialProgress(project);

  return (
    <div className="bg-white border rounded-lg p-3 space-y-1">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium">📄 {project.name}</div>
          {project.intention && (
            <div className="text-xs text-gray-500 mt-0.5">{project.intention}</div>
          )}
        </div>
        {project.deadline && (
          <div className="text-xs text-gray-400 flex-shrink-0">{project.deadline}</div>
        )}
      </div>

      {/* Endowed progress bar */}
      <div className="relative h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          data-testid="project-progress"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-full bg-indigo-400 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {project.summary && (
        <div className="text-xs text-gray-400 line-clamp-2">{project.summary}</div>
      )}
    </div>
  );
}
