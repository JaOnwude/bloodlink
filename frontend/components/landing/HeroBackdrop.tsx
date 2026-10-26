/**
 * The photographs behind the landing page headline, cross-fading one into the next.
 *
 * Each photo stays for a few seconds and zooms in very slowly while it is shown, then fades
 * into the next, so the hero feels alive without pulling the eye from the headline. A dark
 * overlay keeps the white text readable whichever photo is showing, with a crimson glow in
 * the brand colour.
 *
 * Because it moves on its own for longer than five seconds, it has a visible pause button
 * (WCAG 2.2.2). For visitors who have asked for reduced motion it never moves: the first
 * photo is shown still. The photos are decorative; the headline carries the meaning.
 *
 * Only the first photo is loaded straight away; the rest load quietly after it, so the page
 * appears as fast as a single-image hero would.
 */

import { Pause, Play } from "lucide-react";
import Image from "next/image";
import { useEffect, useState } from "react";

import type { SiteImage } from "@/lib/images";
import { usePrefersReducedMotion } from "@/lib/use-prefers-reduced-motion";
import { cn } from "@/lib/utils";

/** How long each photo stays before the next fades in, in milliseconds. */
const PHOTO_INTERVAL_MS = 6500;

export function HeroBackdrop({ photos }: { photos: SiteImage[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const reducedMotion = usePrefersReducedMotion();
  const count = photos.length;
  const playing = !paused && !reducedMotion && count > 1;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(
      () => setIndex((current) => (current + 1) % count),
      PHOTO_INTERVAL_MS,
    );
    return () => window.clearTimeout(timer);
  }, [playing, index, count]);

  if (count === 0) return null;

  return (
    <>
      <div className="absolute inset-0 -z-10 overflow-hidden bg-night" aria-hidden="true">
        {photos.map((photo, position) => {
          const active = position === index;
          return (
            <div
              key={photo.src}
              className={cn(
                "absolute inset-0 transition-opacity duration-[1400ms] ease-in-out",
                active ? "opacity-100" : "opacity-0",
              )}
            >
              {/* The key restarts the slow zoom each time this photo comes back. */}
              <div
                key={active ? `on-${index}` : "off"}
                className={cn("absolute inset-0", active && playing && "hero-zoom")}
              >
                <Image
                  src={photo.src}
                  alt=""
                  fill
                  sizes="100vw"
                  preload={position === 0}
                  className="object-cover"
                  style={{ objectPosition: photo.objectPosition }}
                />
              </div>
            </div>
          );
        })}
        {/* Darkest on the left behind the text, lighter on the right where the cards sit. */}
        <div className="absolute inset-0 bg-night/80 lg:bg-transparent lg:bg-gradient-to-r lg:from-night/95 lg:via-night/80 lg:to-night/45" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_85%_110%,rgb(185_28_50/0.45),transparent_60%)]" />
      </div>

      {count > 1 && !reducedMotion ? (
        <div className="absolute bottom-5 left-1/2 z-10 flex -translate-x-1/2 items-center gap-3 sm:left-8 sm:translate-x-0">
          <button
            type="button"
            onClick={() => setPaused((current) => !current)}
            className="flex size-8 items-center justify-center rounded-full bg-white/10 text-white ring-1 ring-white/25 transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            aria-label={paused ? "Play background photos" : "Pause background photos"}
          >
            {paused ? <Play className="size-3.5" /> : <Pause className="size-3.5" />}
          </button>
          <div className="flex gap-1.5" aria-hidden="true">
            {photos.map((photo, position) => (
              <span
                key={photo.src}
                className={cn(
                  "h-1.5 rounded-full transition-all duration-500",
                  position === index ? "w-6 bg-white" : "w-1.5 bg-white/40",
                )}
              />
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
