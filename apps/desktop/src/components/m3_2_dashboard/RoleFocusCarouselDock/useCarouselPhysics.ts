/**
 * M3.2.1.1 -- Carousel inertia physics hook
 * [R08 SS1] Inertia slide reinforces muscle-memory of intentional role choice,
 *           strengthening SDT autonomy (R09 SS4).
 */

import { useRef, useCallback } from "react";

export function useCarouselPhysics(
  itemWidth: number,
  onSnap: (index: number) => void
) {
  const velocity = useRef(0);
  const startX = useRef(0);
  const currentIndex = useRef(0);
  const totalItems = useRef(0);

  const init = useCallback((count: number, activeIndex: number) => {
    totalItems.current = count;
    currentIndex.current = activeIndex;
  }, []);

  const onPointerDown = useCallback((clientX: number) => {
    startX.current = clientX;
    velocity.current = 0;
  }, []);

  const onPointerMove = useCallback(
    (clientX: number, prevX: number) => {
      velocity.current = clientX - prevX;
    },
    []
  );

  const onPointerUp = useCallback(
    (clientX: number) => {
      const delta = clientX - startX.current;
      // Snap direction based on drag distance + velocity
      let newIndex = currentIndex.current;
      if (Math.abs(delta) > itemWidth * 0.3 || Math.abs(velocity.current) > 5) {
        newIndex =
          delta < 0
            ? Math.min(currentIndex.current + 1, totalItems.current - 1)
            : Math.max(currentIndex.current - 1, 0);
      }
      currentIndex.current = newIndex;
      onSnap(newIndex);
    },
    [itemWidth, onSnap]
  );

  return { init, onPointerDown, onPointerMove, onPointerUp };
}
