/**
 * A slideshow of photographs with a short caption each, for the landing page.
 *
 * It follows the WAI-ARIA carousel pattern, so it works for everyone, not just mouse users:
 *
 * - previous and next buttons, one dot per slide, and the left and right arrow keys;
 * - screen readers hear "Slide 2 of 5" and the caption of the slide in view, and only the
 *   visible slide is exposed to them;
 * - it advances on its own every few seconds, but stops while the pointer is over it or
 *   keyboard focus is inside it, has a pause button, and never moves by itself for visitors
 *   who have asked their system for reduced motion.
 *
 * Photos load lazily and fill a fixed-ratio frame, so the page does not jump while they
 * arrive. A crimson gradient sits behind each photo, so a failed image still looks intended.
 */

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import type { KeyboardEvent } from "react";

import type { CarouselSlide } from "@/lib/images";
import { cn } from "@/lib/utils";

/** How long each slide stays in view while playing, in milliseconds. */
const SLIDE_INTERVAL_MS = 7000;

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeToMotionPreference(onChange: () => void) {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/** Whether the visitor asked for reduced motion. False while rendering on the server. */
function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToMotionPreference,
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}

export function PhotoCarousel({ slides, label }: { slides: CarouselSlide[]; label: string }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  // Hover and focus pause it only for as long as they last; the button pauses it for good.
  const [interacting, setInteracting] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  const count = slides.length;
  const goTo = useCallback((next: number) => setIndex((next + count) % count), [count]);
  const playing = !paused && !interacting && !reducedMotion && count > 1;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => setIndex((current) => (current + 1) % count), SLIDE_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [playing, index, count]);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      goTo(index - 1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      goTo(index + 1);
    }
  }

  if (count === 0) return null;

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label={label}
      className="space-y-4"
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setInteracting(true)}
      onMouseLeave={() => setInteracting(false)}
      onFocus={() => setInteracting(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setInteracting(false);
      }}
    >
      <div className="relative aspect-[4/5] overflow-hidden rounded-3xl bg-linear-to-br from-primary-700 via-primary-900 to-night shadow-lift sm:aspect-[16/9]">
        {/* Announces each new caption to screen readers, but only while it is not playing
            by itself, so a running slideshow does not keep interrupting them. */}
        <div aria-live={playing ? "off" : "polite"}>
          {slides.map((slide, position) => {
            const current = position === index;
            return (
              <div
                key={slide.image.src}
                role="group"
                aria-roledescription="slide"
                aria-label={`${position + 1} of ${count}`}
                aria-hidden={!current}
                className={cn(
                  "absolute inset-0 transition-opacity duration-700 ease-brand motion-reduce:transition-none",
                  current ? "opacity-100" : "pointer-events-none opacity-0",
                )}
              >
                <Image
                  src={slide.image.src}
                  alt={slide.image.alt}
                  fill
                  sizes="(min-width: 1200px) 1100px, 100vw"
                  className="object-cover"
                  style={{ objectPosition: slide.image.objectPosition }}
                />
                <div className="absolute inset-0 bg-linear-to-t from-night/90 via-night/30 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 space-y-2 p-6 sm:p-10">
                  <p className="font-heading text-2xl font-semibold text-ivory sm:text-3xl">
                    {slide.title}
                  </p>
                  <p className="max-w-xl text-ivory/85">{slide.body}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => goTo(index - 1)}
            aria-label="Previous slide"
            className="flex size-10 items-center justify-center rounded-full border border-input bg-surface text-ink transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <ChevronLeft className="size-5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => goTo(index + 1)}
            aria-label="Next slide"
            className="flex size-10 items-center justify-center rounded-full border border-input bg-surface text-ink transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <ChevronRight className="size-5" aria-hidden="true" />
          </button>
          {reducedMotion ? null : (
            <button
              type="button"
              onClick={() => setPaused((current) => !current)}
              aria-label={paused ? "Play slideshow" : "Pause slideshow"}
              className="flex size-10 items-center justify-center rounded-full border border-input bg-surface text-ink transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              {paused ? (
                <Play className="size-4" aria-hidden="true" />
              ) : (
                <Pause className="size-4" aria-hidden="true" />
              )}
            </button>
          )}
        </div>

        <div className="flex items-center gap-1" role="group" aria-label="Choose a slide">
          {slides.map((slide, position) => (
            <button
              key={slide.image.src}
              type="button"
              onClick={() => goTo(position)}
              aria-label={`Slide ${position + 1}: ${slide.title}`}
              aria-current={position === index ? "true" : undefined}
              // A 24px target around a small visible dot keeps it easy to tap.
              className="group flex size-6 items-center justify-center rounded-full focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              <span
                className={cn(
                  "block h-2 rounded-full transition-all duration-300",
                  position === index ? "w-6 bg-primary-600" : "w-2 bg-input group-hover:bg-ink-muted",
                )}
              />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
