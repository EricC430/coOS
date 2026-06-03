/**
 * M3.3.3.2 -- Gibbs Reflection Form
 * [R08 SS6.2] 6-phase Gibbs Cycle: AI fills Description+Evaluation, user fills Feelings+ActionPlan
 * Anti-pattern: NEVER auto-fill user_feeling or user_action_plan -- IKEA effect requires user labour
 */

import React from "react";

interface Props {
  aiDescription: string;
  aiAnalysis?: string;
  userFeeling: string;
  userActionPlan: string;
  learnedLesson?: string;
  onFeelingChange: (v: string) => void;
  onActionPlanChange: (v: string) => void;
  onLearnedLessonChange?: (v: string) => void;
}

export function GibbsReflectionForm({
  aiDescription,
  aiAnalysis,
  userFeeling,
  userActionPlan,
  learnedLesson,
  onFeelingChange,
  onActionPlanChange,
  onLearnedLessonChange,
}: Props) {
  return (
    <div className="space-y-4">
      {/* Description -- AI filled */}
      <div>
        <label className="text-xs text-gray-400 uppercase tracking-wide">客觀描述 (AI)</label>
        <p
          data-testid="ai-description"
          className="mt-1 text-sm bg-gray-50 rounded p-2 text-gray-600"
        >
          {aiDescription || "AI 草稿尚未生成，你也可以先自行填寫"}
        </p>
      </div>

      {/* Feelings -- user MUST fill */}
      <div>
        <label className="text-xs text-gray-400 uppercase tracking-wide">
          主觀感受 <span className="text-red-500">*必填</span>
        </label>
        <textarea
          data-testid="user-feeling-input"
          className="mt-1 w-full border rounded p-2 text-sm resize-none"
          rows={3}
          value={userFeeling}
          onChange={(e) => onFeelingChange(e.target.value)}
          // [R08 SS4.2] Forced blank: placeholder signals requirement, no default text
          placeholder="(必填) 你有什麼感受？焦慮？有成就感？..."
        />
      </div>

      {/* Evaluation/Analysis -- AI filled */}
      {aiAnalysis && (
        <div>
          <label className="text-xs text-gray-400 uppercase tracking-wide">初步分析 (AI)</label>
          <p className="mt-1 text-sm bg-gray-50 rounded p-2 text-gray-600">{aiAnalysis}</p>
        </div>
      )}

      {/* Conclusion -- optional user */}
      <div>
        <label className="text-xs text-gray-400 uppercase tracking-wide">學到了什麼 (選填)</label>
        <textarea
          data-testid="learned-lesson-input"
          className="mt-1 w-full border rounded p-2 text-sm resize-none"
          rows={2}
          value={learnedLesson ?? ""}
          onChange={(e) => onLearnedLessonChange?.(e.target.value)}
          placeholder="有沒有什麼新的洞察或理解？"
        />
      </div>

      {/* Action Plan -- user MUST fill */}
      <div>
        <label className="text-xs text-gray-400 uppercase tracking-wide">
          行動計畫 <span className="text-red-500">*必填</span>
        </label>
        <textarea
          data-testid="user-action-plan-input"
          className="mt-1 w-full border rounded p-2 text-sm resize-none"
          rows={3}
          value={userActionPlan}
          onChange={(e) => onActionPlanChange(e.target.value)}
          placeholder="(必填) 接下來你打算怎麼做？"
        />
      </div>
    </div>
  );
}
