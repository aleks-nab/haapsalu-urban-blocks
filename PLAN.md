# Haapsalu urban blocks and building data quality

Research plan · draft 2 · Aleksandra Nabiulina · 2026-10-30

Self-study project based on Practice 2 of the course *AI Technologies in Urbanism*
(ITMO), done with an AI coding agent (Claude Code), extended with a comparison of
open and official building data for Estonia.

## Why Haapsalu

A small coastal town (about 9 000 residents) on the Läänemaa coast. The sea and
the bays shape the town: they cut the street network, limit where blocks can be,
and create long distances between parts of town that look close on a map. That
makes it a good case for block-based metrics and accessibility.

Note: the Haapsalu railway closed to passenger traffic in the 1990s, so the railway
layer may be empty or contain only the historic line. This is stated, not hidden.

## Research questions

1. **City blocks and metrics (course task).** What do Haapsalu's city blocks look
   like by land use, building density, building type (Spacematrix) and estimated
   population? How well are blocks served by schools, and how long does it take to
   reach them?
2. **Building data quality (my extension).** What is lost or outdated when official
   building data is carried into OpenStreetMap: missing and extra buildings, floors, purpose.
   OSM is not an independent source here (see "OSM and official data are not independent"
   below). Sub-questions:
   - footprint: which buildings are missing in OSM, which exist only in OSM (118 official
     buildings have no OSM pair and 295 OSM buildings have no official pair, by the rule
     "overlap above 50 % of the smaller area");
   - number of floors: OSM has it for 3.6 % of buildings against 75.7 % in the official
     data, and how often the values match;
   - purpose: how the OSM `building` tag compares with the official use (`kaos_nimetus`);
   - missing floors as a finding: how many buildings lack floors in OSM, in EHR,
     and in both;
   - effect: how much do the population and density estimates change if official
     floors are used instead of OSM floors?
   - two ways to estimate population: footprint × floors (BlocksNet default) versus
     the EHR net floor area (`suletud_netopind`) of residential buildings.
3. **Towards 3D cadastre (discussion).** What would be needed to go from floors to
   heights and volumes, and what the gaps found in question 2 mean for that.

## Data (each recorded with source, download date and licence)

Status: **checked** = the source was read or the data downloaded on 2026-10-30;
**assumed** = not verified yet, to be checked before use. Exact URLs, licences, dates and
feature counts are in `data/SOURCES.md`.

