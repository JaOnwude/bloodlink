/**
 * Every photograph used on the site, in one place.
 *
 * Pages never hard-code an image address. They look an image up here by name, so replacing a
 * photo is a one-line change. To use your own picture, save it under `public/images/` and
 * point `src` at it, for example `src: "/images/auth-signin.jpg"`.
 *
 * The photos below are free-to-use placeholders from Pexels (see https://www.pexels.com/license/).
 * Attribution is not required but is recorded in `credit`. They show models, not BloodLink
 * donors or patients, and must never be presented as such.
 */

export interface SiteImage {
  /** Image address: a path under /public, or an allowed remote address. */
  src: string;
  /** Describes the picture for people who cannot see it. Empty means purely decorative. */
  alt: string;
  /** Which part of the picture stays in view when it is cropped to fit its frame. */
  objectPosition?: string;
  credit?: { author: string; source: string; url: string };
}

function pexels(id: number, width: number): string {
  return `https://images.pexels.com/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=${width}`;
}

export const images = {
  /** Beside the sign-in form. */
  authSignIn: {
    src: pexels(6098051, 1600),
    alt: "",
    objectPosition: "50% 25%",
    credit: {
      author: "Laura James",
      source: "Pexels",
      url: "https://www.pexels.com/photo/focused-woman-with-documents-in-hospital-6098051/",
    },
  },

  /** Beside the register form. */
  authRegister: {
    src: pexels(6097758, 1600),
    alt: "",
    objectPosition: "50% 25%",
    credit: {
      author: "Laura James",
      source: "Pexels",
      url: "https://www.pexels.com/photo/attentive-black-physician-reading-document-on-clipboard-6097758/",
    },
  },
} satisfies Record<string, SiteImage>;
