/**
 * Two large selectable cards for choosing what the new account is for.
 *
 * Built on native radio buttons, so keyboard use, arrow-key movement and screen reader
 * announcements all work without extra code. The visual selected state is driven by the
 * radio's checked state.
 */

import { Building2, HeartHandshake } from "lucide-react";
import type { ReactNode } from "react";

export type SelfServiceRole = "donor" | "hospital_staff";

interface RoleOption {
  value: SelfServiceRole;
  title: string;
  description: string;
  icon: ReactNode;
}

const options: RoleOption[] = [
  {
    value: "donor",
    title: "I want to donate",
    description: "Get alerts when someone near you needs your blood group.",
    icon: <HeartHandshake className="size-5" aria-hidden="true" />,
  },
  {
    value: "hospital_staff",
    title: "I work at a hospital",
    description: "Register your facility and request blood from verified donors.",
    icon: <Building2 className="size-5" aria-hidden="true" />,
  },
];

interface RoleChoiceProps {
  value: SelfServiceRole;
  onChange: (role: SelfServiceRole) => void;
}

export function RoleChoice({ value, onChange }: RoleChoiceProps) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-ink">What brings you to BloodLink?</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {options.map((option) => (
          <label key={option.value} className="relative block cursor-pointer">
            <input
              type="radio"
              name="role"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="peer sr-only"
            />
            <span className="flex h-full flex-col gap-2 rounded-2xl border border-input bg-surface p-4 transition-colors duration-150 peer-checked:border-primary-600 peer-checked:bg-primary-50 peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background">
              <span className="text-primary-600">{option.icon}</span>
              <span className="text-sm font-semibold text-ink">{option.title}</span>
              <span className="text-sm text-ink-muted">{option.description}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
