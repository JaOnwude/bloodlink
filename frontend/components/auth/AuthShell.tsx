/**
 * The shared layout of the sign-in and register pages: the form on one side and the
 * photograph panel on the other.
 */

import type { ReactNode } from "react";

import { ImagePanel } from "@/components/auth/ImagePanel";
import { Reveal } from "@/components/motion/Reveal";
import type { SiteImage } from "@/lib/images";

interface AuthShellProps {
  title: string;
  description: string;
  image: SiteImage;
  panelHeading: string;
  panelPoints: string[];
  /** The form. */
  children: ReactNode;
  /** A line under the form, such as a link to the other page. */
  footer?: ReactNode;
}

export function AuthShell({
  title,
  description,
  image,
  panelHeading,
  panelPoints,
  children,
  footer,
}: AuthShellProps) {
  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-2">
      <div className="flex items-center justify-center px-5 py-12 sm:px-8 lg:py-16">
        <div className="w-full max-w-md">
          <Reveal>
            <h1 className="text-title font-semibold text-ink">{title}</h1>
            <p className="mt-3 text-ink-muted">{description}</p>
          </Reveal>
          <Reveal delay={80} className="mt-8">
            {children}
          </Reveal>
          {footer ? <div className="mt-8 text-sm text-ink-muted">{footer}</div> : null}
        </div>
      </div>

      <ImagePanel image={image} heading={panelHeading} points={panelPoints} />
    </div>
  );
}
