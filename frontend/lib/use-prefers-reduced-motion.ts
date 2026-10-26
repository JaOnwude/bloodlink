/**
 * Whether the visitor has asked their system for reduced motion.
 *
 * Anything that moves on its own (a slideshow, a slow zoom, a floating card) checks this and
 * stays still when it is true. It follows the setting live, so turning it on while the page
 * is open stops the motion at once. On the server, where there is no preference to read, it
 * reports false.
 */

import { useSyncExternalStore } from "react";

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void) {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}
