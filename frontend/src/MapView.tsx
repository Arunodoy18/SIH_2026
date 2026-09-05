import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { BASE_STYLE, HAZ_COLORS, PRIORITY_COLORS } from "./mapStyle";

export type LayerKey =
  | "hazard_tiers" | "habitations" | "glacial_lakes" | "rivers"
  | "destination_sites" | "historical_losses" | "flows";

interface Data {
  hazard_tiers?: GeoJSON.FeatureCollection;
  habitations?: GeoJSON.FeatureCollection;
  glacial_lakes?: GeoJSON.FeatureCollection;
  rivers?: GeoJSON.FeatureCollection;
  destination_sites?: GeoJSON.FeatureCollection;
  historical_losses?: GeoJSON.FeatureCollection;
  flows?: GeoJSON.FeatureCollection;
}

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export function MapView({
  data, visible, colourBy, selected, onSelect,
}: {
  data: Data;
  visible: Record<LayerKey, boolean>;
  colourBy: "priority" | "hazard";
  selected: string | null;
  onSelect: (habId: string | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const m = new maplibregl.Map({
      container: ref.current,
      style: BASE_STYLE,
      center: [88.55, 27.62],
      zoom: 8.6,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    m.on("load", () => {
      for (const id of ["hazard_tiers", "habitations", "glacial_lakes", "rivers", "destination_sites", "historical_losses", "flows"]) {
        m.addSource(id, { type: "geojson", data: EMPTY });
      }

      m.addLayer({
        id: "hazard_tiers-fill", source: "hazard_tiers", type: "fill",
        paint: {
          "fill-color": ["match", ["get", "tier"], "red", HAZ_COLORS.red, "orange", HAZ_COLORS.orange, "yellow", HAZ_COLORS.yellow, HAZ_COLORS.green],
          "fill-opacity": ["match", ["get", "tier"], "green", 0.06, "yellow", 0.14, "orange", 0.22, 0.32],
        },
      });

      m.addLayer({
        id: "habitations-fill", source: "habitations", type: "fill",
        paint: {
          "fill-color": [
            "case",
            ["==", ["get", "priority_tier"], "relocate_now"], PRIORITY_COLORS.relocate_now,
            ["==", ["get", "priority_tier"], "plan"], PRIORITY_COLORS.plan,
            ["==", ["get", "priority_tier"], "monitor"], PRIORITY_COLORS.monitor,
            PRIORITY_COLORS.safe,
          ],
          "fill-opacity": 0.45,
        },
      });
      m.addLayer({
        id: "habitations-line", source: "habitations", type: "line",
        paint: {
          "line-color": ["case", ["==", ["get", "hab_id"], ["literal", ""]], "#fff", "#0b0f14"],
          "line-width": 0.6,
        },
      });
      m.addLayer({
        id: "habitations-sel", source: "habitations", type: "line",
        filter: ["==", ["get", "hab_id"], ""],
        paint: { "line-color": "#b7410e", "line-width": 2.5 },
      });

      m.addLayer({
        id: "rivers-line", source: "rivers", type: "line",
        paint: { "line-color": "#2b5f63", "line-width": 1.4, "line-opacity": 0.65 },
      });
      m.addLayer({
        id: "glacial_lakes-line", source: "glacial_lakes", type: "line",
        paint: { "line-color": "#b7410e", "line-width": 2, "line-dasharray": [2, 1.5], "line-opacity": 0.8 },
      });
      m.addLayer({
        id: "flows-line", source: "flows", type: "line",
        paint: {
          "line-color": ["match", ["get", "phase"], 1, "#a83226", "#c2661e"],
          "line-width": ["interpolate", ["linear"], ["get", "persons"], 100, 1.5, 4000, 6],
          "line-opacity": 0.85,
        },
      });
      m.addLayer({
        id: "destination_sites-pt", source: "destination_sites", type: "circle",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "spare_capacity"], 500, 5, 4000, 14],
          "circle-color": "#3f8f56", "circle-opacity": 0.6,
          "circle-stroke-color": "#fffdf8", "circle-stroke-width": 1.6,
        },
      });
      m.addLayer({
        id: "historical_losses-pt", source: "historical_losses", type: "circle",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "houses_damaged"], 10, 3, 350, 11],
          "circle-color": "#8a5a7c", "circle-opacity": 0.6,
          "circle-stroke-color": "#fffdf8", "circle-stroke-width": 1.2,
        },
      });

      m.on("click", "habitations-fill", (e) => {
        const f = e.features?.[0];
        if (f) onSelect(String(f.properties?.hab_id));
      });
      m.on("mouseenter", "habitations-fill", () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", "habitations-fill", () => (m.getCanvas().style.cursor = ""));

      for (const src of ["destination_sites", "glacial_lakes", "historical_losses", "flows"]) {
        m.on("click", `${src}-${src === "flows" || src === "glacial_lakes" ? "line" : "pt"}`, (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const p = f.properties || {};
          const html = Object.entries(p)
            .map(([k, v]) => `<div><b>${k}</b>: ${v}</div>`).join("");
          new maplibregl.Popup({ closeButton: true })
            .setLngLat(e.lngLat).setHTML(`<div style="color:#111;font-size:11px">${html}</div>`).addTo(m);
        });
      }

      ready.current = true;
      setMapReady(true); // triggers the push effects below with current props (no stale closure)
    });

    return () => m.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pushData() {
    const m = map.current;
    if (!m || !ready.current) return;
    (["hazard_tiers", "habitations", "glacial_lakes", "rivers", "destination_sites", "historical_losses", "flows"] as const).forEach((k) => {
      const s = m.getSource(k) as maplibregl.GeoJSONSource | undefined;
      if (s) s.setData((data[k] as any) || EMPTY);
    });
  }
  function pushVisibility() {
    const m = map.current;
    if (!m || !ready.current) return;
    const set = (id: string, on: boolean) => m.getLayer(id) && m.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    set("hazard_tiers-fill", visible.hazard_tiers);
    set("habitations-fill", visible.habitations);
    set("habitations-line", visible.habitations);
    set("habitations-sel", visible.habitations);
    set("rivers-line", visible.rivers);
    set("glacial_lakes-line", visible.glacial_lakes);
    set("destination_sites-pt", visible.destination_sites);
    set("historical_losses-pt", visible.historical_losses);
    set("flows-line", visible.flows);
  }
  function pushColour() {
    const m = map.current;
    if (!m || !ready.current || !m.getLayer("habitations-fill")) return;
    if (colourBy === "hazard") {
      m.setPaintProperty("habitations-fill", "fill-color", [
        "match", ["get", "haz_tier"], "red", HAZ_COLORS.red, "orange", HAZ_COLORS.orange, "yellow", HAZ_COLORS.yellow, HAZ_COLORS.green,
      ] as any);
    } else {
      m.setPaintProperty("habitations-fill", "fill-color", [
        "case",
        ["==", ["get", "priority_tier"], "relocate_now"], PRIORITY_COLORS.relocate_now,
        ["==", ["get", "priority_tier"], "plan"], PRIORITY_COLORS.plan,
        ["==", ["get", "priority_tier"], "monitor"], PRIORITY_COLORS.monitor,
        PRIORITY_COLORS.safe,
      ] as any);
    }
  }
  function pushSelection() {
    const m = map.current;
    if (!m || !ready.current || !m.getLayer("habitations-sel")) return;
    m.setFilter("habitations-sel", ["==", ["get", "hab_id"], selected || " "]);
  }

  useEffect(pushData, [data, mapReady]);
  useEffect(pushVisibility, [visible, mapReady]);
  useEffect(pushColour, [colourBy, mapReady]);
  useEffect(pushSelection, [selected, mapReady]);

  return <div ref={ref} style={{ position: "absolute", inset: 0 }} />;
}
