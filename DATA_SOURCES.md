# Data source registry — Sikkim (Mangan DDMA / Teesta corridor)

The pipeline currently runs on a **synthetic seed** (`redzone/seed/generate_sikkim.py`) that
mimics the *structure and format* of the real layers below. Each real layer is swapped in via
an adapter in `redzone/data/adapters/` that writes the same GeoParquet schema into
`data/interim/`; nothing downstream changes.

| Layer | Real source | Level | Access | Licence | Adapter |
|---|---|---|---|---|---|
| Admin boundaries (GPU / village) | LGD codes + Census 2011 village boundaries (SOI / DataMeet) | GPU / village | download | open (Census), CC-BY (DataMeet) | `census.py` |
| Population, house condition, amenities | Census 2011 (village directory, HH-06 house condition) | village | censusindia.gov.in | open | `census.py` |
| Deprivation (SC/ST %, BPL, kutcha, literacy) | SECC 2011 | GP / block | secc.gov.in | open aggregate | `secc.py` |
| Current built-up / population | Google Open Buildings v3, WorldPop, Meta HRSL | 100 m raster / polygons | download | CC-BY-4.0 / open | `builtup.py` |
| Landslide susceptibility | GSI Bhukosh — National Landslide Susceptibility Mapping (1:50k) | 1:50k | bhukosh.gsi.gov.in | open (registration) | `gsi_landslide.py` |
| Rainfall (daily / normals) | IMD gridded rainfall (0.25°), CWC | grid / gauge | imdpune.gov.in, cwc.gov.in | open | `imd_rainfall.py` |
| Seismic zonation | BIS IS 1893:2016 (Zone IV) + SOI/GSI fault traces | polygon / line | BIS, GSI | reference | `bis_seismic.py` |
| Glacial lakes (inventory + area) | NRSC/ISRO Bhuvan glacial-lake atlas, ICIMOD HKH inventory | polygon | bhuvan.nrsc.gov.in, rds.icimod.org | open (registration) | `glacial_lakes.py` |
| Glacial-lake area change | Sentinel-2 / Landsat NDWI change detection (2000→now) | raster → polygon | Copernicus / USGS | open | `glacial_lakes.py` |
| River network / DEM / slope | Cartosat / ALOS PALSAR / SRTM 30 m DEM; NRSC drainage | raster / line | bhoonidhi.nrsc.gov.in, ASF | open | `terrain.py` |
| Springs (discharge, drying) | Dhara Vikas spring atlas — Sikkim RM&DD | point | sikkimsprings.org / RM&DD | request | `springs.py` |
| Forest cover | FSI State of Forest Report; Sikkim FEWMD | raster / district | fsi.nic.in | open | `forest.py` |
| Roads (lifeline, capacity) | OSM + PWD/BRO road inventory; IRC capacity classes | line | OSM / state PWD | ODbL | `roads.py` |
| Health facilities & beds | IPHS facility registry / HMIS; RHS | point | nrhm-mis.nic.in | open | `services.py` |
| Schools & seats | UDISE+ | point | udiseplus.gov.in | open | `services.py` |
| Historical disaster loss (calibration) | SSDMA situation reports; DesInventar India; EM-DAT; 2011 EQ macroseismic surveys; 2023 GLOF post-event studies | event points | ssdma.nic.in, desinventar.net | open / request | `losses.py` |
| Coastal (cyclone / surge / erosion) | **N/A — Sikkim is landlocked.** Framework covers all six hazards; validate coastal modules on a coastal district if time allows. | — | — | — | — |

## Acquisition priority (for the "hybrid" path)

1. **Fast, high value:** BIS seismic zones, SRTM/Cartosat DEM → slope, Census 2011 village boundaries + population, OSM roads.
2. **Medium:** GSI Bhukosh landslide susceptibility, IMD rainfall normals, NRSC/ICIMOD glacial-lake inventory, FSI forest.
3. **Slow / request:** SECC deprivation at GP level, Dhara Vikas spring data, SSDMA loss records, UDISE+/HMIS facility capacity.

Keep any manually downloaded raw file under `backend/data/raw/<source>/` and record the URL,
date and licence in that folder's `SOURCE.txt`.
