# Licences of the files in `data/`

This is a self-study project. This file lists, for every file in `data/`, the sources it is built on and the terms
of those sources. It is not a legal assessment. The code (`notebook.ipynb`, `build_dashboard.py`) is under the MIT
licence, see `LICENSE` in the root of the repository; it does not apply to the data. Sources, URLs, download dates and
quotations of the terms are in [SOURCES.md](SOURCES.md). `data/raw/` (raw downloads) is not in the repository.

## Terms and official texts

| Short name | Terms | Official text |
| --- | --- | --- |
| OSM / ODbL 1.0 | OpenStreetMap data, Open Data Commons Open Database License 1.0 | https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/ |
| Maa- ja Ruumiamet opendata licence | Republic of Estonia Land and Spatial Development Board opendata licence 01.01.2025 (EHAK boundary, ETAK buildings with EHR data, In-ADS address service) | https://geoportaal.maaruum.ee/opendata-licence |
| CC BY 4.0 | Cadastre WFS `kataster:ky_kehtiv`, attributed to the Ministry of Economic Affairs and Communications | https://creativecommons.org/licenses/by/4.0/legalcode |
| CC BY-SA 4.0 | Statistics Estonia open data (census 2021) | https://creativecommons.org/licenses/by-sa/4.0/legalcode.en |
| CC BY-SA 3.0 | EHIS school buildings (licence field `CC_BY_SA_3.0` of the open data portal record) | https://creativecommons.org/licenses/by-sa/3.0/legalcode |
| not stated | EHIS student numbers (no licence stated for the data on the pages checked) | see [SOURCES.md](SOURCES.md) |

## Files

Files marked with ★ are built on OpenStreetMap data; see the statement below the table.

| File | Built on | Terms |
| --- | --- | --- |
| `osm_buildings.geojson` ★ | OSM buildings | OSM / ODbL 1.0 |
| `osm_landuse.geojson` ★ | OSM land use | OSM / ODbL 1.0 |
| `osm_railways.geojson` ★ | OSM railways | OSM / ODbL 1.0 |
| `osm_roads.geojson` ★ | OSM roads | OSM / ODbL 1.0 |
| `osm_schools.geojson` ★ | OSM schools | OSM / ODbL 1.0 |
| `osm_water.geojson` ★ | OSM water | OSM / ODbL 1.0 |
| `blocks.geojson` ★ | OSM roads, water and buildings; official buildings; cadastral parcels; census 2021; EHIS school buildings and student numbers | OSM / ODbL 1.0; Maa- ja Ruumiamet opendata licence; CC BY 4.0; CC BY-SA 4.0; CC BY-SA 3.0; not stated |
| `blocks_dropped_islands.geojson` ★ | OSM roads and water; OSM and official buildings | OSM / ODbL 1.0; Maa- ja Ruumiamet opendata licence |
| `blocks_dropped_slivers.geojson` ★ | OSM roads and water; OSM and official buildings | OSM / ODbL 1.0; Maa- ja Ruumiamet opendata licence |
| `accessibility_matrix.parquet` ★ | OSM walking network; blocks (OSM) | OSM / ODbL 1.0 |
| `q2_unmatched_buildings.geojson` ★ | OSM buildings; official buildings | OSM / ODbL 1.0; Maa- ja Ruumiamet opendata licence |
| `notebook_numbers.json` ★ | numbers calculated from the files above | OSM / ODbL 1.0; Maa- ja Ruumiamet opendata licence; CC BY 4.0; CC BY-SA 4.0; CC BY-SA 3.0; not stated |
| `boundary.geojson` | EHAK settlement boundary | Maa- ja Ruumiamet opendata licence |
| `official_buildings.geojson` | ETAK buildings with EHR data (added columns calculated) | Maa- ja Ruumiamet opendata licence |
| `purposes_single.csv`, `purposes_mixed.csv` | official buildings (use of the buildings) | Maa- ja Ruumiamet opendata licence |
| `cadastre_parcels.geojson` | cadastre WFS `kataster:ky_kehtiv` | CC BY 4.0 |
| `statistics.json` | Statistics Estonia, census 2021 (RL21003, RL21218, RL21807) | CC BY-SA 4.0 |
| `population_check_city.json` | census 2021; official buildings | CC BY-SA 4.0; Maa- ja Ruumiamet opendata licence |
| `ehis_schools.csv`, `schools.geojson` | EHIS school buildings and student numbers; In-ADS geocoding of one address | CC BY-SA 3.0; not stated; Maa- ja Ruumiamet opendata licence |
| `download_dates.json` | dates only, no third-party content | not applicable |
| `SOURCES.md`, `LICENSE.md` | documentation; `SOURCES.md` quotes the terms of the sources | see the quoted terms |
| `check_map.png`, `blocks_check.png`, `density_check.png`, `land_use_check.png`, `accessibility_check.png`, `schools_check.png`, `q2_check.png`, `classifier_probe_blocks_2_122.png`, `classifier_probe_town.png`, `diagnostic_blocks_2_122.png` | maps (images) drawn from the layers above: OSM roads, water, buildings; official buildings; blocks. Credit: © OpenStreetMap contributors; Maa- ja Ruumiamet | sources as above |

## Statement for the files marked ★

This derived database is made available under the ODbL 1.0.

Licence: https://opendatacommons.org/licenses/odbl/1-0/. Source and attribution: © OpenStreetMap contributors,
https://www.openstreetmap.org/copyright.

Other sources in the same files keep their own terms, as listed in the table. References required by the
Maa- ja Ruumiamet opendata licence are in the README.

## Not verified

- Whether derivatives of ODbL data and of CC BY-SA 4.0 data can be mixed in one file. The official list of Creative
  Commons (https://creativecommons.org/share-your-work/licensing-considerations/compatible-licenses/) names Free Art
  License 1.3 and GPLv3 for BY-SA 4.0 and does not name ODbL. What the OSM side (OSMF) says about it was not looked up.
- Whether `blocks.geojson` is a "Derivative Database" under the ODbL or a "Produced Work". The boundary depends on the
  meaning of "Substantial" in the definitions of the ODbL; no assessment is given here.
- Whether `dashboard.html` with the embedded data is a derivative database or a map ("Produced Work").
- The licence of the student numbers in EHIS (not stated).
- Compatibility of the Maa- ja Ruumiamet opendata licence with ODbL and CC BY-SA.
