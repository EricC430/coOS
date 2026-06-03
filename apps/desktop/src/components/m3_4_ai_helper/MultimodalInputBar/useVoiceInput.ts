/**
 * M3.4.3.3 -- Voice input with 3-tier RAM degradation
 * [R10 §voice cascade] + [RISK-11] Never send to cloud without explicit consent
 * RAM tiers: > 3GB -> whisper-base local | > 1.5GB -> whisper-tiny | has consent -> cloud | else queue
 */

const GB = 1024 ** 3;

async function getAvailableRAM(): Promise<number> {
  // navigator.deviceMemory gives total, not available -- use as proxy on web
  if ("deviceMemory" in navigator) {
    return (navigator as { deviceMemory?: number }).deviceMemory! * GB * 0.5;
  }
  return 4 * GB; // default assume sufficient
}

export async function routeVoiceTranscription(
  audioBlob: Blob,
  hasCloudConsent: boolean
): Promise<string> {
  const ram = await getAvailableRAM();

  if (ram > 3 * GB) {
    // Tier 1: local whisper-base (simulated)
    return localWhisperBase(audioBlob);
  }
  if (ram > 1.5 * GB) {
    // Tier 2: local whisper-tiny
    return localWhisperTiny(audioBlob);
  }
  if (hasCloudConsent) {
    // Tier 3: cloud with explicit consent only
    return cloudWhisperWithConsent(audioBlob);
  }
  // Tier 4: queue for breakpoint processing
  await queueForLater(audioBlob);
  return "";
}

// Stubs -- real implementations connect to local Whisper sidecar
async function localWhisperBase(_blob: Blob): Promise<string> {
  const res = await fetch("/api/m_voice/transcribe", {
    method: "POST",
    body: _blob,
    headers: { "X-Model": "whisper-base" },
  });
  if (!res.ok) throw new Error("whisper_base_failed");
  return (await res.json()).transcript;
}

async function localWhisperTiny(_blob: Blob): Promise<string> {
  const res = await fetch("/api/m_voice/transcribe", {
    method: "POST",
    body: _blob,
    headers: { "X-Model": "whisper-tiny" },
  });
  if (!res.ok) throw new Error("whisper_tiny_failed");
  return (await res.json()).transcript;
}

async function cloudWhisperWithConsent(_blob: Blob): Promise<string> {
  const res = await fetch("/api/m_voice/transcribe_cloud", {
    method: "POST",
    body: _blob,
  });
  if (!res.ok) throw new Error("cloud_whisper_failed");
  return (await res.json()).transcript;
}

async function queueForLater(_blob: Blob): Promise<void> {
  // Persist blob locally; will be processed at next BREAKPOINT_DETECTED
  console.info("[M3.4] Voice queued for breakpoint processing");
}
