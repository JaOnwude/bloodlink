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

/** One photograph in the landing page carousel, with the words shown over it. */
export interface CarouselSlide {
  image: SiteImage;
  title: string;
  body: string;
}

/**
 * The landing page carousel: one photograph for each step of the story, from the request
 * to the donor drive. Every picture was checked by eye against its caption. The people
 * shown are not BloodLink users, and the page says so under the carousel.
 */
export const carouselSlides: CarouselSlide[] = [
  {
    image: {
      src: pexels(6129154, 1600),
      alt: "A doctor and a nurse reviewing a patient's chart in a hospital corridor beside an emergency sign.",
      objectPosition: "50% 30%",
      credit: {
        author: "RDNE Stock project",
        source: "Pexels",
        url: "https://www.pexels.com/photo/doctor-reading-a-medical-chart-held-by-a-nurse-6129154/",
      },
    },
    title: "A request in under a minute",
    body: "Blood group, units and deadline. Matched donors are texted straight away, nearest first.",
  },
  {
    image: {
      src: pexels(12193103, 1600),
      alt: "A donor's arm connected to a blood bag that is filling on a collection mixer.",
      objectPosition: "50% 50%",
      credit: {
        author: "Frank Meriño",
        source: "Pexels",
        url: "https://www.pexels.com/photo/a-blood-collector-attached-on-a-person-s-hand-12193103/",
      },
    },
    title: "Every pledge, tracked to a donation",
    body: "Donors commit to one unit each. The request closes itself when it has enough.",
  },
  {
    image: {
      src: pexels(5721681, 1600),
      alt: "A laboratory scientist looking closely through a microscope.",
      objectPosition: "50% 35%",
      credit: {
        author: "cottonbro studio",
        source: "Pexels",
        url: "https://www.pexels.com/photo/a-woman-looking-through-a-microscope-5721681/",
      },
    },
    title: "Screened before it is used",
    body: "Eligibility is checked before anyone is texted. Your lab still screens every unit, as it always does.",
  },
  {
    image: {
      src: pexels(8248293, 1600),
      alt: "A health worker checking the blood pressure of a smiling older woman at a community health event.",
      objectPosition: "40% 40%",
      credit: {
        author: "Lagos Food Bank Initiative",
        source: "Pexels",
        url: "https://www.pexels.com/photo/doctor-measuring-blood-pressure-8248293/",
      },
    },
    title: "Donors from the community",
    body: "Donor drives with employers, churches, mosques and universities grow the pool before the emergency.",
  },
  {
    image: {
      src: pexels(5452224, 1600),
      alt: "Two doctors in white coats reviewing results together at a desk.",
      objectPosition: "50% 25%",
      credit: {
        author: "Tima Miroshnichenko",
        source: "Pexels",
        url: "https://www.pexels.com/photo/woman-in-white-button-up-long-sleeve-shirt-5452224/",
      },
    },
    title: "Verified hospitals only",
    body: "Every hospital is checked before it can contact a donor, so every alert is real.",
  },
];

/**
 * The photographs that cross-fade behind the landing page headline, in story order: a nurse
 * prepares a donor's arm, blood is drawn, a donation is under way, the units are bagged and
 * labelled by group, and a sample goes to the laboratory. Each was checked by eye against its
 * description. They sit behind a dark overlay, so they are decorative (empty `alt`); the
 * headline carries the meaning. The people shown are models, not BloodLink users, and the
 * hero says so.
 */
export const heroPhotos: SiteImage[] = [
  {
    src: pexels(8460349, 1920),
    alt: "",
    objectPosition: "60% 40%",
    credit: {
      author: "Los Muertos Crew",
      source: "Pexels",
      url: "https://www.pexels.com/photo/nurse-wiping-the-arm-of-a-patient-8460349/",
    },
  },
  {
    src: pexels(35645524, 1920),
    alt: "",
    objectPosition: "60% 50%",
    credit: {
      author: "Sahil Singh",
      source: "Pexels",
      url: "https://www.pexels.com/photo/phlebotomy-procedure-in-medical-clinic-35645524/",
    },
  },
  {
    src: pexels(37553398, 1920),
    alt: "",
    objectPosition: "60% 50%",
    credit: {
      author: "Tahir Xəlfəquliyev",
      source: "Pexels",
      url: "https://www.pexels.com/photo/healthcare-professional-conducting-blood-donation-37553398/",
    },
  },
  {
    src: pexels(4531304, 1920),
    alt: "",
    objectPosition: "50% 50%",
    credit: {
      author: "Charlie-Helen Robinson",
      source: "Pexels",
      url: "https://www.pexels.com/photo/bags-of-blood-4531304/",
    },
  },
  {
    src: pexels(8460346, 1920),
    alt: "",
    objectPosition: "55% 45%",
    credit: {
      author: "Los Muertos Crew",
      source: "Pexels",
      url: "https://www.pexels.com/photo/person-holding-a-blood-sample-in-a-test-tube-8460346/",
    },
  },
];
