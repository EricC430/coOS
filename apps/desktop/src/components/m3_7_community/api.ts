/**
 * M3.7 — Community API Client & SSE Hook
 *
 * SPEC: docs/modules/M3_7_community_ui_SPEC.md §3.1–§3.2
 * Fetch wrappers for all 15 community endpoints.
 * useCommunityStream: SSE hook with 30s polling fallback on disconnect.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";

const BASE = "/api/m6_6";

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const roleId = useCoOSStore.getState().currentRole?.id || "";
  const headers = new Headers(opts?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (roleId) {
    headers.set("X-Role-ID", roleId);
  }
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Community endpoints
// ---------------------------------------------------------------------------

export interface CommunityRead {
  id: string;
  name: string;
  type: string;
  theme?: string;
  member_cap: number;
  member_count: number;
  is_member: boolean;
  role: string;
  goal?: string;
  vision?: string;
  codex?: string;
  rules: string[];
  quotes: string[];
}

export interface CommunityCodex {
  goal: string;
  vision: string;
  codex: string;
  quotes: string[];
  rules: string[];
}

export interface SocialPost {
  id: string;
  author_id: string;
  author_display?: string;
  content: string;
  kind: string;
  likes_count: number;
  created_at?: string;
  published_at?: string;
  validation_count: number;
}

export interface ChallengeItem {
  id: string;
  title: string;
  description?: string;
  period: string;
  source: string;
  progress: number;
  is_draft?: boolean;
  created_at: string;
}

export interface CommitmentItem {
  id: string;
  content: string;
  kind: string;
  validation_count: number;
  published_at?: string;
}

export interface TaskToValidate {
  id: string;
  content: string;
  kind: string;
  author_id: string;
  published_at?: string;
}

export interface ActiveStake {
  id: string;
  xp_amount: number;
  deadline?: string;
}

export interface CommitmentsView {
  commitments: CommitmentItem[];
  to_validate: TaskToValidate[];
  active_stakes: ActiveStake[];
}

export interface StakeRead {
  id: string;
  community_id: string;
  task_id?: string;
  xp_amount: number;
  status: string;
  deadline?: string;
  created_at: string;
}

// --- API functions ---

export const fetchCommunities = () =>
  apiFetch<CommunityRead[]>("/communities");

export const createCommunity = (data: {
  name: string;
  type?: string;
  theme?: string;
  member_cap?: number;
}) => apiFetch<CommunityRead>("/communities", {
  method: "POST",
  body: JSON.stringify(data),
});

export const joinCommunity = (data: { mode: string; theme?: string }) =>
  apiFetch<{ id: string; name: string; joined: boolean }>("/communities/join", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const fetchCodex = (communityId: string) =>
  apiFetch<CommunityCodex>(`/communities/${communityId}/codex`);

export const fetchPosts = (communityId: string) =>
  apiFetch<SocialPost[]>(`/communities/${communityId}/posts`);

export const fetchChallenges = (communityId: string) =>
  apiFetch<ChallengeItem[]>(`/communities/${communityId}/challenges`);

export const fetchCommitments = (communityId: string) =>
  apiFetch<CommitmentsView>(`/communities/${communityId}/commitments`);

export const createPostDraft = (data: {
  community_id: string;
  content: string;
  kind?: string;
}) => apiFetch<{ id: string; is_draft: boolean; privacy_warning: string }>(
  "/posts/draft",
  { method: "POST", body: JSON.stringify(data) },
);

export const publishPost = (draftId: string) =>
  apiFetch<{ id: string; published: boolean; published_at?: string }>(
    "/posts/publish",
    { method: "POST", body: JSON.stringify({ draft_id: draftId }) },
  );

export const likePost = (postId: string) =>
  apiFetch<{ id: string; likes_count: number }>(
    `/posts/${postId}/like`,
    { method: "POST" },
  );

export const fetchStakes = () => apiFetch<StakeRead[]>("/stakes");

export const createStake = (data: {
  community_id: string;
  xp_amount: number;
  task_id?: string;
  deadline?: string;
}) => apiFetch<StakeRead>("/stakes", {
  method: "POST",
  body: JSON.stringify(data),
});

export const createValidation = (data: {
  post_id: string;
  evidence_url?: string;
}) => apiFetch<{ id: string; post_id: string; validated_at: string }>(
  "/validations",
  { method: "POST", body: JSON.stringify(data) },
);

export const approveChallenge = (
  challengeId: string,
  edits?: Record<string, string>,
) => apiFetch<{ id: string; approved: boolean }>(
  `/challenges/${challengeId}/approve`,
  { method: "POST", body: JSON.stringify({ edits }) },
);

export const updateCodex = (
  communityId: string,
  data: CommunityCodex,
) => apiFetch<CommunityCodex>(
  `/communities/${communityId}/codex`,
  { method: "POST", body: JSON.stringify(data) },
);

export const createChallenge = (
  communityId: string,
  data: {
    title: string;
    description?: string;
    period: string;
    source: string;
  },
) => apiFetch<ChallengeItem>(
  `/communities/${communityId}/challenges`,
  { method: "POST", body: JSON.stringify(data) },
);

export const generateAIChallenge = (
  communityId: string,
) => apiFetch<ChallengeItem>(
  `/communities/${communityId}/challenges/generate-ai`,
  { method: "POST" },
);

// ---------------------------------------------------------------------------
// SSE Hook with 30s polling fallback
// ---------------------------------------------------------------------------

export interface CommunityEvent {
  type: string;
  community_id?: string;
  post_id?: string;
  challenge_id?: string;
  actor_id?: string;
  message?: string;
}

export function useCommunityStream(communityId: string | null) {
  const [events, setEvents] = useState<CommunityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleEvent = useCallback((event: CommunityEvent) => {
    setEvents((prev) => [event, ...prev].slice(0, 50));
  }, []);

  useEffect(() => {
    if (!communityId || communityId === "__add__") return;

    let es: EventSource | null = null;
    let closed = false;

    const startSSE = () => {
      const roleId = useCoOSStore.getState().currentRole?.id || "";
      es = new EventSource(`${BASE}/stream?community_id=${communityId}&role_id=${roleId}`);

      es.onopen = () => {
        setConnected(true);
        // Clear polling fallback if SSE connects
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      };

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          handleEvent(data);
        } catch {
          // Ignore non-JSON messages
        }
      };

      es.onerror = () => {
        setConnected(false);
        es?.close();
        if (!closed) {
          // Fallback to 30s polling
          if (!pollingRef.current) {
            pollingRef.current = setInterval(async () => {
              try {
                const posts = await fetchPosts(communityId);
                // Emit a synthetic refresh event
                handleEvent({
                  type: "POLL_REFRESH",
                  community_id: communityId,
                  message: `Refreshed ${posts.length} posts`,
                });
              } catch {
                // Ignore polling errors
              }
            }, 30_000);
          }
          // Attempt reconnect after 5s
          setTimeout(() => {
            if (!closed) startSSE();
          }, 5000);
        }
      };
    };

    startSSE();

    return () => {
      closed = true;
      es?.close();
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [communityId, handleEvent]);

  return { events, connected };
}


// ---------------------------------------------------------------------------
// Community Administration APIs
// ---------------------------------------------------------------------------

export interface MemberRead {
  user_id: string;
  role: string;
  joined_at: string;
  display_name: string;
}

export interface JoinRequestRead {
  id: string;
  community_id: string;
  user_id: string;
  status: string;
  created_at: string;
  display_name: string;
}

export const fetchMembers = (communityId: string) =>
  apiFetch<MemberRead[]>(`/communities/${communityId}/members`);

export const updateMemberRole = (communityId: string, userId: string, role: string) =>
  apiFetch<{ user_id: string; role: string }>(
    `/communities/${communityId}/members/${userId}/role`,
    { method: "POST", body: JSON.stringify({ role }) }
  );

export const kickMember = (communityId: string, userId: string) =>
  apiFetch<{ user_id: string; kicked: boolean }>(
    `/communities/${communityId}/members/${userId}`,
    { method: "DELETE" }
  );

export const leaveCommunity = (communityId: string) =>
  apiFetch<{ community_id: string; left: boolean }>(
    `/communities/${communityId}/leave`,
    { method: "POST" }
  );

export const fetchJoinRequests = (communityId: string) =>
  apiFetch<JoinRequestRead[]>(`/communities/${communityId}/join-requests`);

export const applyJoinCommunity = (communityId: string) =>
  apiFetch<{ id: string; community_id: string; status: string }>(
    `/communities/${communityId}/join-requests`,
    { method: "POST" }
  );

export const handleJoinRequest = (communityId: string, requestId: string, action: string) =>
  apiFetch<{ request_id: string; status: string }>(
    `/communities/${communityId}/join-requests/${requestId}/action`,
    { method: "POST", body: JSON.stringify({ action }) }
  );

export const updateCommunitySettings = (
  communityId: string,
  settings: { challenge_mode: string; member_cap: number }
) =>
  apiFetch<{ id: string; challenge_mode: string; member_cap: number }>(
    `/communities/${communityId}/settings`,
    { method: "POST", body: JSON.stringify(settings) }
  );

export const fetchExploreCommunities = () =>
  apiFetch<CommunityRead[]>("/communities/explore");

