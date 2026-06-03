/**
 * M3.2.3.2 -- Role context pre-fetching cache
 * [R08 SS5] Pre-fetch adjacent roles to minimise perceived wait time
 */

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export async function fetchRoleContext(roleId: string) {
  const res = await fetch(`/api/m6_3/role_context?role_id=${roleId}`);
  if (!res.ok) throw new Error("role_context_fetch_failed");
  return res.json();
}

export function useRoleContextCache(adjacentRoleIds: string[]) {
  const queryClient = useQueryClient();

  useEffect(() => {
    for (const id of adjacentRoleIds) {
      queryClient.prefetchQuery({
        queryKey: ["role_context", id],
        queryFn: () => fetchRoleContext(id),
        staleTime: 60_000,
      });
    }
  }, [adjacentRoleIds.join(",")]);
}
