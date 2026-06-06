/**
 * M1.3.2 Browser Extension — Service Worker (background script)
 *
 * SPEC: docs/modules/M1_3_2_browser_extension_SPEC.md
 */

'use strict';

import { classifyDomain, getCleanPathAndDomain, shouldRecordStay } from './classify.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let cachedRules = {};       // { "github.com": "coding", ... } — loaded from host
let activeTabId = null;
let activeTabUrl = null;
let activeTabTitle = null;
let activeTabStart = null;  // timestamp ms when tab became active
let captureTimeout = null;  // debounce timer for onUpdated events

let captureConsent = { mode: 'off', allowed_processes: [] };
let lastConsentFetch = 0;

// Deduplication state to prevent redundant back-to-back content capture
let lastCapturedUrl = null;
let lastCapturedTitle = null;
let lastCapturedTime = 0;

// ---------------------------------------------------------------------------
// Rules & Consent loading
// ---------------------------------------------------------------------------
async function initializeActiveTabState() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (tab) {
      activeTabId = tab.id;
      activeTabUrl = tab.url;
      activeTabTitle = tab.title || '';
      activeTabStart = Date.now();
    }
  } catch (e) {
    console.warn('Failed to initialize active tab state:', e);
  }
}

function loadRulesFromHost() {
  chrome.runtime.sendNativeMessage('coos_native_host', { command: 'get_rules' }, (response) => {
    if (chrome.runtime.lastError) {
      return;
    }
    if (response && response.rules) {
      cachedRules = response.rules;
    }
  });
  initializeActiveTabState();
}

chrome.runtime.onInstalled.addListener(loadRulesFromHost);
chrome.runtime.onStartup.addListener(loadRulesFromHost);

// Initialize active tab state immediately on script load
initializeActiveTabState();

async function refreshConsent() {
  const now = Date.now();
  if (now - lastConsentFetch < 30000) {
    return captureConsent;
  }
  try {
    const res = await fetch('http://127.0.0.1:8000/api/m1_1/consent');
    if (res.ok) {
      captureConsent = await res.json();
      lastConsentFetch = now;
    } else {
      captureConsent = { mode: 'off', allowed_processes: [] };
    }
  } catch (e) {
    console.warn('Failed to fetch consent from sidecar, turning capture off:', e);
    captureConsent = { mode: 'off', allowed_processes: [] };
  }
  return captureConsent;
}

// Dynamic rule updates
chrome.runtime.onMessage.addListener((message) => {
  if (message.command === 'update_rules' && message.rules) {
    cachedRules = message.rules;
  }
});

// ---------------------------------------------------------------------------
// DOM Text Extraction & Helpers
// ---------------------------------------------------------------------------
function getBrowserProcessName() {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('edg/')) return 'msedge.exe';
  if (ua.includes('firefox/')) return 'firefox.exe';
  if (ua.includes('chrome/')) return 'chrome.exe';
  return 'chrome.exe';
}

function isConsentEnabled(consent) {
  if (consent.mode === 'all' || consent.mode === 'all_apps') return true;
  if (consent.mode === 'selected' || consent.mode === 'selected_apps') {
    const allowed = consent.allowed_processes || [];
    const currentBrowser = getBrowserProcessName().replace('.exe', '');
    return allowed.some(p => {
      const pClean = p.toLowerCase().replace('.exe', '');
      return pClean === currentBrowser || pClean === 'browser';
    });
  }
  return false;
}

