/**
 * M1.3.2 unit tests — domain bucketing + URL scrubbing
 *
 * SPEC: docs/modules/M1_3_2_browser_extension_SPEC.md
 * Research:
 *   [R02: 時間動力學 §1.2] Page dwell time as reading depth indicator
 *   [R06: 數位表型 §2.1] Browsing pattern (social vs learning ratio) as digital phenotype
 */
import { describe, it, expect } from 'vitest';
import { classifyDomain, getCleanPathAndDomain } from '../classify.js';

// ---------------------------------------------------------------------------
// AC-3 / AC-4: Domain bucketing
// ---------------------------------------------------------------------------
describe('classifyDomain', () => {
  const defaultRules = {
    'github.com': 'coding',
    'stackoverflow.com': 'learning',
    'youtube.com': 'entertainment',
    'notion.so': 'productivity',
    'twitter.com': 'social',
    'x.com': 'social',
    'docs.python.org': 'learning',
    'arxiv.org': 'learning',
    'figma.com': 'productivity',
    'slack.com': 'communication',
    'discord.com': 'communication',
  };

  it('AC-3: github.com → coding', () => {
    expect(classifyDomain('github.com', defaultRules)).toBe('coding');
  });

  it('AC-4: stackoverflow.com → learning', () => {
    expect(classifyDomain('stackoverflow.com', defaultRules)).toBe('learning');
  });

  it('youtube.com → entertainment', () => {
    expect(classifyDomain('youtube.com', defaultRules)).toBe('entertainment');
  });

  it('subdomain match: sub.github.com → coding', () => {
    // SPEC §7.1: suffix match — subdomain inherits parent bucket
    expect(classifyDomain('sub.github.com', defaultRules)).toBe('coding');
  });

  it('www. prefix is stripped before matching', () => {
    expect(classifyDomain('www.github.com', defaultRules)).toBe('coding');
  });

  it('unknown domain → "unknown"', () => {
    expect(classifyDomain('some-random-site.xyz', defaultRules)).toBe('unknown');
  });

  it('empty rules returns unknown', () => {
    expect(classifyDomain('github.com', {})).toBe('unknown');
  });
});

// ---------------------------------------------------------------------------
// AC-5: URL scrubbing — sensitive query params removed
// ---------------------------------------------------------------------------
describe('getCleanPathAndDomain', () => {
  it('AC-5: strips query params from URL', () => {
    const result = getCleanPathAndDomain('https://github.com/user/repo/issues/1?token=secret123');
    expect(result.domain).toBe('github.com');
    expect(result.url_path).toBe('/user/repo/issues/1');
    expect(result.url_path).not.toContain('secret123');
    expect(result.url_path).not.toContain('token');
  });

  it('strips hash fragment', () => {
    const result = getCleanPathAndDomain('https://docs.python.org/3/library/os.html#os.getenv');
    expect(result.url_path).toBe('/3/library/os.html');
    expect(result.url_path).not.toContain('#');
  });

  it('strips www. from domain', () => {
    const result = getCleanPathAndDomain('https://www.github.com/user/repo');
    expect(result.domain).toBe('github.com');
  });

  it('handles invalid URL gracefully', () => {
    const result = getCleanPathAndDomain('not-a-url');
    expect(result.domain).toBe('unknown');
    expect(result.url_path).toBe('');
  });

  it('preserves path without query', () => {
    const result = getCleanPathAndDomain('https://stackoverflow.com/questions/123/my-question');
    expect(result.url_path).toBe('/questions/123/my-question');
  });
});

// ---------------------------------------------------------------------------
// AC-1 / AC-2: Short tab stay filtering (< 5s not recorded)
// ---------------------------------------------------------------------------
describe('shouldRecordStay', () => {
  it('AC-1: stay >= 5s should be recorded', async () => {
    const { shouldRecordStay } = await import('../classify.js');
    expect(shouldRecordStay(600)).toBe(true);
  });

  it('AC-2: stay < 5s should NOT be recorded', async () => {
    const { shouldRecordStay } = await import('../classify.js');
    expect(shouldRecordStay(3)).toBe(false);
  });

  it('boundary: exactly 5s should be recorded', async () => {
    const { shouldRecordStay } = await import('../classify.js');
    expect(shouldRecordStay(5)).toBe(true);
  });
});
