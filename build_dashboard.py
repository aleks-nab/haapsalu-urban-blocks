"""Build dashboard.html (and its copy docs/index.html) from the saved results in data/.

One self-contained HTML file: Leaflet 1.9.4 (vendor/leaflet-1.9.4), the block data and all texts are inside it.
Only the basemap tiles are requested live by the browser. Every number in the texts is calculated here from the
files in data/; the table in the tab "Checks" compares them with data/notebook_numbers.json written by the notebook.

Usage:  python build_dashboard.py
"""
import html
import json
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LEAFLET = ROOT / "vendor" / "leaflet-1.9.4"

# Parameters of the method (the same values as in the notebook; they are not calculated)
WALK_SPEED_KMH = 5          # assumption of the walking accessibility
METRES_PER_FLOOR = 3        # assumption for buildings without the number of floors in the register
MIXED_SHARE = 0.5           # land_use_display is "mixed" if the largest class covers less than this share of the parcels
LARGE_BLOCK_LABEL_KM2 = 1   # blocks over this area have large_block = True
THRESHOLDS = (10, 15, 20, 30, 60)   # minutes on foot, share of the children
PROVISION = (10, 15, 20)            # minutes on foot, competitive_provision
BASIC_SCHOOLS = {"75012966", "75012952"}  # EHIS registry codes: Haapsalu Põhikool, Haapsalu Linna Algkool
OTHER_SCHOOLS = {"75038167": "Gymnasium (grades 10-12); only the walking time to it is calculated",
                 "70005660": "School for children with special educational needs; not in the calculation",
                 "80650545": "Private school; not in the calculation"}
BASEMAP_YEAR = 2026
AUTHOR = "Aleksandra Nabiulina"
REPO_URL = "https://github.com/aleks-nab/haapsalu-urban-blocks"
NO_MAP_TABS = ("methods", "sources", "checks")  # text only, full width
TILES = "https://tiles.maaamet.ee/tm/tms/1.0.0/hallkaart@GMC/{z}/{x}/{-y}.png"
TERMS_URL = ("https://geoportaal.maaruum.ee/est/teenused/wms-wfs-wcs-teenused/"
             "maa-ja-ruumiameti-kaarditeenuste-kasutustingimused-p24.html")
LAND_COLOURS = {"residential": "#f2c94c", "business": "#eb5757", "industrial": "#9b51e0", "transport": "#828282",
                "recreation": "#6fcf97", "special": "#2d9cdb", "agriculture": "#a0522d", "mixed": "#d9d2c3"}
Q2_COLOURS = {"official": "#08306b", "osm": "#ff7f00", "absent": "#d81b9a"}


# ---------------------------------------------------------------- helpers

def num(x, d=0):
    return f"{x:,.{d}f}"


def pct(x, d=1):
    return f"{100 * x:.{d}f} %"


def rnd(o):
    if isinstance(o, list):
        return [rnd(i) for i in o]
    return round(o, 5)


def geom_json(g):
    g = shapely.set_precision(g, 1e-5)
    j = json.loads(shapely.to_geojson(g))
    j["coordinates"] = rnd(j["coordinates"])
    return j


def clean(v, d=None):
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or v is pd.NA:
        return None
    if isinstance(v, (np.bool_, bool)):
        return int(v)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), d) if d is not None else float(v)
    return v


def feature_collection(gdf, decimals):
    gdf = gdf.to_crs(4326)
    feats = []
    for rec in gdf.to_dict("records"):
        g = rec.pop("geometry")
        feats.append({"type": "Feature", "geometry": geom_json(g),
                      "properties": {k: clean(v, decimals.get(k)) for k, v in rec.items()}})
    return {"type": "FeatureCollection", "features": feats}


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- data

blocks_raw = gpd.read_file(DATA / "blocks.geojson")
boundary = gpd.read_file(DATA / "boundary.geojson")
schools = gpd.read_file(DATA / "schools.geojson")
q2 = gpd.read_file(DATA / "q2_unmatched_buildings.geojson")
official = gpd.read_file(DATA / "official_buildings.geojson", ignore_geometry=True)
osm = gpd.read_file(DATA / "osm_buildings.geojson", ignore_geometry=True)
islands = gpd.read_file(DATA / "blocks_dropped_islands.geojson", ignore_geometry=True)
slivers = gpd.read_file(DATA / "blocks_dropped_slivers.geojson", ignore_geometry=True)
stats = json.loads((DATA / "statistics.json").read_text(encoding="utf-8"))
popcheck = json.loads((DATA / "population_check_city.json").read_text(encoding="utf-8"))
nbnum = json.loads((DATA / "notebook_numbers.json").read_text(encoding="utf-8"))
dates = json.loads((DATA / "download_dates.json").read_text(encoding="utf-8"))

b = blocks_raw.copy()
b["pph"] = b["population_block"] / (b["area_m2"] / 10_000)
cols = {"block_id": 0, "area_m2": 0, "land_use_display": None, "share": 3, "population_block": 2, "pph": 1,
        "gsi": 3, "fsi": 3, "l": 2, "osr": 2, "median_accessibility": 4, "time_to_basic_school_min": 4,
        "time_to_gymnasium_min": 4, "children_7_15": 0, "provision_strong_10": 3, "provision_strong_15": 3,
        "provision_strong_20": 3, "match_rate": 3, "n_official_unmatched": 0, "n_osm_unmatched": 0,
        "n_official_q2": 0, "n_osm_q2": 0, "floors_coverage_official": 2, "large_block": None, "built_up": None,
        "n_dwellings": 0, "geometry": None}
b = b[list(cols)]
# provision is empty where a block has no children (the notebook keeps NaN there)
blocks_fc = feature_collection(b, {k: v for k, v in cols.items() if v is not None})
emb = pd.DataFrame([f["properties"] for f in blocks_fc["features"]])  # exactly what is embedded in the page
emb["children_7_15"] = emb["children_7_15"].astype(int)

boundary_fc = feature_collection(boundary[["geometry"]], {})

sch = schools[["name", "reg_nr", "students", "address", "geometry"]].copy()
sch["reg_nr"] = sch["reg_nr"].astype(str)
sch["basic"] = sch["reg_nr"].isin(BASIC_SCHOOLS)
sch["kind"] = [("Basic school, in the main calculation" if r in BASIC_SCHOOLS else OTHER_SCHOOLS.get(r, "Other school"))
               for r in sch["reg_nr"]]
sch = sch.drop(columns="reg_nr")
schools_fc = feature_collection(sch, {})

q2w = q2.to_crs(4326)
kinds = sorted(q2["kind"].unique())
group_of = {"official": "official", "osm": "osm"}
points = []
for r in q2w.itertuples():
    g = "absent" if r.status == "absent_from_official_data" else r.layer
    points.append([round(r.geometry.x, 5), round(r.geometry.y, 5), g, kinds.index(r.kind), r.status, r.ref])

# ---------------------------------------------------------------- numbers (all from the data)

