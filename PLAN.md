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
| Cadastral parcels (land-use purpose) | Maa- ja Ruumiamet WFS `https://gsavalik.envir.ee/geoserver/kataster/wfs`, layer `kataster:ky_kehtiv`, fields `siht1`–`siht3`, `so_prts1`–`so_prts3`. Updated daily. Licence: CC BY 4.0 as stated in the service `GetCapabilities` (quoted in `data/SOURCES.md`). | land use of the blocks | checked: 2 663 parcels, 98.8 % of the town |
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
  - **How much the mixed rule matters** (236 dwellings that are mixed or have a cut text,
    45.9 % of the dwelling net floor area, 227 707 m²): (a) 42 buildings are a single dwelling
    use after the cut tail is restored, 111 048 m²; (b) 129 buildings are dwelling plus only
    `Elamu, kooli vms abihoone`, 83 134 m²; (c) 56 buildings are dwelling plus another non-dwelling
    use (shop, office, cafe, hotel), 31 998 m²; (d) 9 buildings combine several dwelling uses,
    1 527 m². Only group (c) really mixes housing with something else (6.5 % of the area).
- **Population per block (dasymetric distribution, not a fit).** The population of the town is
  taken from the census: 9 595 (RL21003, census 2021). It is only distributed over the blocks:
  `population_block = 9 595 × (sum of suletud_netopind of the dwellings in the block) / (sum of
  suletud_netopind of all dwellings of the town)`. The sum over the blocks is 9 595. 29.9 m² per
  person is not changed or used here. A dwelling is assigned to the block that contains its
  inside point. One dwelling has an empty `suletud_netopind` (`etak_id` 205592, `ehr_gid`
  105002892, detached house, 114 m² footprint, 2 registry floors); it is not filled, so it adds
  nothing to its block. The columns `n_dwellings`, `dwelling_net_area_m2` and `population_block`
  are in `blocks.geojson`.
- **Finding for the README: building-only estimate overestimates the population** (check with
  29.9 m² per person, `data/population_check_city.json`; no fitting): the sum of `footprint_m2 ×
  floors` of the dwellings (723 250 m²) gives 24 189 people, 2.52 times the official 9 595; the
  sum of the registry `suletud_netopind` (495 762 m²) gives 16 581 people, 1.73 times. A known
  reason: 24 % of the dwelling floor area is vacant (RL21218: 91 362 of 377 891 m² in Haapsalu
  linn); alone this explains a factor of about 1.32. The rest is not separated; candidates are
  common areas and the non-dwelling parts of mixed buildings. The 29.9 m² is a usable area per
  person from occupied dwellings, while footprint × floors is a gross area.
- **Finding: footprint and register building area.** The median of `footprint_m2 /
  ehitisalune_pind` for the dwellings is 1.19 (1 749 dwellings with a positive
  `ehitisalune_pind`). The reason is not established. An assumption, not checked: the
  geometry is the outline of the roof and the register area is measured at the walls.
- **Density indicators of the blocks** (`gsi`, `fsi`, `l`, `osr`, `share_floors_estimated`, columns of
  `blocks.geojson`) come from `blocksnet.analysis.indicators.calculate_density_indicators` and use
  all official buildings, with floors of all sources. They equal the plain formulas
  (`fsi` = sum of footprint × floors / area, `gsi` = sum of footprint / area, `l` = `fsi / gsi`,
  `osr` = (1 − `gsi`) / `fsi`); BlocksNet only adds clips that never apply here (`gsi` to 0–1, `l`
  not below 1) and gives NaN or infinity where there are no buildings, which we leave empty (81
  blocks). Buildings belong to the block that contains their inside point, footprints are not cut.
