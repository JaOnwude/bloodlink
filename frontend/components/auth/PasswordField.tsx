/**
 * A password field with a show/hide control.
 *
 * Letting people see what they typed matters on phones and for long passphrases, which are
 * easy to mistype. The control is a real button with an accessible name and pressed state.
 */

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

import { FormField } from "@/components/auth/FormField";
import type { FormFieldProps } from "@/components/auth/FormField";
import { Button } from "@/components/ui/button";

export function PasswordField(props: Omit<FormFieldProps, "type" | "trailing">) {
  const [visible, setVisible] = useState(false);

  return (
    <FormField
      {...props}
      type={visible ? "text" : "password"}
      trailing={
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? <EyeOff /> : <Eye />}
        </Button>
      }
    />
  );
}
