/**
 * The decorative panel beside the sign-in and register forms: a photograph under a dark
 * gradient, with a short statement of what BloodLink promises.
 *
 * A crimson gradient sits behind the photo, so if the photo is missing or fails to load,
 * the panel still looks finished. The panel is hidden on small screens, where the form
 * needs the whole width, and the photo is lazy-loaded, so phones never download it.
 */

import { ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import type { SiteImage } from "@/lib/images";

interface ImagePanelProps {
  image: SiteImage;
  heading: string;
  points: string[];
}

export function ImagePanel({ image, heading, points }: ImagePanelProps) {
  const [failed, setFailed] = useState(false);

  return (
    <aside className="relative hidden overflow-hidden bg-linear-to-br from-primary-700 via-primary-900 to-night lg:block">
      {failed ? null : (
        <Image
          src={image.src}
          alt={image.alt}
          fill
          sizes="(min-width: 1024px) 50vw, 100vw"
          className="object-cover"
          style={{ objectPosition: image.objectPosition }}
          onError={() => setFailed(true)}
        />
      )}

      {/* Darkens the lower part of the photo so the text stays readable on any picture. */}
      <div className="absolute inset-0 bg-linear-to-t from-night via-night/55 to-night/10" />

      <div className="relative flex h-full min-h-[32rem] flex-col justify-end p-10 xl:p-14">
        <p className="inline-flex w-fit items-center gap-2 rounded-full bg-ivory/15 px-3 py-1.5 text-sm font-medium text-ivory backdrop-blur">
          <ShieldCheck className="size-4" aria-hidden="true" />
          Verified hospitals only
        </p>
        <h2 className="mt-5 max-w-md font-heading text-heading font-semibold text-ivory">
          {heading}
        </h2>
        <ul className="mt-5 max-w-md space-y-2.5 text-ivory/85">
          {points.map((point) => (
            <li key={point} className="flex gap-3">
              <span
                className="mt-2 size-1.5 shrink-0 rounded-full bg-primary-500"
                aria-hidden="true"
              />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