async function extractPageText(tabId) {
  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        const hostname = window.location.hostname;

        // 1. YouTube Specific Extraction: extract only watch metadata and description, ignore recommendations
        if (hostname.includes('youtube.com')) {
          const videoTitleEl = document.querySelector('h1.ytd-watch-metadata, #container h1.title');
          const descriptionEl = document.querySelector('#description-inner, yt-formatted-string#description');
          const titleText = videoTitleEl ? videoTitleEl.innerText.trim() : '';
          const descText = descriptionEl ? descriptionEl.innerText.trim().substring(0, 1000) : '';
          return `[VIDEO TITLE] ${titleText}\n[DESCRIPTION] ${descText}`;
        }

        // Helper to query text list from a given element tree
        const queryTextFromTree = (root) => {
          const tags = [
            'h1', 'h2', 'h3', 'p', 'article', 'section',
            'li', 'td', 'dd', 'dt',
            '[class*="title"]', '[class*="content"]'
          ];
          const elements = Array.from(root.querySelectorAll(tags.join(',')));
          
          // Filter out elements that contain other matched elements to avoid nested duplication
          const leafElements = elements.filter(el => {
            return !elements.some(otherEl => el !== otherEl && el.contains(otherEl));
          });

          return leafElements
            .map(el => el.innerText.trim())
            .filter(t => t.length > 15)
            .join('\n');
        };

        // 2. Generic Site Clean: Clone DOM and remove typical noise elements (sidebars, comments, ads)
        const bodyClone = document.body.cloneNode(true);
        const noiseSelectors = [
          'nav', 'header', 'footer', 'aside',
          '#sidebar', '.sidebar', '#navigation', '.navigation',
          '#related', '#comments', '#comment', '.comments',
          '.recommendations', '.related-posts', '.menu',
          '#footer', '.footer', '#header', '.header',
          '#comments-section', '.nav-links', '.ad-container', '.ads'
        ];
        noiseSelectors.forEach(sel => {
          bodyClone.querySelectorAll(sel).forEach(el => el.remove());
        });

        let extractedText = queryTextFromTree(bodyClone);

        // 3. Fallback: If the cleaned content is too thin (< 250 chars), fall back to extracting from the original body
        if (extractedText.trim().length < 250) {
          extractedText = queryTextFromTree(document.body);
        }

        return extractedText.substring(0, 4000);
      }
    });
    return result ? result.result : '';
  } catch (err) {
    // Gracefully return empty if scripting is blocked (e.g. chrome:// tabs)
    return '';
  }
}

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

  // Always register the active tab ID even if it is not yet an HTTP page
  activeTabId = activeInfo.tabId;
  activeTabUrl = null;
  activeTabTitle = null;
  activeTabStart = null;

  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.incognito || !tab.url || !tab.url.startsWith('http')) {
      return;
    }
    activeTabUrl = tab.url;
    activeTabTitle = tab.title || '';
    activeTabStart = now;

    // Emit tab_switch event
    await emitTabSwitch(activeTabUrl);

    // Emit content_capture event for the new active tab
    await triggerContentCapture(activeTabId, activeTabUrl, activeTabTitle);
  } catch (e) {
    console.error('onActivated handler error:', e);
  }
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (tabId !== activeTabId) return;
  if (tab.incognito || !tab.url || !tab.url.startsWith('http')) return;

  activeTabUrl = tab.url;
  activeTabTitle = tab.title || '';
  activeTabStart = Date.now();

  // Clear previous scheduled task and debounce for 800ms
  if (captureTimeout) {
    clearTimeout(captureTimeout);
  }

  captureTimeout = setTimeout(async () => {
    try {
      const updatedTab = await chrome.tabs.get(tabId);
      // Ensure the tab is still active and URL hasn't changed before executing capture
      if (updatedTab.active && updatedTab.url === activeTabUrl) {
        await triggerContentCapture(tabId, updatedTab.url, updatedTab.title || '');
      }
    } catch (e) {}
  }, 800);
});

// Track browser window focus changes to update activeTabId and capture content
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    // Browser lost focus entirely
    if (activeTabUrl && activeTabStart !== null) {
      const stayS = Math.floor((Date.now() - activeTabStart) / 1000);
      await maybeEmitTabStay(activeTabUrl, stayS);
      activeTabStart = null;
    }
    return;
  }

  try {
    const [tab] = await chrome.tabs.query({ active: true, windowId: windowId });
    if (tab) {
      const now = Date.now();
      if (activeTabUrl && activeTabStart !== null) {
        const stayS = Math.floor((now - activeTabStart) / 1000);
        await maybeEmitTabStay(activeTabUrl, stayS);
      }

      activeTabId = tab.id;
      activeTabUrl = tab.url;
      activeTabTitle = tab.title || '';
      activeTabStart = now;

      if (tab.incognito || !tab.url || !tab.url.startsWith('http')) {
        return;
      }

      await emitTabSwitch(activeTabUrl);
      await triggerContentCapture(activeTabId, activeTabUrl, activeTabTitle);
    }
  } catch (e) {
    console.error('onFocusChanged handler error:', e);
  }
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
async function triggerContentCapture(tabId, url, title) {
  const consent = await refreshConsent();
  if (!isConsentEnabled(consent)) {
    return;
  }

  const now = Date.now();
  if (url === lastCapturedUrl && title === lastCapturedTitle && (now - lastCapturedTime < 60000)) {
    // Skip duplicate capture on the same page within 60 seconds
    return;
  }

  const pageText = await extractPageText(tabId);
  const cleanUrl = getCleanPathAndDomain(url);
  const appName = getBrowserProcessName();

  const formattedRaw = `[TITLE] ${title}\n[URL] ${url}\n[FOCUS] ${pageText || '(No readable page text)'}`;

  const event = {
    module: 'M1.3.2',
    action: 'content_capture',
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    level: 'INFO',
    role_id: 'default',
    payload: {
      app_name: appName,
      content_raw: formattedRaw,
      content_summary: `${title} — ${cleanUrl.domain}${cleanUrl.url_path}`,
      inference_mode: 'rule_based_fallback',
      privacy_tier: 'T1_OPTIN'
    }
  };

  sendToHost(event);

  lastCapturedUrl = url;
  lastCapturedTitle = title;
  lastCapturedTime = now;
}

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
  // Try native messaging first
  chrome.runtime.sendNativeMessage('coos_native_host', { command: 'telemetry', event }, (response) => {
    if (chrome.runtime.lastError) {
      // Fallback: send directly to FastAPI sidecar via HTTP fetch
      postToHttpEndpoint(event);
    }
  });
}

function postToHttpEndpoint(event) {
  fetch('http://127.0.0.1:8000/api/m1_1/event', {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(event)
  }).catch((err) => {
    console.warn('HTTP fallback connection failed:', err);
  });
}
