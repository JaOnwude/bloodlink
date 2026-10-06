/**
 * Nigerian cities offered when a donor or hospital sets a location.
 *
 * Choosing a city is easier and more private than typing coordinates. The values are
 * approximate city-centre coordinates, accurate enough to rank requests by distance across a
 * city. People who want a closer match can use their device location instead.
 *
 * The list covers every state capital, the Federal Capital Territory and a few large
 * commercial cities. Someone whose town is not listed should pick the nearest city.
 */

export interface City {
  city: string;
  state: string;
  latitude: number;
  longitude: number;
}

export const NIGERIAN_CITIES: readonly City[] = [
  { city: "Aba", state: "Abia", latitude: 5.1066, longitude: 7.3667 },
  { city: "Abakaliki", state: "Ebonyi", latitude: 6.3249, longitude: 8.1137 },
  { city: "Abeokuta", state: "Ogun", latitude: 7.1475, longitude: 3.3619 },
  { city: "Abuja", state: "Federal Capital Territory", latitude: 9.0765, longitude: 7.3986 },
  { city: "Ado-Ekiti", state: "Ekiti", latitude: 7.6211, longitude: 5.2214 },
  { city: "Akure", state: "Ondo", latitude: 7.2571, longitude: 5.2058 },
  { city: "Asaba", state: "Delta", latitude: 6.198, longitude: 6.735 },
  { city: "Awka", state: "Anambra", latitude: 6.2107, longitude: 7.0718 },
  { city: "Bauchi", state: "Bauchi", latitude: 10.3158, longitude: 9.8442 },
  { city: "Benin City", state: "Edo", latitude: 6.335, longitude: 5.6037 },
  { city: "Birnin Kebbi", state: "Kebbi", latitude: 12.4539, longitude: 4.1975 },
  { city: "Calabar", state: "Cross River", latitude: 4.9757, longitude: 8.3417 },
  { city: "Damaturu", state: "Yobe", latitude: 11.7469, longitude: 11.9608 },
  { city: "Dutse", state: "Jigawa", latitude: 11.7561, longitude: 9.3388 },
  { city: "Enugu", state: "Enugu", latitude: 6.4584, longitude: 7.5464 },
  { city: "Gombe", state: "Gombe", latitude: 10.2897, longitude: 11.1673 },
  { city: "Gusau", state: "Zamfara", latitude: 12.1628, longitude: 6.6614 },
  { city: "Ibadan", state: "Oyo", latitude: 7.3775, longitude: 3.947 },
  { city: "Ilorin", state: "Kwara", latitude: 8.4966, longitude: 4.5421 },
  { city: "Jalingo", state: "Taraba", latitude: 8.8938, longitude: 11.3596 },
  { city: "Jos", state: "Plateau", latitude: 9.8965, longitude: 8.8583 },
  { city: "Kaduna", state: "Kaduna", latitude: 10.5105, longitude: 7.4165 },
  { city: "Kano", state: "Kano", latitude: 12.0022, longitude: 8.592 },
  { city: "Katsina", state: "Katsina", latitude: 12.9908, longitude: 7.6018 },
  { city: "Lafia", state: "Nasarawa", latitude: 8.4933, longitude: 8.5158 },
  { city: "Lagos", state: "Lagos", latitude: 6.5244, longitude: 3.3792 },
  { city: "Lokoja", state: "Kogi", latitude: 7.8023, longitude: 6.7333 },
  { city: "Maiduguri", state: "Borno", latitude: 11.8333, longitude: 13.15 },
  { city: "Makurdi", state: "Benue", latitude: 7.7337, longitude: 8.5214 },
  { city: "Minna", state: "Niger", latitude: 9.6139, longitude: 6.5569 },
  { city: "Onitsha", state: "Anambra", latitude: 6.1498, longitude: 6.7857 },
  { city: "Osogbo", state: "Osun", latitude: 7.7827, longitude: 4.5418 },
  { city: "Owerri", state: "Imo", latitude: 5.4836, longitude: 7.0333 },
  { city: "Port Harcourt", state: "Rivers", latitude: 4.8156, longitude: 7.0498 },
  { city: "Sokoto", state: "Sokoto", latitude: 13.0059, longitude: 5.2476 },
  { city: "Umuahia", state: "Abia", latitude: 5.525, longitude: 7.4896 },
  { city: "Uyo", state: "Akwa Ibom", latitude: 5.0377, longitude: 7.9128 },
  { city: "Warri", state: "Delta", latitude: 5.516, longitude: 5.75 },
  { city: "Yenagoa", state: "Bayelsa", latitude: 4.9267, longitude: 6.2676 },
  { city: "Yola", state: "Adamawa", latitude: 9.2035, longitude: 12.4954 },
];

/** Looks a city up by name, ignoring case. Returns undefined when it is not in the list. */
export function findCity(name: string): City | undefined {
  const wanted = name.trim().toLowerCase();
  return NIGERIAN_CITIES.find((entry) => entry.city.toLowerCase() === wanted);
}

/**
 * Rounds a coordinate to two decimal places, about one kilometre.
 *
 * A device location is far more precise than matching needs. Rounding it before it leaves
 * the browser means the exact position of someone's home is never stored.
 */
export function roundCoordinate(value: number): number {
  return Math.round(value * 100) / 100;
}
