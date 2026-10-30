# Haapsalu urban blocks and building data quality

Research plan · draft 1 · Aleksandra Nabiulina · 2026-10-30

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
   - effect: how much do the population and density estimates change if official
     floors are used instead of OSM floors?
3. **Towards 3D cadastre (discussion).** What would be needed to go from floors to
   heights and volumes, and what the gaps found in question 2 mean for that.

## Data (to be confirmed before use, each with source and download date)

| Topic | Source (candidate) | Used for |
| --- | --- | --- |
| Roads, water, land use, buildings, schools | OpenStreetMap (Geofabrik extract for Estonia or Overpass) | blocks, metrics (course task) |
| Official building footprints | Maa- ja Ruumiamet, ETAK buildings | Q2 completeness |
| Official number of floors | Estonian Building Register (EHR) open data, or Maa- ja Ruumiamet 3D building models | Q2 floors, Q3 |
| Population check | Statistics Estonia (settlement or grid population) | sanity check of the estimated population |
| School places | Estonian Education Information System (EHIS) | real school capacity instead of an estimate |
| Travel time | a ready-made graph, as the course says | accessibility |

Which official dataset actually has the number of floors is checked first, not assumed.

## Steps

1. **Set-up.** Project folder, Python 3.12 environment, BlocksNet, empty GitHub repository.
2. **Boundary.** The Haapsalu town boundary (official administrative boundary).
3. **Data.** Download the layers above, record source and date, save as GeoJSON.
4. **Blocks.** Build city blocks with BlocksNet. **Stop and check the blocks on a map** before any metrics.
5. **Metrics.** Land use shares, density, Spacematrix, population estimate, schools, accessibility, as in BlocksNet `examples/pipeline.ipynb`.
6. **Building comparison (Q2).** Match OSM and official buildings, count missing ones, compare floors; recompute population and density with official floors.
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
