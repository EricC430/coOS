/**
 * M3.3.3 -- Draft Approve Modal (Core Psychological Mechanism)
 *
 * SPEC: docs/modules/M3_3_daily_report_reflection_SPEC.md SS7.1
 * [R08 SS6.1] IKEA Effect: user fills own reflection -> psychological ownership
 * [R08 SS4.2] Micro-friction: blank fields are intentional, not removable
 * @risk RISK-01: Approve button only fires XP API AFTER is_reviewed written to DB
 *
 * Anti-patterns:
 *   Never auto-fill user_feeling or user_action_plan
 *   Never call XP API before PATCH is_reviewed=true succeeds
 *   Never embed as inline form -- must be full-screen modal overlay
 */

import React, { useState } from "react";
import { GibbsReflectionForm } from "./GibbsReflectionForm";
import { useApprovalGuard, type DailyReflection } from "./useApprovalGuard";

interface Props {
  reflection: DailyReflection;
  onApproved?: () => void;
  onClose?: () => void;
}

export function DraftApproveModal({ reflection, onApproved, onClose }: Props) {
  const [feeling, setFeeling] = useState(reflection.user_feeling);
  const [actionPlan, setActionPlan] = useState(reflection.user_action_plan);
  const [lesson, setLesson] = useState(reflection.learned_lesson ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const draft: DailyReflection = {
    ...reflection,
    user_feeling: feeling,
    user_action_plan: actionPlan,
    learned_lesson: lesson,
  };

  const { isValid, approve } = useApprovalGuard(draft);

  const handleApprove = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await approve();
      onApproved?.();
    } catch (e) {
      setError("核准失敗，請重試");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Full-screen overlay -- [R08 SS6.2] cuts user off from other UI for focused reflection
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="draft-approve-modal"
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b">
          <h2 className="text-lg font-semibold">完成今日反思 +XP</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="關閉"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-4">
          <GibbsReflectionForm
            aiDescription={reflection.ai_description}
            aiAnalysis={reflection.ai_analysis}
            userFeeling={feeling}
            userActionPlan={actionPlan}
            learnedLesson={lesson}
            onFeelingChange={setFeeling}
            onActionPlanChange={setActionPlan}
            onLearnedLessonChange={setLesson}
          />
        </div>

        {error && (
          <p className="px-6 text-sm text-red-500">{error}</p>
        )}

        <div className="flex justify-end gap-3 px-6 pb-5 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            稍後再說
          </button>
          {/* [RISK-01] Disabled until BOTH required fields are filled */}
          <button
            data-testid="approve-btn"
            onClick={handleApprove}
            disabled={!isValid || submitting}
            className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-indigo-700 transition-colors"
          >
            {submitting ? "核准中..." : "核准並領取 XP"}
          </button>
        </div>
      </div>
    </div>
  );
}
