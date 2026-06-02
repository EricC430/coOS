/**
 * M1.3.2 Domain classification + URL scrubbing
 *
 * SPEC: docs/modules/M1_3_2_browser_extension_SPEC.md §7.1
 * Research:
 *   [R06: 數位表型 §2.1] Browsing pattern as digital phenotype input
 *   [R02: 時間動力學 §1.2] Page dwell time as reading depth indicator
 *
 * Privacy:
 *   - URL query params and hash fragments are ALWAYS stripped [RISK-15]
 *   - title stored only when CaptureMode is AllApps/SelectedApps
 *   - domain bucket and clean path are the only persistent fields
 */

const MIN_STAY_S = 5; // AC-2: < 5s stays not recorded

/**
 * [R06: 數位表型 §2.1] Classify a hostname against the rules map.
 * Supports exact match and suffix match (sub.domain.com matches domain.com).
 *
 * @param {string} hostname - raw hostname (may include www.)
 * @param {Record<string, string>} rules - { "github.com": "coding", ... }
 * @returns {string} bucket name or "unknown"
 */
export function classifyDomain(hostname, rules) {
  const clean = hostname.replace(/^www\./, '');
  for (const [pattern, bucket] of Object.entries(rules)) {
    if (clean === pattern || clean.endsWith('.' + pattern)) {
      return bucket;
    }
  }
  return 'unknown';
}

/**
 * [RISK-15] Strip query params and hash from URL, extract domain.
 * Returns clean domain + path only — never exposes tokens or sensitive params.
 *
 * @param {string} urlStr - full URL string
 * @returns {{ domain: string, url_path: string }}
 */
export function getCleanPathAndDomain(urlStr) {
  try {
    const url = new URL(urlStr);
    const domain = url.hostname.replace(/^www\./, '');
    // pathname only — no search params, no hash
    return { domain, url_path: url.pathname };
  } catch {
    return { domain: 'unknown', url_path: '' };
  }
}

/**
 * [R02: 時間動力學 §1.2] Only record tab stays >= MIN_STAY_S.
 * Rapid tab switches (browsing noise) are discarded.
 *
 * @param {number} stayS - stay duration in seconds
 * @returns {boolean}
 */
export function shouldRecordStay(stayS) {
  return stayS >= MIN_STAY_S;
}
