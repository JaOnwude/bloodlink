/**
 * Photographs of each step of the story as a grid of cards, for the landing page.
 *
 * Every card shows its photo, a short title and one sentence, all at once: nothing to click
 * through, and it fits any screen. On a laptop the first two cards sit side by side in a
 * wider frame and the rest share the row below; on a tablet they go two by two, and on a
 * phone one by one. The photo zooms slightly when the card is hovered, for visitors who have
 * not asked for reduced motion. Photos load lazily and fill a fixed-ratio frame, so the page does not
 * jump while they arrive; a crimson tint sits behind each, so a failed image still looks
 * intended.
 */

import Image from "next/image";

import { Reveal } from "@/components/motion/Reveal";
import type { CarouselSlide } from "@/lib/images";
import { cn } from "@/lib/utils";

export function PhotoCards({ slides }: { slides: CarouselSlide[] }) {
  return (
    <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-6">
      {slides.map((slide, index) => (
        <Reveal
          as="li"
          key={slide.title}
          delay={(index % 3) * 80}
          className={cn(
            "group overflow-hidden rounded-3xl border border-border bg-surface shadow-soft transition-shadow duration-250 ease-brand hover:shadow-lift",
            // Two wide cards on top, then the rest three to a row, so every row is full.
            index < 2 ? "lg:col-span-3" : "lg:col-span-2",
            // An odd last card on a tablet takes the whole row.
            index === slides.length - 1 && slides.length % 2 === 1 && "sm:col-span-2 lg:col-span-2",
          )}
        >
          <div
            className={cn(
              "relative aspect-[4/3] overflow-hidden bg-primary-100",
              index < 2 && "lg:aspect-[16/10]",
              // The full-width odd card on a tablet gets a wide, short frame.
              index === slides.length - 1 &&
                slides.length % 2 === 1 &&
                "sm:aspect-[21/9] lg:aspect-[4/3]",
            )}
          >
            <Image
              src={slide.image.src}
              alt={slide.image.alt}
              fill
              sizes="(min-width: 1024px) 50vw, (min-width: 640px) 50vw, 100vw"
              className="object-cover transition-transform duration-700 ease-brand motion-safe:group-hover:scale-105"
              style={{ objectPosition: slide.image.objectPosition }}
            />
          </div>
          <div className="space-y-2 p-6">
            <h3 className="font-heading text-lg font-semibold text-ink">{slide.title}</h3>
            <p className="text-ink-muted">{slide.body}</p>
          </div>
        </Reveal>
      ))}
    </ul>
  );
}
