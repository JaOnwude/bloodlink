/**
 * Site-wide configuration shared by the header, footer and metadata.
 *
 * Navigation lives here so that adding a page to the menu is a one-line change. Entries
 * should be added only once the page exists, so that no visible link leads to an error.
 */

export interface NavItem {
  label: string;
  href: string;
}

export interface FooterGroup {
  title: string;
  links: NavItem[];
}

export const siteConfig = {
  name: "BloodLink",
  description:
    "BloodLink matches verified hospitals with compatible, eligible donors nearby, then tracks every pledge through to a confirmed donation.",

  /** Links shown in the main navigation. */
  nav: [
    { label: "How it works", href: "/#how-it-works" },
    { label: "Pricing", href: "/#pricing" },
    { label: "For donors", href: "/#donors" },
  ] as NavItem[],

  /** Link columns shown in the footer. Empty groups are not rendered. */
  footerGroups: [
    {
      title: "Hospitals",
      links: [
        { label: "How it works", href: "/#how-it-works" },
        { label: "Pricing", href: "/#pricing" },
        { label: "Register your hospital", href: "/register?as=hospital" },
      ],
    },
    {
      title: "Donors",
      links: [
        { label: "Why donate", href: "/#donors" },
        { label: "Become a donor", href: "/register" },
        { label: "Sign in", href: "/login" },
      ],
    },
  ] as FooterGroup[],

  /** Where the account buttons in the header lead. */
  accountLinks: {
    signIn: "/login",
    register: "/register",
  },
} as const;
