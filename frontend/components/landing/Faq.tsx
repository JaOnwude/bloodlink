/**
 * Frequently asked questions, as an accordion.
 *
 * Built on the native <details> and <summary> elements, so every question opens with a
 * click, a tap or the keyboard, and screen readers announce it as expandable, without any
 * script. Answers describe what BloodLink actually does today; anything planned is said to
 * be planned.
 */

import { ChevronDown } from "lucide-react";

export interface FaqItem {
  question: string;
  answer: string;
}

export function Faq({ items }: { items: FaqItem[] }) {
  return (
    <div className="divide-y divide-border overflow-hidden rounded-3xl border border-border bg-surface">
      {items.map((item) => (
        <details key={item.question} className="group">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-6 py-5 font-heading text-lg font-semibold text-ink transition-colors hover:bg-canvas focus-visible:bg-canvas focus-visible:outline-none [&::-webkit-details-marker]:hidden">
            {item.question}
            <ChevronDown
              className="size-5 shrink-0 text-primary-600 transition-transform duration-250 group-open:rotate-180"
              aria-hidden="true"
            />
          </summary>
          <p className="px-6 pb-6 text-ink-muted">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}
