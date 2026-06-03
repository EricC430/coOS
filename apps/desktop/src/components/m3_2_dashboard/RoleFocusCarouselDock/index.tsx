/**
 * M3.2.1 -- Role Focus Carousel Dock
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS7.1
 * [R08 SS1] Inertia Snap: ritualises role switch as intentional act
 * [R09 SS4 SDT] Centre icon larger by >= 1.3x reinforces autonomy signal
 * @risk RISK-04 Do NOT emit ROLE_SWITCHED during animation -- only on snap complete
 */

import React, { useEffect, useRef, useState } from "react";
import { useCarouselPhysics } from "./useCarouselPhysics";

export interface CarouselRole {
  id: string;
  name: string;
  iconName?: string;
  colorHex?: string;
}

interface Props {
  roles: CarouselRole[];
  activeRoleId: string;
  onRoleSnap: (roleId: string) => void;
}

const ITEM_WIDTH = 72;

export function RoleFocusCarouselDock({ roles, activeRoleId, onRoleSnap }: Props) {
  const [snapIndex, setSnapIndex] = useState(
    Math.max(roles.findIndex((r) => r.id === activeRoleId), 0)
  );
  const prevXRef = useRef(0);

  const handleSnap = (index: number) => {
    setSnapIndex(index);
    // [RISK-04] Emit only on snap complete, not mid-drag
    onRoleSnap(roles[index].id);
  };

  const { init, onPointerDown, onPointerMove, onPointerUp } =
    useCarouselPhysics(ITEM_WIDTH, handleSnap);

  useEffect(() => {
    init(roles.length, snapIndex);
  }, [roles.length, snapIndex, init]);

  // Keep carousel centred on activeRoleId when external switch
  useEffect(() => {
    const idx = roles.findIndex((r) => r.id === activeRoleId);
    if (idx >= 0 && idx !== snapIndex) setSnapIndex(idx);
  }, [activeRoleId]);

  return (
    <div
      data-testid="role-carousel"
      className="flex items-end justify-center gap-2 px-4 pb-2 select-none overflow-hidden"
      style={{ touchAction: "none" }}
      onPointerDown={(e) => {
        prevXRef.current = e.clientX;
        onPointerDown(e.clientX);
      }}
      onPointerMove={(e) => {
        onPointerMove(e.clientX, prevXRef.current);
        prevXRef.current = e.clientX;
      }}
      onPointerUp={(e) => onPointerUp(e.clientX)}
    >
      {roles.map((role, idx) => {
        const distance = Math.abs(idx - snapIndex);
        // [R09 SS4] Centre icon scale >= 1.3x non-centre
        const scale = distance === 0 ? 1.4 : distance === 1 ? 1.0 : 0.75;
        const isCenter = distance === 0;

        return (
          <div
            key={role.id}
            data-testid={isCenter ? "active-role-icon" : "side-role-icon"}
            data-role-id={role.id}
            className="flex flex-col items-center cursor-pointer transition-transform duration-200"
            style={{
              transform: `scale(${scale})`,
              opacity: distance > 2 ? 0 : 1,
              zIndex: isCenter ? 10 : 1,
            }}
          >
            <div
              className="rounded-full flex items-center justify-center font-bold text-white"
              style={{
                width: ITEM_WIDTH,
                height: ITEM_WIDTH,
                background: role.colorHex ?? "#6366f1",
                boxShadow: isCenter ? `0 0 12px ${role.colorHex ?? "#6366f1"}88` : undefined,
              }}
            >
              {role.iconName ?? role.name.slice(0, 2).toUpperCase()}
            </div>
            <span className="text-xs mt-1 text-center truncate w-16">
              {role.name}
            </span>
          </div>
        );
      })}
    </div>
  );
}
