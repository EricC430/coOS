/**
 * M1.3.1 unit tests — collaboration heuristics + entropy
 *
 * SPEC: docs/modules/M1_3_1_vscode_extension_SPEC.md
 * Research:
 *   [R02: 源碼變更熵 §1.1] Shannon Entropy H = -Σ pᵢ log(pᵢ)
 *   [R02: 時間動力學 §1.2] Save interval burst = anxiety/debug cycle
 */
import { describe, it, expect } from 'vitest';
import { calculateChangeEntropy } from '../collaboration';
import { analyzeCollaboration, calculateChurnIndex } from '../collaboration';

// ---------------------------------------------------------------------------
// AC-1: Single file edit → low entropy
// ---------------------------------------------------------------------------
describe('calculateChangeEntropy', () => {
  it('AC-1: single file edit produces entropy < 0.1', () => {
    // [R02: 源碼變更熵 §1.1] All edits in one file → max concentration → H ≈ 0
    const counts = new Map([['main.py', 50]]);
    const result = calculateChangeEntropy(counts);
    expect(result).toBeLessThan(0.1);
  });

  it('AC-2: equal edits across 4 files produces entropy > 0.8', () => {
    // [R02: 源碼變更熵 §1.1] Equal distribution → H = log2(4)/log2(4) = 1.0
    const counts = new Map([
      ['a.py', 10], ['b.py', 10], ['c.py', 10], ['d.py', 10],
    ]);
    const result = calculateChangeEntropy(counts);
    expect(result).toBeGreaterThan(0.8);
  });

  it('returns 0 for empty map', () => {
    expect(calculateChangeEntropy(new Map())).toBe(0);
  });

  it('returns 0 for zero total edits', () => {
    const counts = new Map([['main.py', 0]]);
    expect(calculateChangeEntropy(counts)).toBe(0);
  });

  it('entropy is normalized to [0, 1]', () => {
    const counts = new Map([['a.ts', 30], ['b.ts', 70]]);
    const result = calculateChangeEntropy(counts);
    expect(result).toBeGreaterThanOrEqual(0);
    expect(result).toBeLessThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// AC-3: Human vs AI typing heuristics
// ---------------------------------------------------------------------------
describe('analyzeCollaboration', () => {
  it('large instant insertion classified as AI_GENERATION', () => {
    // [R02: §時間動力學] > 30 chars inserted in < 50ms → AI block paste
    const result = analyzeCollaboration({ insertedChars: 200, deletedChars: 0, timeDeltaMs: 10 });
    expect(result).toBe('AI_GENERATION');
  });

  it('single character typed classified as HUMAN_TYPING', () => {
    const result = analyzeCollaboration({ insertedChars: 1, deletedChars: 0, timeDeltaMs: 150 });
    expect(result).toBe('HUMAN_TYPING');
  });

  it('large deletion classified as BULK_DELETE', () => {
    const result = analyzeCollaboration({ insertedChars: 0, deletedChars: 50, timeDeltaMs: 100 });
    expect(result).toBe('BULK_DELETE');
  });

  it('5-char insertion with normal interval is HUMAN_TYPING', () => {
    const result = analyzeCollaboration({ insertedChars: 5, deletedChars: 0, timeDeltaMs: 200 });
    expect(result).toBe('HUMAN_TYPING');
  });
});

// ---------------------------------------------------------------------------
// AC-4 (Churn Index): repeated AI generation after bulk delete
// ---------------------------------------------------------------------------
describe('calculateChurnIndex', () => {
  it('no churn events produces index 0', () => {
    const events = [
      { insertedChars: 5, deletedChars: 0, timeDeltaMs: 200 },
      { insertedChars: 5, deletedChars: 0, timeDeltaMs: 200 },
    ];
    expect(calculateChurnIndex(events)).toBe(0);
  });

  it('bulk delete followed by large AI insert produces high churn index', () => {
    // [R02: §時間動力學] Delete > 50 then AI insert > 50 in < 1s = churn
    const events = [
      { insertedChars: 0, deletedChars: 100, timeDeltaMs: 500 },
      { insertedChars: 150, deletedChars: 0, timeDeltaMs: 300 },  // AI regeneration
    ];
    const index = calculateChurnIndex(events);
    expect(index).toBeGreaterThan(0);
  });

  it('churn index is in [0, 1] range', () => {
    const events = [
      { insertedChars: 0, deletedChars: 200, timeDeltaMs: 100 },
      { insertedChars: 200, deletedChars: 0, timeDeltaMs: 200 },
      { insertedChars: 0, deletedChars: 200, timeDeltaMs: 100 },
      { insertedChars: 200, deletedChars: 0, timeDeltaMs: 200 },
    ];
    const index = calculateChurnIndex(events);
    expect(index).toBeGreaterThanOrEqual(0);
    expect(index).toBeLessThanOrEqual(1);
  });

  it('empty events array produces index 0', () => {
    expect(calculateChurnIndex([])).toBe(0);
  });
});
