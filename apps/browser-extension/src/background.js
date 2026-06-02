/**
 * M1.3.2 Browser Extension — Service Worker (background script)
 *
 * SPEC: docs/modules/M1_3_2_browser_extension_SPEC.md §7.1, §7.2
 * Research:
 *   [R02: 時間動力學 §1.2] Page dwell time as reading depth indicator
 *   [R06: 數位表型 §2.1] Browsing pattern (social vs learning) as digital phenotype
 *
 * Privacy:
 *   - No DOM access (no content script injected in Off mode)
 *   - URL params/hash stripped before storage [RISK-15]
 *   - title stored ONLY if CaptureMode is AllApps/SelectedApps
 *   - Incognito tabs ALWAYS skipped
 *
 * Supported: Chrome, Edge, Firefox (all use chrome.* namespace).
 */

'use strict';

import { classifyDomain, getCleanPathAndDomain, shouldRecordStay } from './classify.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let cachedRules = {};       // { "github.com": "coding", ... } — loaded from Tauri
let activeTabId = null;
let activeTabUrl = null;
let activeTabStart = null;  // timestamp ms when tab became active

// ---------------------------------------------------------------------------
// Rules: load from Tauri Native Messaging on startup + on update
// ---------------------------------------------------------------------------
function loadRulesFromHost() {
  chrome.runtime.sendNativeMessage('coos_native_host', { command: 'get_rules' }, (response) => {
    if (chrome.runtime.lastError) return; // host not installed yet — silent
    if (response && response.rules) {
      cachedRules = response.rules;
    }
  });
}

chrome.runtime.onInstalled.addListener(loadRulesFromHost);
chrome.runtime.onStartup.addListener(loadRulesFromHost);

// Dynamic rule updates from Tauri settings UI
chrome.runtime.onMessage.addListener((message) => {
  if (message.command === 'update_rules' && message.rules) {
    cachedRules = message.rules;
  }
});

// ---------------------------------------------------------------------------
// Tab tracking
// ---------------------------------------------------------------------------
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const now = Date.now();

  // Emit stay for previous tab
  if (activeTabUrl && activeTabStart !== null) {
    const stayS = Math.floor((now - activeTabStart) / 1000);
    await maybeEmitTabStay(activeTabUrl, stayS);
  }

  // Record new active tab
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.incognito) {
      // [M1.3.2 SPEC §8] NEVER record in incognito
      activeTabId = null;
      activeTabUrl = null;
      activeTabStart = null;
      return;
    }
    activeTabId = activeInfo.tabId;
    activeTabUrl = tab.url || null;
    activeTabStart = now;

    // Emit tab_switch event
    if (activeTabUrl) {
      await emitTabSwitch(activeTabUrl);
    }
  } catch {
    // tab may have been closed already
  }
});

// Update URL when tab navigates while active
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (tabId !== activeTabId) return;
  if (changeInfo.status !== 'complete') return;
  if (tab.incognito) return;
  activeTabUrl = tab.url || activeTabUrl;
});

// Idle state: stop timing when user locks / leaves
chrome.idle.onStateChanged.addListener(async (newState) => {
  if (newState === 'idle' || newState === 'locked') {
    if (activeTabUrl && activeTabStart !== null) {
      const stayS = Math.floor((Date.now() - activeTabStart) / 1000);
      await maybeEmitTabStay(activeTabUrl, stayS);
      activeTabStart = null; // pause timing
    }
  } else if (newState === 'active') {
    activeTabStart = Date.now(); // resume
  }
});

// ---------------------------------------------------------------------------
// Emit helpers
// ---------------------------------------------------------------------------

async function maybeEmitTabStay(url, stayS) {
  if (!shouldRecordStay(stayS)) return; // < 5s = noise
  const { domain, url_path } = getCleanPathAndDomain(url);
  if (!domain || domain === 'unknown') return;

  const bucket = classifyDomain(domain, cachedRules);
  const event = {
    module: 'M1.3.2',
    action: 'tab_stay',
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    level: 'INFO',
    role_id: 'default',
    payload: {
      domain,
      url_path,
      domain_bucket: bucket,
      stay_s: stayS,
      // title: NOT included (CaptureMode::Off default) [RISK-15]
    },
  };
  sendToHost(event);
}

async function emitTabSwitch(toUrl) {
  const { domain } = getCleanPathAndDomain(toUrl);
  if (!domain || domain === 'unknown') return;

  const event = {
    module: 'M1.3.2',
    action: 'tab_switch',
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    level: 'INFO',
    role_id: 'default',
    payload: {
      to_domain: domain,
      to_bucket: classifyDomain(domain, cachedRules),
    },
  };
  sendToHost(event);
}

function sendToHost(event) {
  chrome.runtime.sendNativeMessage('coos_native_host', { command: 'telemetry', event });
}
