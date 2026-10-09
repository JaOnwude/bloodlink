/**
 * How many of the units a request asks for have been pledged, as a bar and in words.
 *
 * The bar is a native `progress` element wrapped in a label, so screen readers announce the
 * value; the sentence underneath says the same thing for everyone.
 */

interface UnitsProgressProps {
  needed: number;
  pledged: number;
  /** A smaller version for lists. */
  compact?: boolean;
}

export function UnitsProgress({ needed, pledged, compact = false }: UnitsProgressProps) {
  const shown = Math.min(pledged, needed);
  const remaining = Math.max(needed - pledged, 0);
  const unitWord = (count: number) => (count === 1 ? "unit" : "units");

  return (
    <div className="space-y-1.5">
      <progress
        value={shown}
        max={needed}
        aria-label={`${shown} of ${needed} ${unitWord(needed)} pledged`}
        className={`block w-full overflow-hidden rounded-full bg-secondary [&::-moz-progress-bar]:bg-primary-600 [&::-webkit-progress-bar]:bg-secondary [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-primary-600 ${
          compact ? "h-1.5" : "h-2.5"
        }`}
      />
      <p className={compact ? "text-xs text-ink-muted" : "text-sm text-ink-muted"}>
        <span className="font-medium text-ink">
          {shown} of {needed}
        </span>{" "}
        {unitWord(needed)} pledged
        {remaining > 0 ? ` · ${remaining} still needed` : ""}
      </p>
    </div>
  );
}