- **MXI and morphotypes (BlocksNet; columns `mxi`, `morphotype_spacematrix`, `spacematrix_cluster`,
  `morphotype_strelka` of `blocks.geojson`).** `mxi` = `living_area / build_floor_area`
  (`calculate_density_indicators`) with `living_area` = sum of `footprint_m2 x floors` of the official buildings with
  `is_dwelling = True` and `build_floor_area` = the same sum over all official buildings (gross floor area on both
  sides). Town: 723 250 of 1 328 477 m2 = 0.544; the 216 blocks with buildings: median 0.70. Morphotypes from
  `blocksnet.analysis.morphotypes`, only for blocks with `fsi > 0`; the 81 blocks without buildings are `not defined`
  (and `mxi` is empty). Results: Spacematrix 7 names for 11 clusters, Strelka 5 types (no high-rise: the largest
  `l` is 5.0). Limitations:
  - **The building counts as dwelling as a whole**: a shop on the ground floor of a dwelling building does not lower
    `mxi`, so mixed use inside a building is not seen.
  - **Sheds and garages count as non-living**: they lower `mxi` of blocks with houses.
  - **The thresholds of Strelka and the names of the Spacematrix clusters come from the BlocksNet code, not from our
    norms.** The number of clusters (11), KMeans, `random_state = 42` and scikit-learn 1.9.1 are the BlocksNet
    defaults and the installed version; another version may give other clusters.
  - **Different Spacematrix clusters can have the same name** (for example three clusters are "low-rise low-density
    residential"); this is a feature of the method (the name comes from the cluster medians), and the dashboard
    labels it on the chart.
- **Blocks with OSM buildings only** (`built_up = True` but `gsi = 0`, one OSM building each, no
  official building): block_id 11, 29, 62, 86, 144, 293. They go into the Q2 comparison (OSM
  buildings without an official pair).
- **Land use of the blocks: cadastral purpose.** The main source is the Maa- ja Ruumiamet cadastre,
  WFS layer `kataster:ky_kehtiv` (`hkood = '1692'`, 2 663 parcels clipped to the town, `data/cadastre_parcels.geojson`),
  without OSM `landuse`. The purpose is the **cadastral land-use purpose (legal), not actual use**. BlocksNet
  `assign_land_use` takes the class with the largest share of the block area (`land_use`, `share`, and the
  shares of all classes in `share_<class>`; there is no minimum share). Mapping of `siht1` to BlocksNet:
  `ELAMUMAA` → RESIDENTIAL; `ARIMAA` → BUSINESS; `UHISKONDLIKE_EHITISTE_MAA` → BUSINESS; `TOOTMISMAA` →
  INDUSTRIAL; `TRANSPORDIMAA` → TRANSPORT; `ULDKASUTATAV_MAA`, `KAITSEALUNE_MAA` → RECREATION;
  `RIIGIKAITSEMAA` → SPECIAL; `VEEKOGUDE_MAA` and `SIHTOTSTARBETA_MAA` have no class (not in the rules).
  - **Limitations.** BlocksNet has no class for public buildings: in the rules of its `pipeline.ipynb` there
    is no rule for schools, hospitals or education; the only public-function rule is `'religious':
    LandUse.SPECIAL`, so the parcels of public buildings go to BUSINESS. A parcel with several purposes
    counts with the purpose of the largest share (`so_prts`; in all 84 such parcels `siht1` already has the
    largest share, 16 of them tie with another purpose and `siht1` is taken). `ULDKASUTATAV_MAA` (public-use
    land, 56 % of the parcel area, mostly forest and large green areas) is RECREATION as a whole. A block
    gets the class with the largest share even if that share is small (30 blocks have `share < 0.5`).
  - **Display class.** `blocks.geojson` has `land_use_display`: equal to `land_use`, but `mixed` where
    `share < 0.5` (30 blocks). The column `land_use` of BlocksNet is not changed. **The dashboard uses
    `land_use_display`.** The threshold 0.5 is our decision; BlocksNet has no threshold.
  - **Finding: population and land use class.** 1 871 of the 9 595 inhabitants (19.5 %) live in blocks whose
    class is not residential; 1 059 of them live in the large blocks 2 and 172 (class recreation), where
    the dwellings are a small built-up part of a very large block. 13 blocks with the class residential have no
    dwellings in the register (block_id 4, 24, 28, 52, 55, 107, 108, 112, 127, 196, 211, 220, 244). They are small
    (570–3 528 m²); 8 have no building at all, 5 have one or two buildings that are not dwellings.
- **Possible extension: legal vs planned vs mapped land use.** The general plan of Haapsalu is available as
  open data: WFS `https://gsavalik.envir.ee/geoserver/planeeringud/wfs`, layer `planeeringud:yld_plan_maakas`
  ("ÜP — maakasutuse juhtotstarve"), plan `planid` 1842001, updated 2024-11-13, covering 64.8 % of the town,
  licence CC BY 4.0 as stated by the service. It is **not downloaded**. A later comparison could set the
  legal purpose (cadastre), the planned purpose (general plan) and the mapped use (OSM) side by side.
- **Walking accessibility: assumptions and limitations.**
  - Walking speed **5 km/h (83.33 m/min)** is a conditional assumption: a generic average walking speed.
    It is the default of IduEdu (`get_walk_graph`, `iduedu/modules/drive_walk_builder.py:181`), which states no
    source for it in its code; it is not a national norm. IduEdu also uses a hardcoded 5 km/h for the
    first and last segment from the block point to the nearest graph node (`matrix_builder.py:224`), which
    does not follow a changed `walk_speed`.
  - The 15 minutes for schools in the BlocksNet service table (Russian standards) are **not used**.
  - **Block point.** BlocksNet takes the `representative_point` of each block as its origin and destination. For
    the large blocks 2 and 172 this point can fall in a forest, so accessibility "from the block" is conditional
    there.
  - **Graph is frozen like the other data:** the graph is saved in `data/raw/`, its download date goes to
    `data/download_dates.json`, and the osmnx cache is directed to `data/raw/osmnx_cache` (osmnx would otherwise
    create a `cache` folder in the project).
  - **Cycleways (checked on the cached OSM data of the town, nothing downloaded again).** The osmnx `walk`
    filter used by IduEdu excludes `highway=cycleway`. In Haapsalu linn there are 72 such lines, 11.75 km:
    `foot=designated` 28 lines (6.31 km), `foot=yes` 9 (3.60 km), no `foot` tag 35 (1.83 km), `foot=no` none. They are
    7.1 % of the length of the walk network (about 165 km by the tags; approximation of the osmnx filter).
    `get_walk_graph` has no parameter for a road filter (the filter is fixed in the code at line 218; only the drive
    graph uses a `custom_filter`).
  - **Decision: own walk graph with cycleways** (the 5 % of the walk network length was a conventional
    guideline, not a rule). One download with `osmnx.graph_from_polygon` for the convex hull of the blocks, with the
    osmnx `walk` filter in which `cycleway` is not excluded (`foot=no` is still excluded; there are no such
    cycleways now). **Assumption: shared paths (cycleways) without a `foot` tag are walkable by pedestrians; this
    was not checked against the OSM access rules for Estonia** (35 lines, 1.83 km, 15.6 % of the cycleway length).
    The graph is built as in IduEdu `get_walk_graph` (EPSG:3301, `length_meter`, `time_min` at 5 km/h, only
    the largest connected component, node `x`, `y`, graph `crs`), with every edge in both directions
    (pedestrians ignore one-way rules; osmnx does this only for `network_type="walk"`). A second graph without
    cycleways, from the same download, is only for comparison. The raw download is in
    `data/raw/walk_graph_download.pickle` (date in `download_dates.json`, key `osm_walk_graph`), the osmnx
    cache is `data/raw/osmnx_cache`; a rerun does not download again.
  - **Deliberate difference from IduEdu: the shortest parallel edge.** IduEdu turns the multigraph into a simple
    graph with `nx.DiGraph`, which keeps the **last** of the parallel edges of a pair of nodes, not the shortest
    (in our graph that was wrong for 49 of 92 pairs). The own graph keeps the shortest edge (the lowest key if
    equal): 98 parallel edges removed in the main graph, 93 in the comparison graph. The matrix is symmetric now.
  - **Where the nodes go.** Main graph: 8 708 nodes in the raw download (not simplified), the same after both
    directions are added; simplification removes 6 018 nodes that lie in the middle of a line (2 neighbours,
    which is exactly the number of such raw nodes), leaving 2 690; the parallel edges change no node; keeping only
    the largest connected component removes 46 (15 components before), leaving **2 644 nodes and 7 294 directed
    edges**, 191 km of ways. Comparison graph (no cycleway): 8 353 nodes after the cycleway edges and the nodes left
    without edges (355) are removed, 2 557 after simplification, 2 498 nodes and 6 681 edges after the largest
    component (59 removed), 176 km.
  - **Result.** Matrix `data/accessibility_matrix.parquet` (rows and columns `block_id`; column names are saved as
    text), type **float16**, which is the default of IduEdu and is kept; it is saved as float16. The asymmetry is 0.
    Comparison with the graph without cycleways over the 43 956 pairs of blocks: the median time saved is 0.00 min,
    the 95th percentile 3.31 min, the maximum 19.4 min; 5 923 pairs (13.5 %) are faster by more than 2 min. 1 638
    pairs (3.7 %) are slower with the cycleways: median 0.02 min, 95th percentile 0.88 min, maximum 3.04 min (21
    pairs by more than 1 min). **All pairs slower by more than 0.1 min involve one of 8 blocks (32, 33, 35, 84, 86,
    102, 147, 149) whose block point snaps to a different nearest node in the two graphs;** the nearest node as the
    crow flies is not always the best entry to the network (example: block 33, 47 m to node 1180 in the main
    graph, 57 m to node 1035 in the other, and from node 1180 the way to block 2 is 3.2 min longer). The rest of the
    slower pairs are rounding noise of the `float16` matrix.
    `blocks.geojson` has `median_accessibility` (median over all blocks of the row of the matrix, the block itself
    with time 0 included): city median 19.6 min, range 13.4–56.0 min; large blocks 2 and 172: 24.0 and 19.7 min.
    Map `data/accessibility_check.png`.
  - **Limitation: snapping of the block point.** The block point (`representative_point`) is connected to the
    nearest graph node as the crow flies, not to the node that is the best entry to the network. For 8 blocks (32,
    33, 35, 84, 86, 102, 147, 149) the nearest node is a different one in the graph with and without cycleways,
    which gives differences of up to 3 min between the two graphs for the pairs that involve these blocks.
  - **Checks.** No infinite, empty or negative values; the diagonal is 0. The block point is farther than 200 m
    from the nearest graph node for 2 blocks: 3 (207 m) and 178 (202 m).
- **Schools: access and provision (basic school, main calculation).**
  - **Schools.** Included: the municipal basic schools **Haapsalu Põhikool** (block 73, 598 pupils of grades 1–9)
    and **Haapsalu Linna Algkool** (block 253, 282 pupils of grades 1–6); places = 880 pupils of grades 1–9 on 1 October
    2026 (EHIS). Not included: **Haapsalu Viigi Kool** (EHIS flag `hev = jah`: school for children with special
    educational needs, state-owned, pupils from the whole county) and **Haapsalu Montessori Kool** (private, 7 pupils
    of grades 1–9). **Gymnasium:** only `time_to_gymnasium_min` to Läänemaa Ühisgümnaasium (block 245, grades 10–12,
    304 pupils, state-owned), no model.
  - **Demand.** 891 children aged 7–15 (census 2021, RL21003), distributed over the blocks in proportion to
    `population_block` (assumption; whole numbers by the largest remainder method; column `children_7_15`).
  - **Times.** `time_to_basic_school_min` is the walking time (matrix of the walk graph, 5 km/h) to the nearest of the two
    basic schools; median 11.4 min, the maximum 49.7 min (block 3); `time_to_gymnasium_min`: median 19.5 min, maximum
    64.3 min. Both columns are in `blocks.geojson`; map `data/schools_check.png`.
  - **Law, PGS § 7 lõige 3** (https://www.riigiteataja.ee/akt/PGS, read on 2026-10-31): «(3) Vähemalt 80 protsendil õpilastest,
    kelle jaoks põhikool on elukohajärgne kool, ei tohi kooli jõudmiseks kuluda rohkem kui 60 minutit.» The law does not say
    how the way is made; **we count on foot** and take the nearest of the two schools as the school of the child.
    Share of the 891 children (distributed demand) within a walking time of the nearest basic school: 10 min 42.3 %
    (377 children), 15 min 75.1 % (669), 20 min 95.4 % (850), 30 min 100 %, 60 min 100 %. The norm (80 % within 60 minutes)
    is met with 100 %.
  - **`competitive_provision`**, `self_supply=True` (the default), `max_depth=1`, thresholds 10, 15, 20 min;
    `provision_strong` of the town 0.423, 0.751, 0.921; blocks with children (173) with `provision_strong < 1`: 89, 43, 32
    (the value of a block is 0 or 1 in all three cases); results with `self_supply=False` are the same. Columns
    `provision_strong_10`, `_15`, `_20` in `blocks.geojson`. The places (880) are fewer than the children (891), so the value for
    the town cannot be above 0.988.
  - **Check of the code.** I suspected that `_supply_self` subtracts the used places twice. **It does not:** the line
    `blocks_df[CAPACITY_LEFT_COLUMN] -= supply` is there once (`blocksnet/analysis/provision/competitive/core.py`, line 60);
    my first reading came from a listing in which this line was printed twice. A toy example of three blocks (block 1: 15
    places and 10 children, block 2: 8 children 5 min away, block 3: 4 children 20 min away, threshold 10 min) gives by
    hand and in the code the same: 5 places left in block 1 after self-supply, `provision_strong` 1.0, 0.625 and 0.0.
  - **Limitations.** The places are the **actual pupils of 2026, not the capacity** of the schools (EHIS open data has no
    number of places), so the result shows how the schools are placed relative to the children, not whether there are enough
    places. The census of 2021 is compared with the pupils of 2026. Some pupils live outside the town. Some children of the
    town go to schools outside it (for example Uuemõisa Lasteaed-Algkool and Ridala Põhikool, which are outside the
    settlement), or to the excluded schools. The age of the children by block is not known (demand follows the population).
    **Haapsalu Linna Algkool teaches only grades 1–6**, while the model treats the places of the two schools as
    interchangeable for all children aged 7–15 (the children of grades 7–9 cannot study there; its places are
    282 pupils of grades 1–6). The result is therefore more favourable than the real situation for the children of
    grades 7–9 near Linna Algkool and far from Põhikool.
    EHIS and Statistics Estonia have no place of residence of the pupils by school or municipality. For the large blocks 2 and
    172 the block point may lie in a forest.
- **Q2 by blocks: numbers** (pairing rule: overlap above 50 % of the smaller building; columns `n_official_unmatched`,
  `n_osm_unmatched`, `match_rate`, `levels_coverage_osm`, `floors_coverage_official` in `blocks.geojson`; map
  `data/q2_check.png`):
  - Official buildings without OSM pair: 118, mostly auxiliary buildings, foundations and canopies (104 + 7 + 4), 111
    without EHR link; none built after 2020. All 33 official buildings first used 2021–2026 have an OSM pair.
  - OSM buildings without official pair: 295; 176 without source tag; 13 greenhouses, 9 roofs; 64 carry a `maaamet:ETAK` id
    absent from current official data (possibly demolished, not verified).
  - Floors: OSM 3.6 %, registry 75.7 %.
  - way/150593045 lies on a water polygon, outside blocks — known exception (so the sum over the blocks is 294 OSM
    buildings without a pair, not 295).
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

**Open question: licence of the published data.** Share-alike terms apply to some inputs: OSM (ODbL 1.0)
and Statistics Estonia (CC BY-SA 4.0), and school buildings from EHIS are marked CC BY-SA 3.0. Derived layers in
the repository (for example `blocks.geojson`, which uses OSM roads and water, and `population_block`, which
uses the census total) may have to be shared under compatible terms. To be decided, and the licence of the
repository chosen, before publishing (step 9).
**Status 2026-10-31:** published without deciding it; `data/LICENSE.md` lists the terms per file and its section "Not verified" keeps the question open.

## Steps

1. **Set-up.** Project folder, Python 3.12 environment, BlocksNet, empty GitHub repository.
2. **Boundary.** EHAK "Asustusüksused", Haapsalu linn. Check it on a map.
3. **Data.** Download the layers above (official buildings via WFS for the boundary only), record source and date, save as GeoJSON. Verify the "assumed" sources.
4. **Blocks.** Build city blocks with BlocksNet (roads incl. `highway=service`, and water; no railway). Drop islands and slivers without buildings (separate files); mark undeveloped blocks (`built_up`) and large blocks (`large_block`). **Stop and check the blocks on a map** before any metrics.
5. **Metrics.** Land use shares, density, Spacematrix, population estimate (official census 2021 living area per person; one comparison with the official population as a check), schools (EHIS capacity, children aged 7–18; BlocksNet norm only as a stated fallback), walking accessibility, as in BlocksNet `examples/pipeline.ipynb`.
6. **Building comparison (Q2).** Match OSM and official buildings, count missing ones, compare floors, count buildings without floors in OSM / EHR / both; recompute population and density with official floors; compare with the EHR net floor area estimate.
7. **Dashboard.** One `dashboard.html`: map of blocks, charts and tables, plus a page section for the OSM vs official comparison. Show `osr` with the colour scale clipped at the 95th percentile (the maximum is 13 715 because of a block with one building).
8. **Checks.** A table "metric — notebook — dashboard" to prove the numbers match; a re-run instruction.
9. **Publish.** GitHub repository with README, plan, notebook, GeoJSON, script, dashboard; a short LinkedIn post.
   **Done 2026-10-31:** repository public, dashboard published on GitHub Pages (https://aleks-nab.github.io/haapsalu-urban-blocks/); MIT for the code, terms per data file in `data/LICENSE.md`. The LinkedIn post is not done.

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
