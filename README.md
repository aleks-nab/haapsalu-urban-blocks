# Haapsalu urban blocks

Live dashboard: https://aleks-nab.github.io/haapsalu-urban-blocks/

Self-study GIS project: city blocks and block metrics for Haapsalu, Estonia, built with
[BlocksNet](https://github.com/aimclub/blocksnet), plus a comparison of OpenStreetMap
buildings with official Estonian building data (footprints and number of floors).

Status: metrics and dashboard done, published on GitHub Pages.

Dashboard: [dashboard.html](dashboard.html) (one file; open it in a browser; the basemap needs the internet).
Overview and key findings: [dashboard.html#overview](dashboard.html#overview).

## Key findings

Numbers are calculated by `build_dashboard.py` from the files in `data/`; details and limits are in the tab
*Methods & limitations* of the dashboard and in [PLAN.md](PLAN.md).

<!-- key-findings:start -->
- Building-only population estimate is 1.73–2.52× the census (24 % of dwelling floor area vacant is one known reason)
- Floors: 75.7 % of official buildings vs 3.6 % in OSM
- 64 OSM buildings carry an ETAK id absent from current official data (possibly demolished, not verified)
- Shared foot/cycle paths shorten walking time by more than 2 min for 13.5 % of block pairs
- All children aged 7-15 live within 30 min walk of a municipal basic school; the PGS § 7 (3) 60-minute rule is met (walking assumed)
<!-- key-findings:end -->

See [PLAN.md](PLAN.md) for the research questions, data sources and steps.

## Environment

- Python 3.12, virtual environment in `.venv` (not committed)
- BlocksNet 1.0.0a9

## Data sources and licences

See [Acknowledgements and credits](#acknowledgements-and-credits) below and
[data/SOURCES.md](data/SOURCES.md) (source, URL, licence, download date and number of features of every layer).

## Acknowledgements and credits

**BlocksNet.** City blocks are cut with [BlocksNet](https://github.com/aimclub/blocksnet)
(version 1.0.0a9, [PyPI](https://pypi.org/project/blocksnet/)), developed by the Institute of Design and
Urban Studies (IDU), ITMO University. BlocksNet is released under the BSD-3-Clause licence.
BlocksNet is installed as a dependency via pip; no BlocksNet source code is copied into this repository.
Publication listed by the BlocksNet authors: Churiakova T., Starikov V., Sudakova V., Morozov A., Mityagin S.
[Digital Master Plan as a tool for generating territory development requirements](https://link.springer.com/chapter/10.1007/978-3-031-48855-9_4).
ARTIIS 2023.

**Course.** Based on practice 2 of the ITMO University course «Технологии ИИ в урбанистике»
(AI Technologies in Urban Studies).

**AI assistance.** Code written with the assistance of Claude Code (AI coding agent); research questions, data choices and decisions by the author.

**Data.** Details, URLs, licences and download dates are in [data/SOURCES.md](data/SOURCES.md).

- OpenStreetMap: roads, water, land use, buildings and schools, © OpenStreetMap contributors, licensed under the
  [ODbL](https://www.openstreetmap.org/copyright).
- Republic of Estonia Land and Spatial Development Board (Maa- ja Ruumiamet): settlement boundary (EHAK) and
  ETAK buildings with Building Register data, under the
  [Maa- ja Ruumiamet opendata licence](https://geoportaal.maaruum.ee/opendata-licence) of 01.01.2025.
  Reference required by the licence: *ETAK buildings with EHR data and EHAK settlement boundary: Republic of
  Estonia Land and Spatial Development Board, extract 30.10.2026.*
- Cadastral parcels (land-use purpose): Maa- ja Ruumiamet cadastre WFS `kataster:ky_kehtiv`, published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) with attribution to the Estonian Ministry of Economic Affairs and Communications (wording of the service quoted in [data/SOURCES.md](data/SOURCES.md)), extract 2026-10-31. The land use of the blocks is the cadastral purpose (legal), not actual use.
- Statistics Estonia: population and housing census 2021 (tables RL21003, RL21218 and RL21807). The database
  states: "Statistics Estonia’s open data can be shared under Creative Commons (CC) licence BY-SA 4.0"
  ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en)).
- Estonian Education Information System (EHIS) open data, from the
  [open data portal](https://andmed.eesti.ee/datasets/eesti-hariduse-infosusteemi-avaandmed-oppeasutuste-hooned):
  school buildings, licence field `CC_BY_SA_3.0` in the portal record. Number of students per school: no licence
  is stated for the data on the pages checked (list of pages in [data/SOURCES.md](data/SOURCES.md)).

## Licence

- Code (`notebook.ipynb`, `build_dashboard.py`): [MIT](LICENSE). It does not apply to the data. `vendor/leaflet-1.9.4/` keeps its own licence file.
- Data in `data/`: see [data/LICENSE.md](data/LICENSE.md) (terms of each source, per file).

This is a self-study project; the licence notes are not a legal assessment.