N = {}
N["blocks"] = len(emb)
N["built_up"] = int(emb["built_up"].sum())
N["large"] = int(emb["large_block"].sum())
N["pop"] = float(emb["population_block"].sum())
N["pop_census"] = int(stats["population_haapsalu_linn_2021"])
N["off"] = len(official)
N["osm"] = len(osm)
oq = q2[q2["layer"] == "official"]
mq = q2[q2["layer"] == "osm"]
N["off_un"] = len(oq)
N["osm_un"] = len(mq)
N["osm_un_absent"] = int((mq["status"] == "absent_from_official_data").sum())
N["osm_un_notag"] = int((mq["status"] == "no_etak_tag").sum())
N["osm_un_town"] = int((mq["status"] == "etak_id_in_town_layer").sum())
N["off_un_blocks"] = int(emb["n_official_unmatched"].sum())
N["osm_un_blocks"] = int(emb["n_osm_unmatched"].sum())
N["match_town"] = 1 - N["off_un"] / N["off"]
N["floors_off"] = float((official["floors_source"] == "registry").mean())
N["levels_osm"] = float(pd.to_numeric(osm["building:levels"], errors="coerce").notna().mean())
N["children"] = int(emb["children_7_15"].sum())
N["places"] = int(schools.loc[schools["reg_nr"].astype(str).isin(BASIC_SCHOOLS), "students"].sum())
N["n_islands"] = len(islands)
N["n_slivers"] = len(slivers)
t_basic = emb["time_to_basic_school_min"]
N["t_med"] = float(t_basic.median())
N["t_max"] = float(t_basic.max())
N["t_max_block"] = int(emb.loc[t_basic.idxmax(), "block_id"])
N["acc_med"] = float(emb["median_accessibility"].median())
N["acc_min"] = float(emb["median_accessibility"].min())
N["acc_max"] = float(emb["median_accessibility"].max())
walk = {}
for t in THRESHOLDS:
    ch = int(emb.loc[t_basic <= t, "children_7_15"].sum())
    walk[t] = dict(children=ch, share=ch / N["children"], blocks=int((t_basic <= t).sum()))
prov = {}
for t in PROVISION:
    p = emb[f"provision_strong_{t}"]
    has = emb["children_7_15"] > 0
    prov[t] = dict(town=float((emb["children_7_15"] * p.fillna(0)).sum() / N["children"]),
                   blocks_with_children=int(has.sum()), below_1=int((has & (p < 1)).sum()))
fl = official["floors_source"].value_counts()
N["floors_not_registry"] = 1 - float(fl.get("registry", 0)) / len(official)
pop_blocks = int((emb["population_block"] > 0).sum())
lu = (emb.groupby("land_use_display").agg(blocks=("block_id", "size"), pop=("population_block", "sum"),
                                            area=("area_m2", "sum")).sort_values("blocks", ascending=False))
mixed_ok = bool(((emb["land_use_display"] == "mixed") == (emb["share"] < MIXED_SHARE)).all())
non_res_pop = float(emb.loc[emb["land_use_display"] != "residential", "population_block"].sum()) / N["pop"]
dens = emb.loc[(emb["large_block"] == 0) & (emb["population_block"] > 0), "pph"]
big = emb.loc[emb["large_block"] == 1, "area_m2"]
gs = emb[(emb["gsi"] > 0) & (emb["fsi"] > 0)]
scale = dict(pph=float(np.percentile(emb.loc[emb["population_block"] > 0, "pph"], 95)),
             fsi=float(np.percentile(gs["fsi"], 95)),
             acc=[float(emb["median_accessibility"].min()), float(np.percentile(emb["median_accessibility"], 98))],
             time=float(np.percentile(t_basic, 98)))
top_kinds = oq["kind"].value_counts().head(3)

# ---------------------------------------------------------------- checks table: indicator, notebook, dashboard

checks = []


def chk(name, nb, dash, fmt=str):
    checks.append(dict(name=name, nb=fmt(nb), dash=fmt(dash), ok=fmt(nb) == fmt(dash)))


i0 = lambda x: num(round(x))
chk("Population, sum over the blocks (people)", nbnum["population_block_sum"], N["pop"], i0)
chk("Population, census 2021 (RL21003)", nbnum["official_population_2021"], N["pop"], i0)
chk("Urban blocks", nbnum["n_blocks"], N["blocks"], i0)
chk("Built-up blocks", nbnum["n_built_up_blocks"], N["built_up"], i0)
chk("Large blocks", nbnum["n_large_blocks"], N["large"], i0)
chk("Official buildings in town", nbnum["n_official_buildings"], N["off"], i0)
chk("OSM buildings in town", nbnum["n_osm_buildings"], N["osm"], i0)
chk("Official buildings without OSM pair (layer)", nbnum["n_official_unmatched"], N["off_un"], i0)
chk("Official buildings without OSM pair (sum over blocks)", nbnum["n_official_unmatched_in_blocks"],
    N["off_un_blocks"], i0)
chk("OSM buildings without official pair (layer)", nbnum["n_osm_unmatched"], N["osm_un"], i0)
chk("OSM buildings without official pair (sum over blocks)", nbnum["n_osm_unmatched_in_blocks"],
    N["osm_un_blocks"], i0)
chk("OSM buildings with an ETAK id absent from official data", nbnum["n_osm_absent_from_official"],
    N["osm_un_absent"], i0)
chk("Match rate of official buildings, town", nbnum["match_rate_town"], N["match_town"], lambda x: f"{x:.4f}")
chk("Official buildings with floors in the register", nbnum["floors_coverage_official"], N["floors_off"],
    lambda x: f"{x:.4f}")
chk("OSM buildings with building:levels", nbnum["levels_coverage_osm"], N["levels_osm"], lambda x: f"{x:.4f}")
chk("Children aged 7-15 (distributed over blocks)", nbnum["children_7_15"], N["children"], i0)
chk("Places in the basic schools (pupils 2026)", nbnum["school_places"], N["places"], i0)
for t in THRESHOLDS:
    chk(f"Children within {t} min of a basic school, %", nbnum["walk_share_pct"][str(t)], 100 * walk[t]["share"],
        lambda x: f"{x:.1f}")
for t in PROVISION:
    chk(f"Provision (strong) of the town, {t} min", nbnum["provision_strong_town"][str(t)], prov[t]["town"],
        lambda x: f"{x:.3f}")
chk("Median time to the nearest basic school, min", nbnum["time_to_basic_school_median_min"], N["t_med"],
    lambda x: f"{x:.1f}")
chk("Longest time to the nearest basic school, min", nbnum["time_to_basic_school_max_min"], N["t_max"],
    lambda x: f"{x:.1f}")
n_ok = sum(c["ok"] for c in checks)

vacant_share = (stats["vacant_dwelling_area_m2_2021_haapsalu_linn"] / stats["all_dwelling_area_m2_2021_haapsalu_linn"])
children_line = (f"All children aged 7-15 live within 30 min walk of a municipal basic school"
                 if walk[30]["share"] == 1 else
                 f"{pct(walk[30]['share'])} of the children aged 7-15 live within 30 min walk of a municipal basic school")
