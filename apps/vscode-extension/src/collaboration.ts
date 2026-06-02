/**
 * M1.3.1 Collaboration heuristics + Shannon Entropy
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md §7.1, §7.4
 * Research:
 *   [R02: 源碼變更熵 §1.1] H = -Σ pᵢ log₂(pᵢ), normalised by log₂(N)
 *   [R02: 時間動力學 §1.2] Save interval burst = anxiety/debug cycle indicator
 */

import type { EditChunk, CollaborationType } from './types';

/**
 * [R02: 源碼變更熵 §1.1] Calculate normalised Shannon Entropy of edit distribution.
 *
 * H = -Σ pᵢ log₂(pᵢ)  normalised to [0,1] by dividing by log₂(N).
 * Low entropy → concentrated edits (single file focus).
 * High entropy → scattered edits across many files.
 */
export function calculateChangeEntropy(editCounts: Map<string, number>): number {
  if (editCounts.size === 0) return 0;

  const total = Array.from(editCounts.values()).reduce((a, b) => a + b, 0);
  if (total === 0) return 0;

  let entropy = 0;
  for (const count of editCounts.values()) {
    const p = count / total;
    if (p > 0) entropy -= p * Math.log2(p);
  }

  // Normalise to [0, 1]
  const maxEntropy = Math.log2(editCounts.size);
  return maxEntropy > 0 ? entropy / maxEntropy : 0;
}

/**
 * [R02: 時間動力學 §1.2] Heuristic: distinguish human typing from AI block generation.
 *
 * AI generation: large insertion (> 30 chars) in very short time (< 50ms).
 * Human typing: small insertion (1-5 chars) at normal pace (50-800ms).
 * Bulk delete: large deletion with no insertion.
 */
export function analyzeCollaboration(chunk: EditChunk): CollaborationType {
  if (chunk.insertedChars > 30 && chunk.timeDeltaMs < 50) {
    return 'AI_GENERATION';
  }
  if (chunk.deletedChars > 10 && chunk.insertedChars === 0) {
    return 'BULK_DELETE';
  }
  if (chunk.insertedChars > 0 && chunk.insertedChars <= 5) {
    return 'HUMAN_TYPING';
  }
  // Default: human typing (covers medium insertions at normal pace)
  return 'HUMAN_TYPING';
}

/**
 * [R02: 時間動力學 §1.2] Calculate Agent Churn Index for a sequence of edit chunks.
 *
 * Churn = proportion of total changes that follow a delete→AI-insert pattern.
 * High churn (→ 1.0): developer stuck in a bug loop with AI agent.
 * Low churn (→ 0.0): steady forward progress.
 */
export function calculateChurnIndex(events: EditChunk[]): number {
  if (events.length < 2) return 0;

  let churnScore = 0;
  let totalChange = 0;

  for (let i = 1; i < events.length; i++) {
    const prev = events[i - 1];
    const curr = events[i];
    totalChange += curr.insertedChars + curr.deletedChars;

    // Churn pattern: large delete followed by AI-scale insert within 1 second
    if (
      prev.deletedChars > 50 &&
      curr.insertedChars > 50 &&
      curr.timeDeltaMs < 1000
    ) {
      churnScore += prev.deletedChars + curr.insertedChars;
    }
  }

  if (totalChange === 0) return 0;
  return Math.min(1, churnScore / totalChange);
}
