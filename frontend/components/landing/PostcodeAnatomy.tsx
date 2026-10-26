/**
 * Nigeria's digital postcode taken apart, and how BloodLink uses each part.
 *
 * The five segments of a sample postcode are labelled (state, LGA, district, area, building
 * unit), then the rings BloodLink alerts in are shown widening from the hospital's own
 * area to its state. It also shows what a donor's profile keeps: the first four segments
 * only, never the building. The postcode is one of NIPOST's published sample codes.
 */

import { cn } from "@/lib/utils";

const SEGMENTS = [
  { code: "FC", label: "State", detail: "Federal Capital Territory" },
  { code: "01", label: "LGA", detail: "Abaji" },
  { code: "A01", label: "District", detail: "within the LGA" },
  { code: "KP", label: "Area", detail: "a neighbourhood" },
  { code: "27", label: "Unit", detail: "one building" },
];

const RINGS = [
  { prefix: "FC-01-A01-KP", label: "Same postcode area", note: "texted first", width: "w-1/4" },
  { prefix: "FC-01-A01", label: "Same district", note: "then", width: "w-1/2" },
  { prefix: "FC-01", label: "Same LGA", note: "then", width: "w-3/4" },
  { prefix: "FC", label: "Same state", note: "last", width: "w-full" },
];

export function PostcodeAnatomy() {
  return (
    <div className="space-y-6 rounded-3xl bg-white/5 p-6 ring-1 ring-white/10 sm:p-8">
      <div>
        <p className="text-xs font-semibold tracking-wider text-white/60 uppercase">
          One building, five parts
        </p>
        <ol className="mt-4 grid grid-cols-5 gap-1.5 sm:gap-2" aria-label="Parts of a postcode">
          {SEGMENTS.map((segment, index) => (
            <li key={segment.label} className="text-center">
              <span
                className={cn(
                  "block rounded-xl py-3 font-mono text-lg font-semibold sm:text-2xl",
                  index === SEGMENTS.length - 1
                    ? "border border-dashed border-white/40 bg-white/5 text-white/70"
                    : "bg-primary-600 text-white",
                )}
              >
                {segment.code}
              </span>
              <span className="mt-2 block text-xs font-semibold text-white">{segment.label}</span>
              <span className="hidden text-[11px] text-white/60 sm:block">{segment.detail}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-white/60">
          A donor&apos;s profile keeps only the first four parts. The building unit is checked with
          NIPOST and then dropped, so a donor&apos;s home is never stored.
        </p>
      </div>

      <div>
        <p className="text-xs font-semibold tracking-wider text-white/60 uppercase">
          Who hears about a request, in order
        </p>
        <ol className="mt-4 space-y-3">
          {RINGS.map((ring) => (
            <li key={ring.prefix} className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-white">
                  {ring.label} <span className="text-white/50">· {ring.note}</span>
                </span>
                <span className="font-mono text-xs whitespace-nowrap text-white/70">
                  {ring.prefix}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10">
                <div className={cn("h-1.5 rounded-full bg-primary-500", ring.width)} />
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
