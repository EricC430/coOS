/**
 * M3.1 -- Global State tests
 *
 * SPEC: docs/modules/M3_1_global_state_layout_SPEC.md SS6
 * [R08 SS1] Centralised state prevents cognitive inconsistency
 * [R09 SS4 SDT] Role switch must feel instantaneous (< 100ms)
 * @integration_risk RISK-06
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { useCoOSStore } from "../../src/stores/m3_1_global_store";

const mockRoles = [
  { id: "csie_001", name: "CSIE", themeColorPalette: { primary: "#4A90D9" }, sortOrder: 0 },
  { id: "family_002", name: "FAMILY", themeColorPalette: { primary: "#E07B39" }, sortOrder: 1 },
];

const mockExperts = [
  { id: "robert_001", expertName: "Robert", trustLevel: 3, title: "動力導師" },
  { id: "beth_002", expertName: "Beth", trustLevel: 2, title: "情感諮商師" },
];

beforeEach(() => {
  useCoOSStore.setState({
    currentRole: null,
    xpBalance: 0,
    level: 1,
    activeExpert: null,
    roleCache: {},
    expertCache: {},
    isRoleTransitioning: false,
  });
});

describe("M3.1.1 Global variable management", () => {
  it("seedRoleCache initialises currentRole to sortOrder=0 role", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    expect(useCoOSStore.getState().currentRole?.id).toBe("csie_001");
  });

  it("switchRole updates currentRole within synchronous tick (< 100ms proxy)", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    const before = Date.now();
    useCoOSStore.getState().switchRole("family_002");
    const elapsed = Date.now() - before;
    expect(useCoOSStore.getState().currentRole?.id).toBe("family_002");
    expect(elapsed).toBeLessThan(100);
  });

  it("applyXPGrant sets xpBalance to new_total", () => {
    useCoOSStore.getState().applyXPGrant({ amount: 50, new_total: 1200 });
    expect(useCoOSStore.getState().xpBalance).toBe(1200);
  });

  it("setActiveExpert does not mutate currentRole", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    useCoOSStore.getState().seedExpertCache(mockExperts);
    useCoOSStore.getState().switchRole("csie_001");
    const prevRole = useCoOSStore.getState().currentRole;
    useCoOSStore.getState().setActiveExpert("beth_002");
    expect(useCoOSStore.getState().currentRole).toEqual(prevRole);
  });

  it("[RISK-06] switchRole sets isRoleTransitioning=true", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    useCoOSStore.getState().switchRole("family_002");
    expect(useCoOSStore.getState().isRoleTransitioning).toBe(true);
  });

  it("level computed correctly from xp (floor(sqrt(xp/100)))", () => {
    useCoOSStore.getState().applyXPGrant({ amount: 400, new_total: 400 });
    // sqrt(400/100) = sqrt(4) = 2
    expect(useCoOSStore.getState().level).toBe(2);
  });

  it("negative xp forces level=1", () => {
    useCoOSStore.getState().applyXPGrant({ amount: -50, new_total: -50 });
    expect(useCoOSStore.getState().level).toBe(1);
  });
});

describe("M3.1.2 Pub/Sub event dispatch", () => {
  it("switchRole triggers subscriber with new role", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    useCoOSStore.getState().switchRole("csie_001");

    const listener = vi.fn();
    const unsub = useCoOSStore.subscribe(
      (state) => state.currentRole,
      listener
    );
    useCoOSStore.getState().switchRole("family_002");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0][0]?.id).toBe("family_002");
    unsub();
  });

  it("[RISK-06] switching to same role_id does NOT re-trigger subscriber", () => {
    useCoOSStore.getState().seedRoleCache(mockRoles);
    useCoOSStore.getState().switchRole("csie_001");

    const listener = vi.fn();
    const unsub = useCoOSStore.subscribe(
      (state) => state.currentRole,
      listener
    );
    useCoOSStore.getState().switchRole("csie_001"); // same
    expect(listener).not.toHaveBeenCalled();
    unsub();
  });
});
