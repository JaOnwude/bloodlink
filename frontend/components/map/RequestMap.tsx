/**
 * Map of a request: the hospital, the search radius, and where matching donors are.
 *
 * Donor positions come from the server already rounded to a grid of about a kilometre, so
 * the map shows neighbourhoods, never homes. Donors who share a grid square are drawn as
 * one marker that is larger and labelled with how many there are.
 *
 * Leaflet touches `window` when it loads, so this module must only be imported in the
 * browser. Use `MapPanel`, which loads it that way, rather than importing it directly.
 *
 * Markers are drawn shapes rather than Leaflet's default image pins, which do not survive
 * bundling. Leaflet sets colours as SVG attributes, where CSS variables do not apply, so
 * the colours below are copies of the design tokens in styles/globals.css.
 */

import "leaflet/dist/leaflet.css";

import type { LatLngBoundsExpression } from "leaflet";
import { latLng } from "leaflet";
import { useEffect, useMemo } from "react";
import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";

import type { BloodGroup } from "@/types/api";

// Copies of design tokens (see the module note): primary-600, primary-700, trust-600.
const HOSPITAL_COLOUR = "#b91c32";
const RADIUS_COLOUR = "#9a1429";
const DONOR_COLOUR = "#0f766e";

export interface MapDonor {
  id: string;
  bloodGroup: BloodGroup;
  latitude: number;
  longitude: number;
  distanceKm: number;
}

export interface RequestMapProps {
  hospital: { name: string; latitude: number; longitude: number };
  radiusKm: number;
  donors: MapDonor[];
}

interface DonorCluster {
  key: string;
  latitude: number;
  longitude: number;
  groups: BloodGroup[];
  nearestKm: number;
}

/** Combine donors who share a grid square into one marker. */
function clusterDonors(donors: MapDonor[]): DonorCluster[] {
  const clusters = new Map<string, DonorCluster>();
  for (const donor of donors) {
    const key = `${donor.latitude},${donor.longitude}`;
    const existing = clusters.get(key);
    if (existing) {
      existing.groups.push(donor.bloodGroup);
      existing.nearestKm = Math.min(existing.nearestKm, donor.distanceKm);
    } else {
      clusters.set(key, {
        key,
        latitude: donor.latitude,
        longitude: donor.longitude,
        groups: [donor.bloodGroup],
        nearestKm: donor.distanceKm,
      });
    }
  }
  return [...clusters.values()];
}

function describeCluster(cluster: DonorCluster): string {
  const count = cluster.groups.length;
  const groups = [...new Set(cluster.groups)].join(", ");
  const people = count === 1 ? "1 donor" : `${count} donors`;
  return `${people} (${groups}), about ${cluster.nearestKm.toFixed(1)} km away`;
}

/** Keeps the whole search circle in view whenever the radius changes. */
function FitToRadius({ center, radiusKm }: { center: [number, number]; radiusKm: number }) {
  const map = useMap();
  useEffect(() => {
    const bounds = latLng(center).toBounds(radiusKm * 2000);
    map.fitBounds(bounds as LatLngBoundsExpression, { padding: [16, 16] });
  }, [map, center, radiusKm]);
  return null;
}

export default function RequestMap({ hospital, radiusKm, donors }: RequestMapProps) {
  const center = useMemo<[number, number]>(
    () => [hospital.latitude, hospital.longitude],
    [hospital.latitude, hospital.longitude],
  );
  const clusters = useMemo(() => clusterDonors(donors), [donors]);

  return (
    <MapContainer
      center={center}
      zoom={11}
      scrollWheelZoom={false}
      className="h-72 w-full rounded-2xl sm:h-80"
      // The ranked list beside the map carries the same information for screen readers.
      aria-label={`Map of ${hospital.name} and nearby donors`}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />
      <FitToRadius center={center} radiusKm={radiusKm} />

      <Circle
        center={center}
        radius={radiusKm * 1000}
        pathOptions={{ color: RADIUS_COLOUR, weight: 1, dashArray: "4 6", fillOpacity: 0.04 }}
      />

      {clusters.map((cluster) => (
        <CircleMarker
          key={cluster.key}
          center={[cluster.latitude, cluster.longitude]}
          radius={Math.min(6 + (cluster.groups.length - 1) * 2, 16)}
          pathOptions={{ color: "#ffffff", weight: 2, fillColor: DONOR_COLOUR, fillOpacity: 0.85 }}
        >
          <Tooltip>{describeCluster(cluster)}</Tooltip>
        </CircleMarker>
      ))}

      <CircleMarker
        center={center}
        radius={9}
        pathOptions={{ color: "#ffffff", weight: 3, fillColor: HOSPITAL_COLOUR, fillOpacity: 1 }}
      >
        <Tooltip permanent direction="top" offset={[0, -10]}>
          {hospital.name}
        </Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
