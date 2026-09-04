"""Synthetic — but structurally realistic — Sikkim dataset for the Mangan / Teesta corridor.

Produces GeoParquet in data/interim/:
    habitations.parquet        GPU-level polygons + census/SECC/physio attributes
    glacial_lakes.parquet      upstream lakes with 2000 vs 2024 area, dam type, volume
    rivers.parquet             Teesta main stem + Lachen/Lachung/Dik tributaries
    faults.parquet             active lineament traces (seismic modifier)
    destination_sites.parquet  candidate green resettlement sites with spare capacity
    historical_losses.parquet  ~24 disaster-loss events 2000-2024 (calibration target)

Nothing here is an official figure. Real layers are swapped in via redzone/data/adapters/.
Deterministic: seeded RNG. Re-run any time with `python -m redzone.seed.generate_sikkim`.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely import voronoi_polygons
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from redzone.config import AOI_BBOX, CRS_GEO, CRS_METRIC, INTERIM_DIR

RNG = np.random.default_rng(42)

# --------------------------------------------------------------------------------------
# 1. Habitations — hand-placed GPU/settlement centroids along the corridor
#    (name, lat, lon, block, seed_population, chronic_landslide_incidents)
# --------------------------------------------------------------------------------------
_HABITATIONS = [
    # --- North Sikkim, upper Teesta / Lachen–Lachung (Mangan district) ---
    ("Lachen", 27.717, 88.555, "Chungthang", 2600, 2),
    ("Lachung", 27.691, 88.743, "Chungthang", 2400, 2),
    ("Chungthang", 27.600, 88.644, "Chungthang", 4200, 5),
    ("Munshithang", 27.640, 88.640, "Chungthang", 1100, 3),
    ("Bop", 27.560, 88.662, "Chungthang", 700, 2),
    ("Toong", 27.560, 88.610, "Mangan", 1300, 3),
    ("Singhik", 27.545, 88.560, "Mangan", 1900, 2),
    ("Mangan", 27.507, 88.535, "Mangan", 5200, 4),
    ("Sankalang", 27.480, 88.560, "Mangan", 1400, 3),
    ("Namok", 27.470, 88.590, "Mangan", 1600, 2),
    ("Mangshila", 27.470, 88.520, "Mangan", 2100, 1),
    ("Pentong", 27.430, 88.560, "Mangan", 1200, 2),
    # --- Dzongu (Lepcha reserve, west bank — restricted single-bridge access) ---
    ("Passingdang", 27.560, 88.520, "Dzongu", 1500, 3),
    ("Tingvong", 27.610, 88.500, "Dzongu", 1100, 2),
    ("Lingdong-Barfok", 27.570, 88.480, "Dzongu", 900, 2),
    ("Hee-Gyathang", 27.520, 88.505, "Dzongu", 1300, 4),
    ("Lingzya", 27.640, 88.470, "Dzongu", 800, 2),
    ("Sakyong-Pentong", 27.600, 88.455, "Dzongu", 700, 1),
    # --- Gangtok district, down the Teesta ---
    ("Dikchu", 27.420, 88.520, "Dikchu", 3100, 4),
    ("Makha", 27.380, 88.500, "Dikchu", 1700, 4),
    ("Phodong", 27.410, 88.580, "Kabi", 2200, 1),
    ("Kabi", 27.400, 88.610, "Kabi", 1800, 1),
    ("Phensang", 27.435, 88.622, "Kabi", 1500, 1),
    ("Ranka", 27.340, 88.660, "Gangtok", 3400, 1),
    ("Gangtok-North", 27.352, 88.612, "Gangtok", 18000, 2),
    ("Rey-Mindu", 27.300, 88.590, "Gangtok", 2600, 1),
    ("Singtam", 27.235, 88.500, "Singtam", 6200, 3),
    ("Rangpo", 27.176, 88.530, "Rangpo", 4300, 3),
]


def _rivers() -> gpd.GeoDataFrame:
    lines = {
        "Teesta (main stem)": LineString([
            (88.22, 27.91), (88.40, 27.85), (88.55, 27.75), (88.644, 27.600),
            (88.61, 27.56), (88.55, 27.50), (88.52, 27.42), (88.50, 27.38),
            (88.50, 27.235), (88.53, 27.176),
        ]),
        "Lachen Chu": LineString([(88.555, 27.717), (88.60, 27.66), (88.644, 27.600)]),
        "Lachung Chu": LineString([(88.743, 27.691), (88.69, 27.64), (88.644, 27.600)]),
        "Dik Chu": LineString([(88.60, 27.45), (88.56, 27.435), (88.52, 27.42)]),
        "Zemu Chu": LineString([(88.30, 27.80), (88.40, 27.83), (88.55, 27.75)]),
    }
    return gpd.GeoDataFrame(
        {"name": list(lines), "kind": "river"}, geometry=list(lines.values()), crs=CRS_GEO
    )


def _faults() -> gpd.GeoDataFrame:
    lines = {
        "Tista lineament": LineString([(88.30, 28.05), (88.52, 27.70), (88.75, 27.30)]),
        "Gangtok fault splay": LineString([(88.45, 27.55), (88.62, 27.35), (88.72, 27.18)]),
    }
    return gpd.GeoDataFrame(
        {"name": list(lines), "slip_rate_mm_yr": [2.0, 1.2]},
        geometry=list(lines.values()), crs=CRS_GEO,
    )


def _glacial_lakes() -> gpd.GeoDataFrame:
    # name, lat, lon, area_2000_ha, area_2024_ha, dam_type, volume_mcm, breached_2023
    rows = [
        ("South Lhonak", 27.910, 88.210, 42.0, 167.0, "moraine", 65.0, True),
        ("Lhonak East", 27.930, 88.240, 8.0, 22.0, "moraine", 9.0, False),
        ("Shako Cho", 27.860, 88.300, 18.0, 34.0, "moraine", 12.0, False),
        ("Khangchung Cho", 27.880, 88.352, 10.0, 19.0, "moraine", 8.0, False),
        ("Zemu Upper", 27.800, 88.300, 5.0, 15.0, "ice", 6.0, False),
        ("Gurudongmar Complex", 28.020, 88.710, 30.0, 41.0, "bedrock", 20.0, False),
        ("Tso Lhamo", 28.000, 88.780, 55.0, 60.0, "bedrock", 40.0, False),
        ("Lachung Head", 27.832, 88.720, 4.0, 11.0, "moraine", 4.0, False),
    ]
    geoms, recs = [], []
    for name, lat, lon, a0, a1, dam, vol, breached in rows:
        r_deg = np.sqrt(a1 * 1e4 / np.pi) / 111_320  # circle of equal area, deg radius
        geoms.append(Point(lon, lat).buffer(r_deg, quad_segs=16))
        recs.append(dict(
            name=name, lat=lat, lon=lon, area_2000_ha=a0, area_2024_ha=a1,
            dam_type=dam, volume_mcm=vol, breached_2023=breached,
            growth_ratio=round(a1 / a0, 2),
        ))
    return gpd.GeoDataFrame(recs, geometry=geoms, crs=CRS_GEO)


def _destination_sites() -> gpd.GeoDataFrame:
    # name, lat, lon, spare_capacity, land_ha, servicing_cost_per_person, tier, access_road_km
    rows = [
        ("Bardang Relief Site", 27.552, 88.600, 1500, 12.0, 90_000, "yellow", 1.5),
        ("Mangan New Township Extn", 27.492, 88.520, 3000, 26.0, 55_000, "green", 0.8),
        ("Namok Terrace", 27.463, 88.585, 1200, 9.0, 80_000, "green", 2.1),
        ("Phodong Resettlement", 27.408, 88.575, 2500, 21.0, 50_000, "green", 1.0),
        ("Rangrang Bench", 27.447, 88.565, 900, 7.0, 85_000, "yellow", 2.6),
        ("Ranka Plateau", 27.345, 88.655, 2800, 24.0, 45_000, "green", 1.2),
        ("Singtam Peripheral", 27.252, 88.489, 4000, 30.0, 40_000, "green", 0.6),
        ("Rangpo Industrial Buffer", 27.190, 88.520, 3500, 28.0, 40_000, "green", 0.5),
    ]
    geoms = [Point(lon, lat) for _, lat, lon, *_ in rows]
    recs = [
        dict(site_id=f"DST-{i+1:02d}", name=n, lat=lat, lon=lon, spare_capacity=cap,
             land_available_ha=ha, servicing_cost_per_person=cost, hazard_tier=tier,
             access_road_km=rd)
        for i, (n, lat, lon, cap, ha, cost, tier, rd) in enumerate(rows)
    ]
    return gpd.GeoDataFrame(recs, geometry=geoms, crs=CRS_GEO)


def _voronoi_habitations(rivers: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = [Point(lon, lat) for _, lat, lon, *_ in _HABITATIONS]
    aoi = box(*AOI_BBOX)
    mp = gpd.GeoSeries(pts, crs=CRS_GEO).union_all()
    cells = list(voronoi_polygons(mp, extend_to=aoi.buffer(0.05)).geoms)

    # match each voronoi cell to the habitation point it contains
    recs, geoms = [], []
    rivers_m = rivers.to_crs(CRS_METRIC)
    river_union_m = unary_union(rivers_m.geometry.values)

    for (name, lat, lon, block, pop0, slides), pt in zip(_HABITATIONS, pts):
        cell = next((c for c in cells if c.contains(pt)), None)
        if cell is None:
            cell = min(cells, key=lambda c: c.distance(pt))
        cell = cell.intersection(aoi)
        if cell.is_empty or not isinstance(cell, (Polygon,)):
            cell = pt.buffer(0.02)
        geoms.append(cell)

        northness = (lat - 27.15) / (28.10 - 27.15)               # 0 south .. 1 far north
        dzongu = 1.0 if block == "Dzongu" else 0.0
        river_dist_km = Point(lon, lat).buffer(0)  # placeholder; computed below in metric CRS

        recs.append(dict(
            hab_id="", name=name, block=block, district="Mangan" if block in
            {"Chungthang", "Mangan", "Dzongu"} else "Gangtok",
            lat=lat, lon=lon, _northness=northness, _dzongu=dzongu,
            _pop0=pop0, landslide_incidents=slides,
        ))

    gdf = gpd.GeoDataFrame(recs, geometry=geoms, crs=CRS_GEO)
    gdf["hab_id"] = [f"SK-{i+1:03d}" for i in range(len(gdf))]

    # area + distance to nearest river, in metres
    gdf_m = gdf.to_crs(CRS_METRIC)
    gdf["area_sqkm"] = (gdf_m.area / 1e6).round(2)
    gdf["river_dist_km"] = (
        gdf_m.geometry.centroid.distance(river_union_m) / 1000.0
    ).round(2)
    return gdf


def _attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    n = len(gdf)
    north = gdf["_northness"].to_numpy()
    dz = gdf["_dzongu"].to_numpy()
    pop0 = gdf["_pop0"].to_numpy(dtype=float)
    rdist = gdf["river_dist_km"].to_numpy()

    def noise(scale):
        return RNG.normal(0.0, scale, n)

    pop = np.maximum(200, pop0 * (1 + noise(0.05))).round().astype(int)
    hh_size = 3.8 + 0.6 * north
    households = np.ceil(pop / hh_size).astype(int)

    forest_pct = np.clip(28 + 46 * north + noise(6), 5, 92).round(1)
    slope_gt30_pct = np.clip(32 + 34 * north + noise(7), 8, 95).round(1)
    rainfall_mm = np.clip(2100 + 1500 * (1 - north) + 400 * (rdist < 2) + noise(150), 900, 4200).round().astype(int)
    spring_lpm = np.clip(190 - 120 * north - 0.4 * (forest_pct < 30) * 50 + noise(25), 8, 260).round(1)
    lifeline_roads = np.where(north > 0.55, 1, np.where(north > 0.3, 2, 3)).astype(int)
    lifeline_roads = np.where(dz > 0, 1, lifeline_roads)

    isolation = np.clip(0.15 + 0.7 * north + 0.15 * dz + 0.1 * (rdist > 4) + noise(0.05), 0, 1).round(3)

    sc_pct = np.clip(4 + noise(1.5), 1, 12).round(1)
    st_pct = np.where(
        dz > 0, np.clip(80 + noise(6), 55, 96),
        np.clip(22 + 30 * north + noise(7), 8, 78),
    ).round(1)
    kutcha_pct = np.clip(9 + 30 * north + 10 * dz + noise(5), 3, 80).round(1)
    elderly_pct = np.clip(7 + 3 * north + noise(1.2), 3, 15).round(1)
    children_pct = np.clip(10 + 5 * north + noise(1.5), 6, 22).round(1)
    bpl_pct = np.clip(11 + 26 * north + 6 * dz + noise(4), 4, 70).round(1)
    literacy_pct = np.clip(86 - 20 * north - 4 * dz + noise(3), 45, 96).round(1)

    hospital_beds = np.where(
        pop > 5000, RNG.integers(20, 120, n),
        np.where(pop > 2500, RNG.integers(4, 20, n), RNG.integers(0, 6, n)),
    )
    school_seats = np.maximum(
        0, (pop * (0.20 - 0.06 * north) + noise(60)),
    ).round().astype(int)

    out = gdf.drop(columns=["_northness", "_dzongu", "_pop0"]).copy()
    out = out.assign(
        population=pop, households=households,
        forest_pct=forest_pct, slope_gt30_pct=slope_gt30_pct,
        annual_rainfall_mm=rainfall_mm, spring_discharge_lpm=spring_lpm,
        lifeline_road_count=lifeline_roads, isolation_index=isolation,
        sc_pct=sc_pct, st_pct=st_pct, kutcha_pct=kutcha_pct,
        elderly_pct=elderly_pct, children_pct=children_pct, bpl_pct=bpl_pct,
        literacy_pct=literacy_pct, hospital_beds=hospital_beds, school_seats=school_seats,
    )
    return out


def _historical_losses() -> gpd.GeoDataFrame:
    # (type, year, lat, lon, deaths, houses_damaged)
    rows = [
        # 2023 South Lhonak GLOF — down the Teesta
        ("glof", 2023, 27.598, 88.646, 12, 210),
        ("glof", 2023, 27.505, 88.536, 8, 160),
        ("glof", 2023, 27.420, 88.520, 6, 140),
        ("glof", 2023, 27.236, 88.500, 9, 190),
        ("glof", 2023, 27.178, 88.531, 7, 150),
        ("glof", 2023, 27.383, 88.500, 3, 70),
        # 2011 Sikkim earthquake — North cluster
        ("earthquake", 2011, 27.508, 88.536, 6, 240),
        ("earthquake", 2011, 27.601, 88.645, 5, 180),
        ("earthquake", 2011, 27.546, 88.560, 3, 120),
        ("earthquake", 2011, 27.352, 88.612, 4, 300),
        ("earthquake", 2011, 27.470, 88.520, 2, 90),
        # Monsoon landslides along NH-10 / corridor (spread across years)
        ("landslide", 2016, 27.600, 88.644, 4, 45),
        ("landslide", 2019, 27.507, 88.535, 3, 30),
        ("landslide", 2020, 27.235, 88.500, 5, 60),
        ("landslide", 2021, 27.176, 88.530, 2, 25),
        ("landslide", 2022, 27.420, 88.520, 3, 38),
        ("landslide", 2023, 27.520, 88.505, 4, 52),
        ("landslide", 2024, 27.380, 88.500, 3, 41),
        ("landslide", 2015, 27.717, 88.555, 2, 18),
        # Flash floods near confluences
        ("flood", 2017, 27.600, 88.644, 2, 34),
        ("flood", 2018, 27.420, 88.520, 1, 22),
        ("flood", 2023, 27.235, 88.500, 2, 40),
        ("flood", 2016, 27.691, 88.743, 1, 15),
    ]
    geoms = [Point(lon, lat) for _, _, lat, lon, *_ in rows]
    recs = [
        dict(event_id=f"EVT-{i+1:03d}", hazard_type=t, year=y, lat=lat, lon=lon,
             deaths=d, houses_damaged=h)
        for i, (t, y, lat, lon, d, h) in enumerate(rows)
    ]
    return gpd.GeoDataFrame(recs, geometry=geoms, crs=CRS_GEO)


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    rivers = _rivers()
    faults = _faults()
    lakes = _glacial_lakes()
    dests = _destination_sites()
    losses = _historical_losses()
    habs = _attributes(_voronoi_habitations(rivers))

    for name, gdf in {
        "rivers": rivers, "faults": faults, "glacial_lakes": lakes,
        "destination_sites": dests, "historical_losses": losses, "habitations": habs,
    }.items():
        path = INTERIM_DIR / f"{name}.parquet"
        gdf.to_parquet(path)
        print(f"  wrote {path.relative_to(INTERIM_DIR.parent.parent)}  ({len(gdf)} features)")

    print(
        f"\nSeed complete: {len(habs)} habitations, pop {habs.population.sum():,}, "
        f"{len(lakes)} glacial lakes, {len(dests)} destination sites "
        f"(spare capacity {dests.spare_capacity.sum():,}), {len(losses)} historical events."
    )


if __name__ == "__main__":
    main()
