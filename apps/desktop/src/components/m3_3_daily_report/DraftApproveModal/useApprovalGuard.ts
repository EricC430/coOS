/**
 * M3.3.3 -- Approval Guard
 *
 * [R08 SS6.1 IKEA Effect] User MUST fill in their own reflection before XP is granted.
 * [R08 SS6.2 Gibbs] 6-phase form: AI fills Description+Evaluation, user fills Feelings+ActionPlan.
 * @risk RISK-01: XP MUST NOT be requested before is_reviewed=true is confirmed in DB
 */

export interface DailyReflection {
  id: string;
  ai_description: string;
  ai_analysis?: string;
  user_feeling: string;
  user_action_plan: string;
  learned_lesson?: string;
  is_draft: boolean;
  is_reviewed: boolean;
}

export function useApprovalGuard(reflection: DailyReflection) {
  const isValid =
    reflection.user_feeling.trim().length > 0 &&
    reflection.user_action_plan.trim().length > 0 &&
    reflection.ai_description.length > 0;

  const approve = async (): Promise<void> => {
    if (!isValid) throw new Error("validation_failed");

    // [RISK-01] Step 1: write user fields + set is_reviewed=true FIRST
    const patchRes = await fetch(`/api/m6_4/reflections/${reflection.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_feeling: reflection.user_feeling,
        user_action_plan: reflection.user_action_plan,
        learned_lesson: reflection.learned_lesson ?? null,
        is_draft: false,
        is_reviewed: true,
      }),
    });
    if (!patchRes.ok) throw new Error("patch_failed");

    // [RISK-01] Step 2: only then request XP settlement
    const xpRes = await fetch(`/api/m4_5/grant_xp`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reflection_id: reflection.id, is_reviewed: true }),
    });
    if (!xpRes.ok) throw new Error("xp_grant_failed");
  };

  return { isValid, approve };
}
