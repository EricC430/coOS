/**
 * M3.7 -- Community UI (MVP Stub)
 *
 * SPEC: docs/modules/M3_7_community_ui_SPEC.md
 * Tag: [進階] -- Full implementation deferred to Phase 6b
 *
 * MVP: stub card only. NO hard dependencies on M4.13 or M6.6.
 * This stub must NOT be removed even in Phase 6b -- use stubMode=false to activate.
 *
 * Anti-pattern: NEVER implement full M3.7 features in MVP.
 *               Hard-coding M4.13/M6.6 deps here breaks MVP isolation.
 */

import React from "react";
import { FullCommunityUI } from "./FullCommunityUI";

interface Props {
  stubMode?: boolean;
}

export function CommunityUI({ stubMode = true }: Props) {
  if (stubMode) {
    return (
      <div
        data-testid="community-stub"
        className="flex flex-col items-center justify-center h-full text-gray-400 gap-3"
      >
        <div className="text-4xl">🌐</div>
        <p className="text-sm">社群功能將在進階階段開放</p>
        <p className="text-xs text-gray-300">完成 MVP 閉環後解鎖</p>
      </div>
    );
  }

  return <FullCommunityUI />;
}
