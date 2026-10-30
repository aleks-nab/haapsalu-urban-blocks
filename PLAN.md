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
2. **Building data quality (my extension).** How complete and how accurate are
   OpenStreetMap buildings in Haapsalu compared with the official Estonian data:
   - footprint: which buildings are missing in OSM, which exist only in OSM;
   - number of floors: how often OSM has it at all, and how often it matches;
   - missing floors as a finding: how many buildings lack floors in OSM, in EHR,
     and in both;
   - effect: how much do the population and density estimates change if official
     floors are used instead of OSM floors?
   - two ways to estimate population: footprint × floors (BlocksNet default) versus
     the EHR net floor area (`suletud_netopind`) of residential buildings.
3. **Towards 3D cadastre (discussion).** What would be needed to go from floors to
   heights and volumes, and what the gaps found in question 2 mean for that.

## Data (each recorded with source, download date and licence)

Status: **checked** = the source page or service description was read on 2026-10-30
(no data downloaded yet); **assumed** = not verified yet, to be checked before use.

| Topic | Source | Used for | Status |
| --- | --- | --- | --- |
| Town boundary | Maa- ja Ruumiamet, EHAK administrative and settlement division, layer "Asustusüksused", unit **Haapsalu linn** (the settlement, not the municipality, which since 2017 also includes the former Ridala vald). SHP, updated monthly, open licence. | study area | checked (source); assumed: the polygon follows the coastline |
| Official buildings: footprints, floors, height, areas, use | Maa- ja Ruumiamet WFS `https://gsavalik.envir.ee/geoserver/etak_tuletis/wfs`, layer `etak_tuletis:etak_ehr_hooned` (ETAK buildings enriched with Building Register EHR data), requested for Haapsalu only. Fields include `max_korruste_arv`, `min_korruste_arv`, `korgus`, `ehitisalune_pind`, `suletud_netopind`, `kaos_nimetus`, `esmane_kasutus`, `ehr_gid`. Updated daily, open licence (CC BY 4.0 equivalent). | Q2, Q3 | checked (field list); assumed: how complete the fields are, and how many buildings have no EHR link |
| Roads, water, land use, buildings, schools | OpenStreetMap (via osmnx, as in BlocksNet `examples/pipeline.ipynb`) | blocks, metrics (course task), Q2 | checked (method) |
| Living area per person | Statistics Estonia, census 2021: average floor area per person for Haapsalu if published, otherwise Lääne county, otherwise the Estonian average (30.1 m²). Table code and download date to be cited. | population estimate (model parameter) | assumed (table not located yet) |
| Official population of Haapsalu town | Statistics Estonia, population of the settlement Haapsalu linn | check of the model and the building data | assumed |
| Population grid | Statistics Estonia, census 2021 grid | optional block-level check | assumed |
| School capacity | Estonian Education Information System (EHIS): actual capacity or number of students of each school in Haapsalu | school capacity instead of the BlocksNet estimate | assumed |
| School-age children (7–18) | Statistics Estonia, population by age for Haapsalu linn (or the smallest published area that contains it) | school demand instead of the BlocksNet norm | assumed |
| 3D building models | Maa- ja Ruumiamet 3D building models | Q3 | assumed (old page not found); the `korgus` field above may be enough |
| Travel graph | **walking** graph built by BlocksNet / IduEdu from OSM | accessibility, school provision | checked (function exists in BlocksNet 1.0.0a9) |

Known data issues (from press and studies, checked): parts of the EHR are hidden from
the public, and one building can have several EHR records.

## Method decisions

- **Living area per person comes from official statistics, not from tuning.** Use the
  Statistics Estonia census 2021 average floor area per person: for Haapsalu if
  available, otherwise for Lääne county, otherwise the Estonian average of 30.1 m².
  The table and its date are cited in the README. The BlocksNet defaults (20 m² default,
  30 m² in the example) are not used.
- **One check, not calibration.** The estimated population is compared once with the
  official population of Haapsalu linn. The difference is reported as a check of the
  model and of the building data; the parameter is not changed to make them match.
- **Second population estimate** from the EHR net floor area (`suletud_netopind`) of
  residential buildings, compared with the footprint × floors approach.
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
- **Railway:** the Haapsalu line is closed; the railway layer may be empty, which is fine.

## Steps

1. **Set-up.** Project folder, Python 3.12 environment, BlocksNet, empty GitHub repository.
2. **Boundary.** EHAK "Asustusüksused", Haapsalu linn. Check it on a map.
3. **Data.** Download the layers above (official buildings via WFS for the boundary only), record source and date, save as GeoJSON. Verify the "assumed" sources.
4. **Blocks.** Build city blocks with BlocksNet. **Stop and check the blocks on a map** before any metrics.
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
