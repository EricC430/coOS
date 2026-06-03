/**
 * M3.3.2 -- Dual-track time fallback
 * [R08 SS5] AI inquiry result takes priority; telemetry is fallback
 */

export type TimeSource = "ai_inquiry" | "telemetry_estimate";

export interface TimeSpentResult {
  time_spent_minutes: number;
  source: TimeSource;
}

export async function resolveTimeSpent(taskId: string): Promise<TimeSpentResult> {
  try {
    const res = await fetch(`/api/m4_4/time_spent/${taskId}`);
    if (res.ok) {
      const data = await res.json();
      if (data?.time_spent_minutes) {
        return { time_spent_minutes: data.time_spent_minutes, source: "ai_inquiry" };
      }
    }
  } catch {
    // fall through
  }

  // Fallback: telemetry
  try {
    const res = await fetch(`/api/m1_1/telemetry_estimate/${taskId}`);
    if (res.ok) {
      const data = await res.json();
      return {
        time_spent_minutes: data?.duration_minutes ?? 0,
        source: "telemetry_estimate",
      };
    }
  } catch {
    // fall through
  }

  return { time_spent_minutes: 0, source: "telemetry_estimate" };
}