| Topic | Source | Used for | Status |
| --- | --- | --- | --- |
| Town boundary | Maa- ja Ruumiamet, EHAK administrative and settlement division, layer "Asustusüksused", unit **Haapsalu linn** (the settlement, not the municipality, which since 2017 also includes the former Ridala vald). SHP, updated monthly, open data (same Maa- ja Ruumiamet licence, see `data/SOURCES.md`). | study area | checked: EHAK code 1692, 11.0 km², follows the coastline |
| Official buildings: footprints, floors, height, areas, use | Maa- ja Ruumiamet WFS `https://gsavalik.envir.ee/geoserver/etak_tuletis/wfs`, layer `etak_tuletis:etak_ehr_hooned` (ETAK buildings enriched with Building Register EHR data), requested for Haapsalu only. Fields include `max_korruste_arv`, `min_korruste_arv`, `korgus`, `ehitisalune_pind`, `suletud_netopind`, `kaos_nimetus`, `esmane_kasutus`, `ehr_gid`. Updated daily. Licence: Maa- ja Ruumiamet opendata licence 01.01.2025 (own licence text, https://geoportaal.maaruum.ee/opendata-licence; quoted in `data/SOURCES.md`). | Q2, Q3 | checked: 3 941 buildings in town, 2 984 linked to EHR, 2 982 with floors |
| Roads, water, land use, buildings, schools | OpenStreetMap (via osmnx, as in BlocksNet `examples/pipeline.ipynb`) | blocks, metrics (course task), Q2 | checked (method) |
| Living area per person | Statistics Estonia, census 2021: RL21218 total area of occupied conventional dwellings / RL21003 population, Haapsalu linn = **29.9 m²** (total useful floor area, same concept as the 30.1 m² for Estonia on the census page "Housing arrangements") | population estimate (model parameter) | checked |
| Official population of Haapsalu town | Statistics Estonia, census 2021, RL21003, settlement Haapsalu linn: **9 595** (31.12.2021) | check of the model and the building data | checked |
| Population grid | Statistics Estonia, census 2021 grid | optional block-level check | assumed |
| School capacity | EHIS open data: service `opilastearvud` (students per school, 01.10.2026) and `hooned` (school buildings with coordinates). No design capacity is published, so students are used as capacity. | school capacity instead of the BlocksNet estimate | checked |
| School-age children (7–18) | Statistics Estonia, census 2021, RL21003, Haapsalu linn: **1 188** | school demand instead of the BlocksNet norm | checked |
| 3D building models | Maa- ja Ruumiamet 3D building models | Q3 | assumed (old page not found); the `korgus` field above may be enough |
| Travel graph | **walking** graph built by BlocksNet / IduEdu from OSM | accessibility, school provision | checked (function exists in BlocksNet 1.0.0a9) |

Known data issues (from press and studies, checked): parts of the EHR are hidden from
the public, and one building can have several EHR records.

**OSM and official data are not independent (checked on 2026-10-31).** 3 459 of the 3 885
OSM buildings carry the tag `maaamet:ETAK`, and 3 391 of these values are the `etak_id` of an
official building. All 3 046 OSM buildings with a `height` tag have it. The OSM height equals
the official `korgus_m` exactly in 2 988 of 3 002 matched pairs; 14 pairs differ by more than
1 m (largest difference 10 m). There is no `source:height` or `source:geometry` tag, so the
origin of the heights is not stated in OSM. Conclusion for Q2: OSM cannot be used as an
independent check of the official data; the comparison shows what is lost or outdated on the
way into OSM.

## Method decisions

- **Living area per person comes from official statistics, not from tuning: 29.9 m²**
  for Haapsalu linn (census 2021, RL21218 / RL21003). The census defines dwelling area in
  two ways: the total useful floor area inside the outer walls, or the floor area of rooms
  only. The 30.1 m² for Estonia ("Housing arrangements" page) is the total useful floor
  area: it equals the RL21218 total (38.97 million m²) divided by the residents. RL21807
  (23.5 m² Estonia, 22.7 m² Haapsalu linn) is about 78 % of that, which fits rooms only
  (inferred, the table has no footnote). BlocksNet uses footprint × floors, a gross floor
  area, so the total useful floor area is the closer concept. The value is slightly low
  because people in institutions are in the denominator (same method gives 29.3 m² for
  Estonia against the published 30.1 m²). The BlocksNet defaults (20 m² and 30 m²) are not used.
- **Limitation: gross versus usable floor area.** BlocksNet computes floor area as
  footprint × floors, a *gross* floor area (walls, staircases, corridors, non-residential
  floors). The 29.9 m² per person is a *usable* floor area of dwellings and is smaller.
  Dividing a gross area by a usable-area norm overestimates the population, so the
  estimate is expected to be higher than the official 9 595. This is reported as a
  limitation; nothing is tuned to match 9 595.
- **One check, not calibration.** The estimated population is compared once with the
  official population of Haapsalu linn. The difference is reported as a check of the
  model and of the building data; the parameter is not changed to make them match.
- **Second population estimate** from the EHR net floor area (`suletud_netopind`) of
  residential buildings, compared with the footprint × floors approach.
- **Floors for calculations** (columns in `official_buildings.geojson`): `footprint_m2` is
  the area of the geometry in EPSG:3301 (not the register field `ehitisalune_pind`);
  `floors` is `max_korruste_arv`, else `round(korgus_m / 3)` with a minimum of 1, else 1;
  `floors_source` is `registry` (2 982 buildings), `height_3m` (879) or `default_1` (80).
  3 m per floor is a conventional assumption, not a norm. Floors that do not come from the
  registry are used for density only, not for the population estimate.
- **Dwellings for the population estimate** are chosen by the official use `kaos_nimetus`,
  not by a substring, and stored in the column `is_dwelling` of `official_buildings.geojson`.
  Five uses count as dwellings: `Üksikelamu`, `Muu kolme või enama korteriga elamu`,
  `Ridaelamu või kaksikelamu sektsioon (juhul kui on oma katus ja sissepääs maapinnalt)`,
  `Kahe korteriga elamu`, `Ridaelamu`. Repeated entries in the text are collapsed first.
  - **Mixed uses:** a building is a dwelling if at least one of its uses is one of the five;
    its whole area counts as dwelling area. *Limitation:* this overestimates the population
    in houses with shops or offices.
  - **Cut texts:** `kaos_nimetus` is cut at 500 characters (77 buildings). If the last use of
    such a text is a fragment of exactly one known full use, it is read as that use, for the
    classification only (75 buildings; 2 ambiguous fragments are left as they are). The
    values in the data are not changed.
  - **Not counted (limitation):** hotels, a sanatorium and garden or holiday houses are not
    permanent housing. A children's home and a care home (6 buildings) are not counted
    either, although people live there. `Elamu, kooli vms abihoone` (779 buildings) is an
    outbuilding, not housing.
  - Result: 1 757 dwelling buildings (1 521 with a single dwelling use, 236 mixed or with a
    cut text), all with floors from the registry.
- **First population check for the whole town** (no fitting, only a check; per-block method
  is chosen later; `data/population_check_city.json`): with 29.9 m² per person, the sum of
  `footprint_m2 × floors` of the dwellings (723 250 m²) gives 24 189 people, 2.52 times the
  official 9 595; the sum of the registry `suletud_netopind` (495 762 m²) gives 16 581 people,
  1.73 times. Both are expected to be too high: footprint × floors is a gross area, the 29.9 m²
  is a usable area per person from occupied dwellings, and the building areas include vacant
  dwellings (census: 91 362 m² of 377 891 m² of dwelling area in Haapsalu linn is vacant),
  common areas and the non-dwelling parts of mixed buildings.
- **Missing floors are a finding.** Report how many buildings lack floors in OSM, in EHR,
  and in both, and what default BlocksNet uses then (1 floor).
- **School provision uses Estonian data, not the BlocksNet norms.** The BlocksNet norms
  (120 places per 1 000 residents, 15 minutes) come from Russian standards. Instead:
  - capacity: actual capacity or number of students per school from EHIS;
  - demand: number of children aged 7–18 from Statistics Estonia, spread over blocks
    in proportion to the estimated population.
  The BlocksNet norm is a fallback only, used for a part where Estonian data cannot be
  found; the README then says which part and why. The 15-minute walking limit has no
  Estonian source yet, so it is kept as a fallback and marked as such.
- **Schools used:** only general-education schools whose main building is inside
  Haapsalu linn (5 schools, 1 281 students). Excluded: Haapsalu Kutsehariduskeskus
  (vocational), Uuemõisa Lasteaed-Algkool (Uuemõisa alevik, just east of the town boundary)
  and Ridala Põhikool (Panga küla, about 13 km south). The OSM duplicate of Haapsalu
  Põhikool is removed.
- **Railway:** the Haapsalu line is closed. OSM still has 4 segments tagged `railway=rail`
  (about 2.4 km); they are saved but **not used for block cutting**.
- **Buildings** (OSM and official) are kept whole if their inside point lies in the town,
  not cut at the boundary, so footprint areas stay correct.
- **Roads for cutting:** the BlocksNet road types plus `highway=service` (yard and access
  roads; the BlocksNet list misses almost all of them). **Not used:** `footway`, `path`,
  `cycleway`, `steps` (they would cut the town into narrow strips). Dead-end streets are not
  extended to the next road and land-use outlines are not used for cutting (both were tested
  and rejected for now).
- **Islands without buildings** are not city blocks: a block with no buildings that is
  further than 20 m from every road line is dropped and saved to
  `data/blocks_dropped_islands.geojson`; it is not counted in block statistics. There is no
  area limit in this rule (an earlier 1 ha limit let one 1.2 ha island stay).
- **Slivers:** a block with no buildings and area below 500 m² (typically a strip between
  roads) is dropped and saved to `data/blocks_dropped_slivers.geojson`. The islands rule is
  applied first, then the slivers rule.
- **Undeveloped blocks** (forest, fields) with at least 500 m² are kept and marked
  `built_up = False`, so that averages and the dashboard can show built-up blocks
  separately. A block is built up if it has at least one building in the official or the
  OSM layer; no threshold on building share is used.
- **Large blocks:** a block over 1 km² gets `large_block = True`. The threshold is final:
  the two largest blocks are 3.76 and 1.31 km², the next one is only 0.39 km², and any
  threshold from 0.4 to 1.3 km² selects the same two blocks (2 and 172). Such blocks are
  kept, and averages and the dashboard can show them separately. The blocks also have `building_share` (footprint of
  the official buildings / block area) to show how empty they are.
- **BlocksClassifier is not used:** in a separate trial the model labelled 213 of 216 blocks
  `INVALID` and cut nothing.
- **Known limitation, shoreline strip:** block 2 (3.76 km²) contains the empty south-eastern
  area and also a thin strip along the shore, because the street network does not separate
  them. The strip is left as it is; the block is covered by `large_block = True`.

## Steps

1. **Set-up.** Project folder, Python 3.12 environment, BlocksNet, empty GitHub repository.
2. **Boundary.** EHAK "Asustusüksused", Haapsalu linn. Check it on a map.
3. **Data.** Download the layers above (official buildings via WFS for the boundary only), record source and date, save as GeoJSON. Verify the "assumed" sources.
4. **Blocks.** Build city blocks with BlocksNet (roads incl. `highway=service`, and water; no railway). Drop islands and slivers without buildings (separate files); mark undeveloped blocks (`built_up`) and large blocks (`large_block`). **Stop and check the blocks on a map** before any metrics.
5. **Metrics.** Land use shares, density, Spacematrix, population estimate (official census 2021 living area per person; one comparison with the official population as a check), schools (EHIS capacity, children aged 7–18; BlocksNet norm only as a stated fallback), walking accessibility, as in BlocksNet `examples/pipeline.ipynb`.
6. **Building comparison (Q2).** Match OSM and official buildings, count missing ones, compare floors, count buildings without floors in OSM / EHR / both; recompute population and density with official floors; compare with the EHR net floor area estimate.
7. **Dashboard.** One `dashboard.html`: map of blocks, charts and tables, plus a page section for the OSM vs official comparison.
8. **Checks.** A table "metric — notebook — dashboard" to prove the numbers match; a re-run instruction.
9. **Publish.** GitHub repository with README, plan, notebook, GeoJSON, script, dashboard; a short LinkedIn post.

## Outputs

- `notebook.ipynb` — code, maps, explanations
- `data/*.geojson` — inputs and results
- `build_dashboard.py` — builds the page from saved results
- `dashboard.html` — interactive map and dashboard
- `README.md` — what, why, how to re-run, findings, data sources and licences

## Working rules (safety)

- Everything lives in one project folder; the agent works only there.
- The agent asks before every command; nothing is approved "for all".
- No downloads of programs, only data files and Python packages from PyPI.
- The project is pushed to GitHub regularly, so nothing important exists in one place only.
- Everything in English.
