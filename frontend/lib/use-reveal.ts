/**
 * Scroll-triggered reveal behaviour.
 *
 * The hook watches an element and, the first time it scrolls into view, marks it with
 * `data-revealed="true"`. The stylesheet turns that attribute into a fade-and-rise
 * transition (see "Scroll reveal" in styles/globals.css). Keeping the visual rules in CSS
 * and only the trigger in JavaScript means animations stay cheap (opacity and transform
 * only) and can be switched off entirely for visitors who prefer reduced motion.
 *
 * The attribute is written straight to the element instead of through React state, so
 * revealing never causes a re-render.
 */

import { useEffect, useRef } from "react";
import type { RefObject } from "react";

export function useRevealOnScroll<T extends HTMLElement>(): RefObject<T | null> {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reveal = () => {
      node.dataset.revealed = "true";
    };

    // Reveal at once when motion is unwanted or the browser cannot observe visibility.
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || typeof IntersectionObserver === "undefined") {
      reveal();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            reveal();
            observer.disconnect();
          }
        }
      },
      // Trigger slightly before the element is fully in view, so it feels natural.
      { threshold: 0.15, rootMargin: "0px 0px -8% 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return ref;
}