rule_met = walk[60]["share"] >= 0.8
FINDINGS = [
    f"Building-only population estimate is {popcheck['ratio_net_to_official']:.2f}–{popcheck['ratio_gross_to_official']:.2f}× "
    f"the census ({vacant_share * 100:.0f} % of dwelling floor area vacant is one known reason)",
    f"Floors: {pct(N['floors_off'])} of official buildings vs {pct(N['levels_osm'])} in OSM",
    f"{N['osm_un_absent']} OSM buildings carry an ETAK id absent from current official data (possibly demolished, not verified)",
    f"Shared foot/cycle paths shorten walking time by more than 2 min for {pct(nbnum['cycleway_share_faster_over_2min'])} of block pairs",
    f"{children_line}; the PGS § 7 (3) 60-minute rule is {'met' if rule_met else 'not met'} (walking assumed)",
]
AUTHOR_LINE = f"{AUTHOR} · self-study project · October 2026 · GitHub: "

# ---------------------------------------------------------------- texts of the tabs


def card(value, label):
    return f'<div class="card"><b>{value}</b><span>{esc(label)}</span></div>'


def table(head, rows, cls=""):
    h = "".join(f"<th>{esc(x)}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


T = {}
T["overview"] = f"""
<h2>Haapsalu urban blocks</h2>
<h3 class="kf">Key findings</h3>
<ul class="kf">{''.join('<li>' + esc(x) + '</li>' for x in FINDINGS)}</ul>
<p>Haapsalu (Estonia) cut into <b>{num(N['blocks'])}</b> urban blocks along OpenStreetMap roads and water with
<a href="https://github.com/aimclub/blocksnet">BlocksNet</a>, and described by land use, population, building density,
walking accessibility and access to schools. A second question compares OpenStreetMap buildings with the official
Estonian building data. Choose a tab above; click a block on the map for its numbers.</p>
<div class="cards">
{card(num(N['pop_census']), 'inhabitants, census 2021 (distributed over the blocks)')}
{card(num(N['blocks']), 'urban blocks; ' + num(N['built_up']) + ' with buildings')}
{card(num(N['off']) + ' / ' + num(N['osm']), 'buildings: official / OpenStreetMap')}
{card(num(N['children']), 'children aged 7-15 (census 2021), distributed')}
{card(num(N['places']), 'pupils in the two basic schools, 2026')}
{card(pct(N['match_town']), 'official buildings with an OSM pair')}
</div>
<p>The {N['large']} blocks outlined in blue are large (over {LARGE_BLOCK_LABEL_KM2} km&sup2;); their values are less
meaningful (see <i>Methods &amp; limitations</i>). {num(N['n_islands'])} islands and {num(N['n_slivers'])} slivers without buildings
were dropped from the blocks (kept in separate files).</p>
<p class="note">The grey outline is the settlement boundary of Haapsalu linn (EHAK). This is a self-study project; the
numbers are results of a model with the stated assumptions (tab <i>Methods &amp; limitations</i>), not official statistics.</p>
<p class="by">{esc(AUTHOR_LINE)}<a href="{REPO_URL}">{REPO_URL}</a></p>
"""

lu_rows = [[esc(k), num(int(r.blocks)), num(r["pop"]), pct(r["pop"] / N["pop"]),
            num(r.area / 1e6, 2)] for k, r in lu.iterrows()]
T["landuse"] = f"""
<h2>Land use</h2>
<p>Each block gets the class with the largest share of its parcels' area, taken from the <b>cadastral land-use purpose
(legal), not the actual use of the land</b>. If the largest class covers less than {int(MIXED_SHARE * 100)} % of the
parcels the block is <i>mixed</i>{'' if mixed_ok else ' (rule not verified)'}.</p>
{table(['Class', 'Blocks', 'Population', 'Share of population', 'Area, km²'], lu_rows)}
<p>{pct(non_res_pop)} of the population lives in blocks whose class is not <i>residential</i> (this includes the mixed blocks).</p>
<p class="note">The cadastre says what a parcel may be used for; a parcel can be a house plot of a business class or the
other way round. OpenStreetMap land use is not used.</p>
"""

T["population"] = f"""
<h2>Population</h2>
<p>People per hectare of block area. The census total of Haapsalu linn ({num(N['pop_census'])} people, 2021) is
<b>distributed</b> over the blocks in proportion to the registry net floor area of their dwellings; it is not a count
per block. {num(pop_blocks)} blocks have population, the others have no dwellings.</p>
<p>Among the blocks with population (without the large blocks) the density is between {num(dens.min(), 1)} and
{num(dens.max(), 1)} people per hectare, median {num(dens.median(), 1)}. The scale on the map is clipped at the 95th
percentile ({num(scale['pph'], 0)}).</p>
<p>For comparison, the same population estimated from floor area gives a much higher number: registry net area of
dwellings divided by {popcheck['living_area_per_person_m2']} m&sup2; per person
(Statistics Estonia, census 2021) gives {num(popcheck['population_net'])} people
({popcheck['ratio_net_to_official']:.2f} times the census); footprint &times; floors gives
{num(popcheck['population_gross'])} ({popcheck['ratio_gross_to_official']:.2f} times). This is why the census total is
distributed instead.</p>
"""


def scatter():
    W, H, ml, mr, mt, mb = 520, 340, 46, 12, 12, 40
    xmax = np.ceil(gs["gsi"].max() * 10) / 10
    ymax = np.ceil(gs["fsi"].max() * 4) / 4
    px = lambda x: ml + (W - ml - mr) * x / xmax
    py = lambda y: H - mb - (H - mt - mb) * y / ymax
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Spacematrix: fsi against gsi of the blocks">']
    for i in range(int(round(xmax * 10)) + 1):
        x = i / 10
        s.append(f'<line class="gr" x1="{px(x):.1f}" y1="{py(0):.1f}" x2="{px(x):.1f}" y2="{py(ymax):.1f}"/>'
                 f'<text class="tk" x="{px(x):.1f}" y="{H - mb + 14}" text-anchor="middle">{x:.1f}</text>')
    for i in range(int(round(ymax * 4)) + 1):
        y = i / 4
        s.append(f'<line class="gr" x1="{px(0):.1f}" y1="{py(y):.1f}" x2="{px(xmax):.1f}" y2="{py(y):.1f}"/>'
                 f'<text class="tk" x="{ml - 6}" y="{py(y) + 4:.1f}" text-anchor="end">{y:.2f}</text>')
    for L in (1, 2, 3):
        x1 = min(xmax, ymax / L)
        s.append(f'<line class="gl" x1="{px(0):.1f}" y1="{py(0):.1f}" x2="{px(x1):.1f}" y2="{py(L * x1):.1f}"/>'
                 f'<text class="gt" x="{px(x1) - 3:.1f}" y="{py(L * x1) + 11:.1f}" text-anchor="end">L={L}</text>')
    for O in (1, 2, 4):
        x0 = max(0.0, 1 - O * ymax)
        s.append(f'<line class="go" x1="{px(x0):.1f}" y1="{py((1 - x0) / O):.1f}" x2="{px(xmax):.1f}" '
                 f'y2="{py((1 - xmax) / O):.1f}"/>'
                 f'<text class="gt" x="{px(xmax) - 3:.1f}" y="{py((1 - xmax) / O) - 4:.1f}" text-anchor="end">OSR={O}</text>')
    s.append(f'<text class="ax" x="{(ml + W - mr) / 2:.0f}" y="{H - 6}" text-anchor="middle">gsi (ground space index)</text>'
             f'<text class="ax" transform="translate(12 {(mt + H - mb) / 2:.0f}) rotate(-90)" text-anchor="middle">'
             f'fsi (floor space index)</text>')
    for r in gs.itertuples():
        c = LAND_COLOURS.get(r.land_use_display, "#999")
        s.append(f'<circle class="pt" cx="{px(r.gsi):.1f}" cy="{py(r.fsi):.1f}" r="{3.2 if not r.large_block else 5}" '
                 f'fill="{c}" data-id="{r.block_id}" tabindex="0"><title>Block {r.block_id}: gsi {r.gsi:.3f}, '
                 f'fsi {r.fsi:.3f}</title></circle>')
    s.append("</svg>")
    print(f"Spacematrix axes: gsi 0..{xmax}, fsi 0..{ymax}; smallest L of the blocks with buildings: {blocks_raw['l'].min():.3f}")
    for O in (1, 2, 4):
        x0 = max(0.0, 1 - O * ymax)
        print(f"  OSR={O}: gsi={x0:.2f} -> fsi {(1 - x0) / O:.3f}; gsi={xmax:.2f} -> fsi {(1 - xmax) / O:.3f}")
    assert blocks_raw["l"].dropna().min() >= 1
    return "".join(s)


T["density"] = f"""
<h2>Building density</h2>
<p>Map: <b>fsi</b>, floor space index = floor area of all official buildings / block area (floors from the register,
else height / {METRES_PER_FLOOR} m, else 1; {pct(N['floors_not_registry'])} of the buildings have no floors in the
register). The scale is clipped at the 95th percentile ({scale['fsi']:.2f}). Blocks without buildings are grey.</p>
<p>Chart: Spacematrix of the {num(len(gs))} blocks with buildings, coloured by land-use class.
<b>gsi</b> = footprint / block area; <b>L</b> = fsi / gsi, the mean number of floors; <b>OSR</b> = (1 &minus; gsi) / fsi,
open space per m&sup2; of floor area. Solid lines: constant L; dashed: constant OSR. Click a dot to find its block.</p>
<div class="chart">{scatter()}</div>
<p class="note">Large blocks are shown larger. A block with one small building has a very high OSR (up to
{num(emb['osr'].max())}); this is why OSR is not mapped.</p>
"""

T["access"] = f"""
<h2>Walking accessibility</h2>
<p>For each block: the <b>median walking time</b> from its point to all the other blocks, on the OpenStreetMap walking
network at {WALK_SPEED_KMH} km/h. City median {num(N['acc_med'], 1)} min; blocks range from {num(N['acc_min'], 1)} to
{num(N['acc_max'], 1)} min. The scale is clipped at the 98th percentile ({scale['acc'][1]:.0f} min).</p>
<p class="note">{WALK_SPEED_KMH} km/h is a conditional assumption. The block point is the representative point of the
block; in the large blocks it can fall in a forest.</p>
"""

w_rows = [[f"{t} min", num(walk[t]["children"]), pct(walk[t]["share"]), num(walk[t]["blocks"])] for t in THRESHOLDS]
p_rows = [[f"{t} min", f"{prov[t]['town']:.3f}", num(prov[t]["below_1"]) + " of " + num(prov[t]["blocks_with_children"])]
          for t in PROVISION]
T["schools"] = f"""
<h2>Schools</h2>
<p>The map shows what you choose:</p>
<div class="radios">
<label><input type="radio" name="schoolmode" value="time" checked> walking time to the nearest basic school</label>
{''.join(f'<label><input type="radio" name="schoolmode" value="{t}"> served within {t} min</label>' for t in PROVISION)}
</div>
<p><b>Basic schools</b> (red stars) are the two municipal schools of the main calculation; their places
({num(N['places'])}) are the pupils of grades 1-9 on 1 October 2026. Black triangles are other schools, shown for
information. The {num(N['children'])} children aged 7-15 of the census 2021 are distributed over the blocks in proportion
to the population. Walking time to the nearest basic school: median {num(N['t_med'], 1)} min, longest {num(N['t_max'], 1)} min
(block {N['t_max_block']}).</p>
<h3>Children within a walking time</h3>
{table(['Walking time', 'Children', 'Share of the children', 'Blocks'], w_rows)}
<p>The Basic Schools and Upper Secondary Schools Act (PGS &sect; 7 (3)) says, in short, that at least 80 % of the pupils
for whom a school is the home school must reach it within 60 minutes (paraphrase; it does not say how the way is made, here:
on foot). {pct(walk[60]['share'])} of the children are within 60 minutes of the nearest basic school.</p>
<h3>Provision with BlocksNet <code>competitive_provision</code></h3>
{table(['Threshold', 'Provision (strong), town', 'Blocks with children not fully served'], p_rows)}
<p class="note">The places are the pupils of 2026, not the capacity of the schools, so the result shows how the schools
are placed relative to the children, not whether there are enough places. Haapsalu Linna Algkool teaches grades 1-6
only. Some children go to schools outside the town or to the excluded schools.</p>
"""

kind_txt = ", ".join(f"{esc(k)} ({v})" for k, v in top_kinds.items())
T["q2"] = f"""
<h2>Q2: official buildings in OpenStreetMap</h2>
<p>What is missing or outdated in OpenStreetMap when compared with the official building data? A pair is an official
and an OSM building whose overlap is more than 50 % of the smaller one. Only numbers here.</p>
<div class="cards">
{card(num(N['off_un']), 'official buildings without an OSM pair (of ' + num(N['off']) + ')')}
{card(num(N['osm_un']), 'OSM buildings without an official pair (of ' + num(N['osm']) + ')')}
{card(pct(N['floors_off']), 'official buildings with floors in the register')}
{card(pct(N['levels_osm']), 'OSM buildings with building:levels')}
</div>
<div class="radios">
<label><input type="checkbox" data-q2="official" checked> <i class="dot" style="background:{Q2_COLOURS['official']}"></i>
official, no OSM pair ({num(N['off_un'])})</label>
<label><input type="checkbox" data-q2="osm" checked> <i class="dot" style="background:{Q2_COLOURS['osm']}"></i>
OSM, no official pair ({num(N['osm_un'] - N['osm_un_absent'])})</label>
<label><input type="checkbox" data-q2="absent" checked> <i class="dot" style="background:{Q2_COLOURS['absent']}"></i>
OSM, <b>possibly demolished, not verified</b> ({num(N['osm_un_absent'])})</label>
</div>
<p>Block colour: share of the official buildings that have an OSM pair (scale from 0.5; blocks without official buildings
are grey). The largest groups of official buildings without a pair by type: {kind_txt}.</p>
<p>The {num(N['osm_un_absent'])} OSM buildings in magenta carry a <code>maaamet:ETAK</code> id that is in no building of the
current official data; whether they were demolished was not verified. Of the other OSM buildings without a pair,
{num(N['osm_un_notag'])} have no such tag and {num(N['osm_un_town'])} have an id of a building of the official town layer
whose outline does not pair. Sum over the blocks: {num(N['off_un_blocks'])} official and {num(N['osm_un_blocks'])} OSM
buildings ({num(N['osm_un'] - N['osm_un_blocks'])} OSM building outside all blocks).</p>
<p class="note">OSM and the official data are not independent: OSM buildings often carry the official ETAK id
(<code>PLAN.md</code> has the counts).</p>
"""

T["methods"] = f"""
<h2>Methods &amp; limitations</h2>
<h3>Method</h3>
<ul>
<li><b>Blocks.</b> BlocksNet <code>cut_urban_blocks</code> from OSM roads (BlocksNet road types plus
<code>highway=service</code>; no footways or paths) and water. Railways are not used. Islands and slivers without
buildings are dropped; blocks over {LARGE_BLOCK_LABEL_KM2} km&sup2; are marked.</li>
<li><b>Buildings</b> come from the official ETAK + Building Register layer and from OSM; a building belongs to the block
that contains its inside point and is not cut.</li>
<li><b>Floors:</b> register value, else height / {METRES_PER_FLOOR} m (conditional), else 1.</li>
<li><b>Population:</b> census 2021 total distributed by registry net area of dwellings.</li>
<li><b>Land use:</b> cadastral purpose, class with the largest area share.</li>
<li><b>Accessibility:</b> OSM walking network (cycleways without a <code>foot</code> tag are assumed walkable),
{WALK_SPEED_KMH} km/h, shortest of parallel edges; the matrix is stored as <code>float16</code>.</li>
<li><b>Schools:</b> EHIS schools inside the town; demand = children 7-15 distributed by population; BlocksNet
<code>competitive_provision</code> with thresholds of {', '.join(str(t) for t in PROVISION)} minutes.</li>
<li><b>Q2:</b> pairing by overlap above 50 % of the smaller building.</li>
</ul>
<h3>Limitations</h3>
<ul>
<li>{WALK_SPEED_KMH} km/h and {METRES_PER_FLOOR} m per floor are assumptions, not norms.</li>
<li>The block point is snapped to the nearest node of the walking network; for a few blocks the choice of the node
changes times by minutes. A few blocks are far from the nearest node of the network.</li>
<li>Large blocks: the block point can lie in a forest.</li>
<li>Land use is legal (cadastre), not actual.</li>
<li>Population per block is a distributed total; the census is from 2021 and the pupils from 2026.</li>
<li>Places of the schools are the pupils, not the capacity; the age of children by block is unknown.</li>
<li>The buildings of the register and OSM are of different dates (OSM was downloaded
{esc(dates['osm'])}, official buildings {esc(dates['etak_ehr_hooned'])}).</li>
<li>The basemap is informative and unofficial (Maa- ja Ruumiamet); it is not part of the analysis.</li>
</ul>
<p class="note">The full list with numbers is in <code>PLAN.md</code> in the repository.</p>
"""

T["sources"] = f"""
<h2>Data sources &amp; credits</h2>
<p>Details, URLs, licences and download dates of every layer are in <code>data/SOURCES.md</code>.</p>
<ul>
<li><b>OpenStreetMap</b>: roads, water, buildings and schools, &copy; OpenStreetMap contributors,
<a href="https://www.openstreetmap.org/copyright">ODbL</a> (downloaded {esc(dates['osm'])}; roads
{esc(dates['osm_roads'])}).</li>
<li><b>Maa- ja Ruumiamet</b> (Land and Spatial Development Board): settlement boundary (EHAK) and ETAK buildings with
Building Register data, under the
<a href="https://geoportaal.maaruum.ee/opendata-licence">opendata licence</a> of 01.01.2025. <i>ETAK buildings with EHR
data and EHAK settlement boundary: Republic of Estonia Land and Spatial Development Board, extract
{esc(dates['etak_ehr_hooned'][8:10])}.{esc(dates['etak_ehr_hooned'][5:7])}.{esc(dates['etak_ehr_hooned'][:4])}.</i></li>
<li><b>Cadastral parcels</b> (land-use purpose): Maa- ja Ruumiamet cadastre WFS, <a
href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, attributed to the Estonian Ministry of Economic
Affairs and Communications (downloaded {esc(dates['cadastre'])}).</li>
<li><b>Statistics Estonia</b>: census 2021 (RL21003, RL21218, RL21807), <a
href="https://creativecommons.org/licenses/by-sa/4.0/deed.en">CC BY-SA 4.0</a> (downloaded {esc(dates['statistics'])}).</li>
<li><b>EHIS</b> (Estonian Education Information System) open data: school buildings and student numbers (downloaded
{esc(dates['ehis'])}). The licence of the student numbers is not stated on the pages checked.</li>
<li><b>Basemap</b>: Aluskaart (hallkaart), Maa- ja Ruumiamet {BASEMAP_YEAR}; tiles are loaded live from the
Land and Spatial Development Board. <a href="{esc(TERMS_URL)}">Terms of the map services</a> (in Estonian;
quoted in <code>data/SOURCES.md</code>). The map is informative and unofficial.</li>
<li><b>Leaflet</b> 1.9.4, &copy; Volodymyr Agafonkin and CloudMade, BSD 2-Clause licence (embedded in this file with
its licence).</li>
</ul>
<h3>Credits</h3>
<p><a href="https://github.com/aimclub/blocksnet">BlocksNet</a> (version 1.0.0a9, BSD-3-Clause), developed by the
Institute of Design and Urban Studies (IDU), ITMO University; installed as a dependency, no code is copied.
Publication listed by its authors: Churiakova T., Starikov V., Sudakova V., Morozov A., Mityagin S.,
<a href="https://link.springer.com/chapter/10.1007/978-3-031-48855-9_4">Digital Master Plan as a tool for generating
territory development requirements</a>, ARTIIS 2023.</p>
<p>Based on practice 2 of the ITMO University course &laquo;Технологии ИИ в урбанистике&raquo; (AI Technologies in
Urban Studies).</p>
<p>Licences: code under MIT; the terms of each data file are in <a href="{REPO_URL}/blob/main/data/LICENSE.md"><code>data/LICENSE.md</code></a> in the repository.</p>
<p>Code written with the assistance of Claude Code (AI coding agent); research questions, data choices and decisions by the author.</p>
"""

n_bad = len(checks) - n_ok
taken_rows = [
    ["Pairs of blocks faster by more than 2 min with the cycleways", f"{num(nbnum['cycleway_pairs_faster_over_2min'])} of {num(nbnum['cycleway_pairs'])} ({pct(nbnum['cycleway_share_faster_over_2min'])})", "Key findings"],
    ["Vacant dwelling area, census 2021 (RL21218)", f"{num(stats['vacant_dwelling_area_m2_2021_haapsalu_linn'])} of {num(stats['all_dwelling_area_m2_2021_haapsalu_linn'])} m² ({pct(vacant_share, 0)})", "Key findings"],
    ["Population from net dwelling area / from footprint × floors", f"{num(popcheck['population_net'])} / {num(popcheck['population_gross'])} people", "Population, Key findings"],
]
chk_rows = [[esc(c["name"]), c["nb"], c["dash"], "OK" if c["ok"] else "<b>DIFFERENT</b>"] for c in checks]
T["checks"] = f"""
<h2>Checks</h2>
<p>Each indicator is calculated in the notebook (<code>data/notebook_numbers.json</code>) and again by
<code>build_dashboard.py</code> from the data embedded in this page. <b>{n_ok} of {len(checks)} agree</b>{'' if n_bad == 0 else f'; <b>{n_bad} differ</b>'}.</p>
{table(['Indicator', 'Notebook', 'Dashboard', 'Result'], chk_rows, 'checks')}
<h3>Numbers taken from the notebook (not recalculated here)</h3>
{table(['Number', 'Value', 'Used in'], taken_rows)}
<p class="note">To re-run: execute <code>notebook.ipynb</code> (it rewrites <code>data/</code>), then
<code>python build_dashboard.py</code>.</p>
"""

TAB_ORDER = [("overview", "Overview"), ("landuse", "Land use"), ("population", "Population"),
             ("density", "Density"), ("access", "Accessibility"), ("schools", "Schools"),
             ("q2", "Q2: OSM vs official"), ("methods", "Methods & limitations"), ("sources", "Data & credits"),
             ("checks", "Checks")]

config = dict(tiles=TILES, attribution=f"Aluskaart: Maa- ja Ruumiamet {BASEMAP_YEAR}", landColours=LAND_COLOURS,
              q2Colours=Q2_COLOURS, scale=scale, tabs=TAB_ORDER, kinds=kinds, thresholds=list(PROVISION), noMap=list(NO_MAP_TABS))
data_json = json.dumps({"config": config, "blocks": blocks_fc, "boundary": boundary_fc, "schools": schools_fc,
                        "points": points, "text": T}, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
data_json = data_json.replace("</", "<\\/")

# ---------------------------------------------------------------- page

CSS = """
:root{--bg:#fafaf8;--fg:#1d1f24;--mut:#5b6068;--line:#d9d9d4;--card:#fff;--acc:#1b4f9c;--tab:#eceae4}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17191d;--fg:#e6e6e3;--mut:#a3a7ad;--line:#33363c;--card:#1f2227;--acc:#7fb0ff;--tab:#2a2d33}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
#app{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(340px,.8fr);grid-template-rows:auto 1fr;height:100vh}
header{grid-column:1/3;padding:10px 16px 0;border-bottom:1px solid var(--line)}
header h1{font-size:17px;margin:0 0 8px}
.by{color:var(--mut);font-size:12px;font-weight:400}h1 .by{margin-left:6px}
ul.kf{margin:4px 0 12px;padding-left:20px}ul.kf li{margin:3px 0}h3.kf{margin-top:8px}
nav{display:flex;flex-wrap:wrap;gap:4px;padding-bottom:8px}
nav button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--tab);color:var(--fg);border-radius:6px;padding:4px 10px;cursor:pointer}
nav button[aria-selected=true]{background:var(--acc);border-color:var(--acc);color:#fff}
#map{min-height:0;background:#e9eef2}
#panel{overflow:auto;padding:12px 18px 40px;border-left:1px solid var(--line)}
#panel h2{font-size:19px;margin:6px 0 8px}#panel h3{font-size:15px;margin:16px 0 6px}
a{color:var(--acc)}code{font-size:.9em}
.note{color:var(--mut);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:10px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.card b{display:block;font-size:20px}.card span{font-size:12.5px;color:var(--mut)}
.tw{overflow-x:auto;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
td:not(:first-child),th:not(:first-child){text-align:right}table.checks td:last-child{text-align:left}
.radios{display:flex;flex-direction:column;gap:3px;margin:8px 0;font-size:14px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:3px}
.chart svg{width:100%;height:auto;max-width:560px}
.chart .gr{stroke:var(--line);stroke-width:.6}.chart .tk,.chart .gt,.chart .ax{fill:var(--mut);font-size:10px}
.chart .gl{stroke:#888;stroke-width:1}.chart .go{stroke:#888;stroke-width:1;stroke-dasharray:4 3}
.chart .pt{stroke:#333;stroke-width:.6;cursor:pointer}.chart .pt:hover,.chart .pt:focus{stroke:#000;stroke-width:2}
.legend{background:rgba(255,255,255,.92);color:#1d1f24;padding:6px 9px;border-radius:6px;font-size:12px;line-height:1.35;max-width:230px}
.legend .bar{height:10px;width:180px;border:1px solid #888;margin:3px 0}.legend .sw{display:inline-block;width:12px;height:12px;margin-right:5px;vertical-align:-2px;border:1px solid #777}
.legend .row{white-space:nowrap}.legend .lr{display:flex;justify-content:space-between;width:180px}
.bm{background:rgba(255,255,255,.92);color:#1d1f24;padding:5px 8px;border-radius:6px;font-size:12px}
.bm label{display:block}
.leaflet-popup-content{font-size:13px;margin:10px 12px}.leaflet-popup-content table{font-size:12px}
#app.nomap{grid-template-columns:minmax(0,1fr)}
#app.nomap #map{display:none}
#app.nomap #panel{border-left:0;padding:12px clamp(16px,4vw,56px) 40px}
@media (max-width:799px){
#app{display:block;height:auto}
header{position:static}
#map{height:58vh}
#panel{border-left:0;overflow:visible;padding-bottom:60px}
}
"""

JS = r"""
(function(){
const D=JSON.parse(document.getElementById('data').textContent),C=D.config;
const LC=C.landColours,QC=C.q2Colours;
const SEQ={blue:['#ffffcc','#a1dab4','#41b6c4','#2c7fb8','#253494'],heat:['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026'],
rdylgn:['#d73027','#fdae61','#ffffbf','#a6d96a','#1a9850']};
const NA='#e2e2e2';
function hex(h){return [1,3,5].map(i=>parseInt(h.substr(i,2),16))}
function ramp(st,t){t=Math.max(0,Math.min(1,t));const k=t*(st.length-1),i=Math.min(st.length-2,Math.floor(k)),f=k-i,a=hex(st[i]),b=hex(st[i+1]);
return 'rgb('+a.map((x,j)=>Math.round(x+(b[j]-x)*f)).join(',')+')'}
function grad(st){return 'linear-gradient(to right,'+st.join(',')+')'}
const fmt={int:v=>v==null?'-':Math.round(v).toLocaleString('en'),f1:v=>v==null?'-':v.toFixed(1),f2:v=>v==null?'-':v.toFixed(2),f3:v=>v==null?'-':v.toFixed(3),
pct:v=>v==null?'-':(100*v).toFixed(1)+' %',osr:v=>v==null?'-':(v>100?'> 100':v.toFixed(2)),txt:v=>v==null?'-':v,yn:v=>v==null?'-':(v>=1?'yes':'no')};
const map=L.map('map',{preferCanvas:true,minZoom:8,maxZoom:19});
const tiles=L.tileLayer(C.tiles,{minZoom:8,maxNativeZoom:18,maxZoom:19,attribution:C.attribution});
tiles.addTo(map);
const bm=L.control({position:'topright'});
bm.onAdd=function(){const d=L.DomUtil.create('div','bm');
d.innerHTML='<b>Basemap</b><label><input type="radio" name="bm" value="on" checked> hallkaart</label><label><input type="radio" name="bm" value="off"> no basemap</label>';
L.DomEvent.disableClickPropagation(d);
d.addEventListener('change',e=>{if(e.target.value==='off'){map.removeLayer(tiles)}else{tiles.addTo(map);tiles.bringToBack()}});return d};
bm.addTo(map);
const boundary=L.geoJSON(D.boundary,{style:{color:'#222',weight:1.6,fill:false},interactive:false}).addTo(map);
let needFit=false;const byId={};let sel=null,cur='overview',state={school:'time',q2:{official:true,osm:true,absent:true}};
function base(p){return p.large_block?{color:'#1b4f9c',weight:2.6}:{color:'#6b6b6b',weight:.5}}
const T={
overview:{f:p=>({fillColor:'#2c7fb8',fillOpacity:.32}),leg:()=>'<div class="row"><span class="sw" style="background:#9cc5de"></span>urban block</div>'+largeLeg()},
landuse:{f:p=>({fillColor:LC[p.land_use_display]||NA,fillOpacity:.8}),
leg:()=>'<b>Land use (cadastral purpose)</b>'+Object.keys(LC).filter(k=>k!=='agriculture').map(k=>'<div class="row"><span class="sw" style="background:'+LC[k]+'"></span>'+k+'</div>').join('')+largeLeg(),
rows:[['Class','land_use_display','txt'],['Share of largest class','share','pct'],['Population','population_block','f1']]},
population:{f:p=>p.population_block>0?{fillColor:ramp(SEQ.blue,p.pph/C.scale.pph),fillOpacity:.85}:{fillColor:NA,fillOpacity:.5},
leg:()=>cbar('People per hectare',SEQ.blue,'0',Math.round(C.scale.pph)+'+')+nodata('no population')+largeLeg(),
rows:[['Population (distributed)','population_block','f1'],['People per hectare','pph','f1'],['Dwellings','n_dwellings','int'],['Area, m²','area_m2','int']]},
density:{f:p=>p.fsi>0?{fillColor:ramp(SEQ.blue,p.fsi/C.scale.fsi),fillOpacity:.85}:{fillColor:NA,fillOpacity:.5},
leg:()=>cbar('fsi (floor space index)',SEQ.blue,'0',C.scale.fsi.toFixed(2)+'+')+nodata('no buildings')+largeLeg(),
rows:[['fsi','fsi','f3'],['gsi','gsi','f3'],['L (mean floors)','l','f2'],['OSR','osr','osr'],['Official buildings','n_official_q2','int']]},
access:{f:p=>({fillColor:ramp(SEQ.heat,(p.median_accessibility-C.scale.acc[0])/(C.scale.acc[1]-C.scale.acc[0])),fillOpacity:.85}),
leg:()=>cbar('Median walking time to the other blocks, min',SEQ.heat,Math.round(C.scale.acc[0]),Math.round(C.scale.acc[1])+'+')+largeLeg(),
rows:[['Median walking time, min','median_accessibility','f1']]},
schools:{f:p=>{if(state.school==='time')return {fillColor:ramp(SEQ.heat,p.time_to_basic_school_min/C.scale.time),fillOpacity:.85};
const v=p['provision_strong_'+state.school];return v==null?{fillColor:NA,fillOpacity:.5}:{fillColor:v>=1?'#4daf4a':'#e41a1c',fillOpacity:.8}},
leg:()=>(state.school==='time'?cbar('Walking time to the nearest basic school, min',SEQ.heat,'0',Math.round(C.scale.time)+'+'):
'<b>Served within '+state.school+' min</b><div class="row"><span class="sw" style="background:#4daf4a"></span>children served</div><div class="row"><span class="sw" style="background:#e41a1c"></span>not served</div>'+nodata('no children'))+
'<div class="row">&#9733; basic school &nbsp; &#9650; other school</div>'+largeLeg(),
rows:[['Time to basic school, min','time_to_basic_school_min','f1'],['Time to gymnasium, min','time_to_gymnasium_min','f1'],['Children 7-15','children_7_15','int'],
['Served within 10 / 15 / 20 min',null,null]]},
q2:{f:p=>p.match_rate==null?{fillColor:NA,fillOpacity:.45}:{fillColor:ramp(SEQ.rdylgn,(p.match_rate-.5)/.5),fillOpacity:.65},
leg:()=>cbar('Share of official buildings with an OSM pair',SEQ.rdylgn,'0.5 or less','1')+nodata('no official buildings')+
['official|official, no OSM pair','osm|OSM, no official pair','absent|OSM, possibly demolished, not verified'].map(s=>{const a=s.split('|');
return '<div class="row"><span class="sw" style="border-radius:50%;background:'+QC[a[0]]+'"></span>'+a[1]+'</div>'}).join('')+largeLeg(),
rows:[['Match rate','match_rate','pct'],['Official buildings','n_official_q2','int'],['Official without pair','n_official_unmatched','int'],
['OSM buildings','n_osm_q2','int'],['OSM without pair','n_osm_unmatched','int'],['Floors in register','floors_coverage_official','pct']]}
};
['methods','sources','checks'].forEach(k=>T[k]={f:p=>({fillColor:'#2c7fb8',fillOpacity:.32}),leg:()=>'',rows:[['Population (distributed)','population_block','f1'],['Area, m²','area_m2','int']]});
T.overview.rows=T.landuse.rows;
function cbar(t,st,a,b){return '<b>'+t+'</b><div class="bar" style="background:'+grad(st)+'"></div><div class="lr"><span>'+a+'</span><span>'+b+'</span></div>'}
function nodata(t){return '<div class="row"><span class="sw" style="background:'+NA+'"></span>'+t+'</div>'}
function largeLeg(){return '<div class="row"><span class="sw" style="background:#fff;border:2px solid #1b4f9c"></span>large block</div>'}
function popup(p){const rows=(T[cur].rows||[]).map(r=>{if(r[1]===null)return '<tr><td>'+r[0]+'</td><td>'+[10,15,20].map(t=>{const v=p['provision_strong_'+t];return v==null?'-':(v>=1?'yes':'no')}).join(' / ')+'</td></tr>';
return '<tr><td>'+r[0]+'</td><td style="text-align:right">'+fmt[r[2]](p[r[1]])+'</td></tr>'}).join('');
return '<b>Block '+p.block_id+'</b>'+(p.large_block?' (large block)':'')+'<table>'+rows+'</table>'}
const blocks=L.geoJSON(D.blocks,{style:f=>Object.assign({fillOpacity:.5},base(f.properties),T[cur].f(f.properties)),
onEachFeature:(f,l)=>{byId[f.properties.block_id]=l;l.on('click',()=>{select(f.properties.block_id,false)})}}).addTo(map);
function restyle(){blocks.setStyle(f=>Object.assign({},base(f.properties),T[cur].f(f.properties)));if(sel){byId[sel].setStyle({color:'#000',weight:3.2});byId[sel].bringToFront()}}
function select(id,zoom){sel=id;restyle();const l=byId[id];l.bindPopup(popup(l.feature.properties)).openPopup(l.getBounds().getCenter());
l.on('popupclose',()=>{if(sel===id){sel=null;restyle()}});if(zoom)map.fitBounds(l.getBounds(),{maxZoom:17,padding:[40,40]})}
const sch=L.layerGroup(),q2g={official:L.layerGroup(),osm:L.layerGroup(),absent:L.layerGroup()};
L.geoJSON(D.schools,{pointToLayer:(f,ll)=>L.marker(ll,{icon:L.divIcon({className:'',iconSize:[22,22],iconAnchor:[11,11],
html:'<div style="font-size:'+(f.properties.basic?24:15)+'px;line-height:22px;text-align:center;color:'+(f.properties.basic?'#d73027':'#111')+';text-shadow:0 0 3px #fff,0 0 3px #fff">'+(f.properties.basic?'&#9733;':'&#9650;')+'</div>'})}).bindPopup('<b>'+f.properties.name+'</b><br>'+f.properties.kind+'<br>Pupils 2026: '+f.properties.students+'<br>'+f.properties.address)}).addTo(sch);
const kindsList=C.kinds,stTxt={no_osm_pair:'no OSM pair',no_etak_tag:'no maaamet:ETAK tag',etak_id_in_town_layer:'ETAK id is in the official town layer',etak_id_in_bbox_only:'ETAK id only outside the town',
absent_from_official_data:'ETAK id is in no official building: possibly demolished, not verified'};
const cvs=L.canvas({padding:.5});
D.points.forEach(p=>{L.circleMarker([p[1],p[0]],{renderer:cvs,radius:p[2]==='absent'?6:4.5,color:'#fff',weight:1,fillColor:QC[p[2]],fillOpacity:.95})
.bindPopup('<b>'+(p[2]==='official'?'Official':'OSM')+' building '+p[5]+'</b><br>'+kindsList[p[3]]+'<br>'+stTxt[p[4]]).addTo(q2g[p[2]])});
const leg=L.control({position:'bottomleft'});leg.onAdd=function(){this._d=L.DomUtil.create('div','legend');return this._d};leg.addTo(map);
const panel=document.getElementById('panel'),nav=document.getElementById('tabs');
C.tabs.forEach(t=>{const b=document.createElement('button');b.type='button';b.textContent=t[1];b.dataset.id=t[0];b.setAttribute('role','tab');nav.appendChild(b)});
nav.addEventListener('click',e=>{if(e.target.dataset.id)show(e.target.dataset.id)});
function show(id){cur=id;sel=null;map.closePopup();[...nav.children].forEach(b=>b.setAttribute('aria-selected',b.dataset.id===id));
const nm=C.noMap.indexOf(id)>=0;document.getElementById('app').classList.toggle('nomap',nm);if(!nm){map.invalidateSize();if(needFit)fit()}panel.innerHTML=D.text[id];panel.scrollTop=0;
map[id==='schools'?'addLayer':'removeLayer'](sch);Object.keys(q2g).forEach(k=>{map[id==='q2'&&state.q2[k]?'addLayer':'removeLayer'](q2g[k])});
if(id==='schools'){const r=panel.querySelector('input[name=schoolmode][value="'+state.school+'"]');if(r)r.checked=true}
if(id==='q2')panel.querySelectorAll('input[data-q2]').forEach(c=>c.checked=state.q2[c.dataset.q2]);
restyle();leg._d.innerHTML=T[id].leg();try{history.replaceState(null,'','#'+id)}catch(e){}}
panel.addEventListener('change',e=>{const t=e.target;
if(t.name==='schoolmode'){state.school=t.value;restyle();leg._d.innerHTML=T.schools.leg()}
if(t.dataset.q2){state.q2[t.dataset.q2]=t.checked;map[t.checked?'addLayer':'removeLayer'](q2g[t.dataset.q2])}});
panel.addEventListener('click',e=>{const c=e.target.closest&&e.target.closest('.pt');if(c)select(+c.dataset.id,true)});
panel.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('pt')){e.preventDefault();select(+e.target.dataset.id,true)}});
const h=(location.hash||'').slice(1);show(D.text[h]?h:'overview');
function fit(){const m=document.getElementById('map');if(!m.offsetWidth){needFit=true;return}needFit=false;map.invalidateSize();map.fitBounds(boundary.getBounds(),{padding:[10,10]})}
fit();window.addEventListener('load',fit);
window.addEventListener('hashchange',()=>{const k=(location.hash||'').slice(1);if(D.text[k]&&k!==cur)show(k)});
})();
"""

leaflet_js = (LEAFLET / "leaflet.js").read_text(encoding="utf-8")
leaflet_css = (LEAFLET / "leaflet.css").read_text(encoding="utf-8")
leaflet_licence = (LEAFLET / "LICENSE").read_text(encoding="utf-8").strip()
assert "</script" not in leaflet_js and "-->" not in leaflet_licence and "--" not in leaflet_licence

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Haapsalu urban blocks</title>
<meta name="description" content="Urban blocks of Haapsalu (Estonia): land use, population, density, walking accessibility, schools and OSM vs official buildings.">
<!--
Leaflet 1.9.4, https://leafletjs.com (embedded below, unmodified)

{leaflet_licence}
-->
<style>
{leaflet_css}
</style>
<style>
{CSS}
</style>
</head>
<body>
<div id="app">
<header><h1>Haapsalu urban blocks <small class="by">{esc(AUTHOR_LINE)}<a href="{REPO_URL}">{REPO_URL}</a></small></h1><nav id="tabs" role="tablist" aria-label="Sections"></nav></header>
<div id="map" aria-label="Map of the urban blocks"></div>
<main id="panel" tabindex="-1"></main>
</div>
<script id="data" type="application/json">{data_json}</script>
<script>
{leaflet_js}
</script>
<script>
{JS}
</script>
</body>
</html>
"""

readme = ROOT / "README.md"
r = readme.read_text(encoding="utf-8")
a, z = "<!-- key-findings:start -->", "<!-- key-findings:end -->"
assert r.count(a) == 1 and r.count(z) == 1
block = a + "\n" + "\n".join(f"- {x}" for x in FINDINGS) + "\n" + z
r = r[:r.index(a)] + block + r[r.index(z) + len(z):]
readme.write_text(r, encoding="utf-8")

out = ROOT / "dashboard.html"
out.write_text(page, encoding="utf-8")
docs = ROOT / "docs"
docs.mkdir(exist_ok=True)
shutil.copyfile(out, docs / "index.html")
(docs / ".nojekyll").write_text("", encoding="utf-8")

print(f"dashboard.html: {out.stat().st_size:,} bytes (data {len(data_json):,}, leaflet js+css {len(leaflet_js) + len(leaflet_css):,})")
print(f"Checks: {n_ok} of {len(checks)} agree")
w = max(len(c["name"]) for c in checks)
for c in checks:
    print(f"  {'OK       ' if c['ok'] else 'DIFFERENT'} {c['name']:<{w}}  notebook {c['nb']:>8}  dashboard {c['dash']:>8}")
if not mixed_ok:
    print("WARNING: land_use_display 'mixed' does not follow share < 0.5 everywhere")
sys.exit(0 if n_ok == len(checks) else 1)
