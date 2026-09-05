import type { StyleSpecification } from "maplibre-gl";

// Minimal raster basemap (OSM) — swap for an offline vector style or MapTiler key for the finale.
// Tinted toward the field-survey palette (warm paper, desaturated) instead of full-color OSM.
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
    { id: "bg", type: "background", paint: { "background-color": "#f4f2ea" } },
    { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.75, "raster-saturation": -0.55, "raster-brightness-min": 0.35, "raster-brightness-max": 1 } },
  ],
};

// Matches --green/--yellow/--orange/--red in theme.css (field-survey palette).
export const HAZ_COLORS: Record<string, string> = {
  green: "#3f8f56",
  yellow: "#b78a1e",
  orange: "#c2661e",
  red: "#a83226",
};

export const PRIORITY_COLORS: Record<string, string> = {
  relocate_now: "#a83226",
  plan: "#c2661e",
  monitor: "#b78a1e",
  safe: "#8f8570",
};
