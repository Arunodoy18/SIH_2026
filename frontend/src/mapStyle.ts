import type { StyleSpecification } from "maplibre-gl";

// Minimal raster basemap (OSM) — swap for an offline vector style or MapTiler key for the finale.
export const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#0f1419" } },
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.55, "raster-saturation": -0.6, "raster-brightness-max": 0.85 } },
  ],
};

export const HAZ_COLORS: Record<string, string> = {
  green: "#2fbf71",
  yellow: "#e5b83b",
  orange: "#ef8a3c",
  red: "#e5484d",
};

export const PRIORITY_COLORS: Record<string, string> = {
  relocate_now: "#e5484d",
  plan: "#ef8a3c",
  monitor: "#e5b83b",
  safe: "#3d5166",
};
