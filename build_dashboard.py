"""Build dashboard.html (and its copy docs/index.html) from the saved results in data/.

One self-contained HTML file: Leaflet 1.9.4 (vendor/leaflet-1.9.4), the block data and all texts are inside it.
Only the basemap tiles are requested live by the browser. Every number in the texts is calculated here from the
files in data/; the table in the section "Checks" compares them with data/notebook_numbers.json written by the notebook.

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
cols = {"block_id": 0, "area_m2": 0, "land_use_display": None, "share": 3, "population_block": 4, "pph": 1,
        "gsi": 5, "fsi": 5, "l": 4, "osr": 3, "mxi": 4, "morphotype_spacematrix": None,
        "spacematrix_cluster": None, "morphotype_strelka": None, "median_accessibility": 4, "time_to_basic_school_min": 4,
        "time_to_gymnasium_min": 4, "children_7_15": 0, "provision_strong_10": 3, "provision_strong_15": 3,
        "provision_strong_20": 3, "match_rate": 3, "n_official_unmatched": 0, "n_osm_unmatched": 0,
        "n_official_q2": 0, "n_osm_q2": 0, "floors_coverage_official": 2, "large_block": None, "built_up": None,
        "n_dwellings": 0, "geometry": None}
b["spacematrix_cluster"] = b["spacematrix_cluster"].astype("Int64")
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

reg = emb[emb["large_block"] == 0]  # blocks without the large blocks
IND = [("population_block", "Population (people, distributed)"), ("gsi", "gsi"), ("fsi", "fsi"), ("l", "l (mean floors)"),
       ("osr", "osr"), ("mxi", "mxi"), ("median_accessibility", "Median walking time to other blocks, min"),
       ("time_to_basic_school_min", "Time to nearest basic school, min")]


def summ(df, m):
    x = df[m]
    return dict(n=int(x.notna().sum()), mean=float(x.mean()), median=float(x.median()), min=float(x.min()),
                max=float(x.max()), missing=int(x.isna().sum()))


def fmt_summ(d):
    return f"{d['n']} / {d['mean']:,.2f} / {d['median']:,.2f} / {d['min']:,.2f} / {d['max']:,.2f}"


for m, label in IND:
    chk(f"{label}: N / mean / median / min / max (without large blocks)", nbnum["summary_without_large"][m], summ(reg, m), fmt_summ)
sm_counts = emb["morphotype_spacematrix"].value_counts().sort_index()
st_counts = emb["morphotype_strelka"].value_counts().sort_index()
assert set(sm_counts.index) == set(nbnum["morphotype_spacematrix_counts"]) and set(st_counts.index) == set(nbnum["morphotype_strelka_counts"])
for name, c in nbnum["morphotype_spacematrix_counts"].items():
    chk(f"Spacematrix morphotype: {name}", c, int(sm_counts[name]), i0)
for name, c in nbnum["morphotype_strelka_counts"].items():
    chk(f"Strelka morphotype: {name}", c, int(st_counts[name]), i0)
chk("Spacematrix clusters", nbnum["spacematrix_clusters"], int(emb["spacematrix_cluster"].nunique()), i0)
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

# ---------------------------------------------------------------- texts of the page


def card(value, label):
    return f'<div class="card"><b>{value}</b><span>{esc(label)}</span></div>'


def table(head, rows, cls=""):
    h = "".join(f"<th>{esc(x)}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table></div>'


T = {}

lu_rows = [[esc(k), num(int(r.blocks)), num(r["pop"]), pct(r["pop"] / N["pop"]),
            num(r.area / 1e6, 2)] for k, r in lu.iterrows()]



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




def hist_svg(vals, xlabel, bins=12):
    vals = np.asarray(vals, dtype=float)
    cnt, edges = np.histogram(vals, bins=bins)
    W, H, ml, mr, mt, mb = 420, 190, 36, 8, 10, 38
    ymax = int(cnt.max())
    px = lambda x: ml + (W - ml - mr) * (x - edges[0]) / (edges[-1] - edges[0])
    py = lambda y: H - mb - (H - mt - mb) * y / ymax
    s_ = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Histogram of {esc(xlabel)}">']
    for y in (0, ymax):
        s_.append(f'<line class="gr" x1="{ml}" y1="{py(y):.1f}" x2="{W - mr}" y2="{py(y):.1f}"/>'
                  f'<text class="tk" x="{ml - 5}" y="{py(y) + 4:.1f}" text-anchor="end">{y}</text>')
    for c, a, b2 in zip(cnt, edges[:-1], edges[1:]):
        s_.append(f'<rect class="bar" x="{px(a) + 0.5:.1f}" y="{py(c):.1f}" width="{px(b2) - px(a) - 1:.1f}" '
                  f'height="{py(0) - py(c):.1f}"><title>{a:.2f} to {b2:.2f}: {int(c)} blocks</title></rect>')
    for t in np.linspace(edges[0], edges[-1], 5):
        s_.append(f'<text class="tk" x="{px(t):.1f}" y="{H - mb + 14}" text-anchor="middle">{t:.2f}</text>')
    s_.append(f'<text class="ax" x="{(ml + W - mr) / 2:.0f}" y="{H - 6}" text-anchor="middle">{esc(xlabel)}</text>'
              f'<text class="ax" transform="translate(10 {(mt + H - mb) / 2:.0f}) rotate(-90)" text-anchor="middle">blocks</text></svg>')
    return "".join(s_)


def bars_svg(items, w=420, dec=0, aria="Bar chart"):
    """items: (label, value, fill colour or None, block id or None); label above its bar."""
    rh, ml, mr = 30, 4, 46
    vmax = max(v for _, v, _, _ in items) or 1
    s_ = [f'<svg viewBox="0 0 {w} {rh * len(items) + 4}" role="img" aria-label="{esc(aria)}">']
    for i, (label, v, fill, bid) in enumerate(items):
        y = 2 + i * rh
        bw = (w - ml - mr) * v / vmax
        extra = f' data-id="{bid}" tabindex="0"' if bid else ""
        style = f' style="fill:{fill}"' if fill else ""
        s_.append(f'<text class="bl" x="{ml}" y="{y + 11}">{esc(label)}</text>'
                  f'<rect class="bar{" pt" if bid else ""}" x="{ml}" y="{y + 15}" width="{bw:.1f}" height="10"{style}{extra}>'
                  f'<title>{esc(label)}: {v:,.{dec}f}</title></rect>'
                  f'<text class="bv" x="{ml + bw + 4:.1f}" y="{y + 24}">{v:,.{dec}f}</text>')
    s_.append("</svg>")
    return "".join(s_)


top10 = emb.nlargest(10, "population_block")
top_ids = [int(x) for x in top10["block_id"]]
sm_name_clusters = emb[emb["spacematrix_cluster"].notna()].groupby("morphotype_spacematrix")["spacematrix_cluster"].nunique()
dup_names = [f"{k} ({v} groups)" for k, v in sm_name_clusters.items() if v > 1]
top_items = [(f"Block {r.block_id} \u00b7 {r.land_use_display}" + (" \u00b7 large block" if r.large_block else ""), float(r.population_block), None, int(r.block_id)) for r in top10.itertuples()]
DISP = {"gsi": "gsi (share of block covered by buildings)", "fsi": "fsi (floor space index)", "l": "l (average number of floors)",
        "osr": "osr (open space ratio)", "mxi": "mxi (housing share of floor area)"}
sum_rows = []
for m, label in IND:
    d = summ(reg, m)
    sum_rows.append([esc(DISP.get(m, label)), num(d["n"]), num(d["mean"], 2), num(d["median"], 2), num(d["min"], 2), num(d["max"], 2), num(d["missing"])])
big_rows = [[str(int(r.block_id)), num(r.area_m2 / 1e6, 2)] + [("-" if pd.isna(getattr(r, m)) else num(getattr(r, m), 2)) for m, _ in IND]
            for r in emb[emb["large_block"] == 1].itertuples()]
n_dev = int((emb["fsi"] > 0).sum())



w_rows = [[f"{t} min", num(walk[t]["children"]), pct(walk[t]["share"]), num(walk[t]["blocks"])] for t in THRESHOLDS]
p_rows = [[f"{t} min", f"{prov[t]['town']:.3f}", num(prov[t]["below_1"]) + " of " + num(prov[t]["blocks_with_children"])]
          for t in PROVISION]

kind_txt = ", ".join(f"{esc(k)} ({v})" for k, v in top_kinds.items())

T["methods"] = f"""
<h2>Methods &amp; limitations</h2>
<h3>How it was made</h3>
<ul>
<li><b>Blocks.</b> We cut the town into urban blocks along roads and water from OpenStreetMap (OSM). Streets and service roads count;
footpaths and railways do not. Islands and tiny slivers without buildings are dropped. Blocks over {LARGE_BLOCK_LABEL_KM2} km&sup2; are marked as large.</li>
<li><b>Buildings</b> come from two sources: the official building layer (Estonian Topographic Database, ETAK, with the Building Register) and OSM.
A building belongs to the block that contains its centre point.</li>
<li><b>Floors.</b> The number of floors comes from the register. If it is missing we use the height divided by {METRES_PER_FLOOR} m, and if there is no height, one floor.</li>
<li><b>Population.</b> The 2021 census total is shared between the blocks by the floor area of their residential buildings.</li>
<li><b>Land use.</b> The class that covers most of the land of the block, from the cadastre.</li>
<li><b>Walking time.</b> Along the OSM walking network at {WALK_SPEED_KMH} km/h. Cycleways without a note about pedestrians are treated as walkable.</li>
<li><b>Schools.</b> The school buildings of the Estonian Education Information System (EHIS) inside the town. The children aged 7&ndash;15 are shared
between the blocks by population. Provision is calculated for walking limits of {PROVISION[0]}, {PROVISION[1]} and {PROVISION[2]} minutes.</li>
<li><b>Housing share and morphotypes.</b> MXI is the share of the floor area that is housing. BlocksNet groups blocks by floors, density and
housing share and gives each group a name (Spacematrix), and also sorts blocks into types by fixed rules (Strelka).</li>
<li><b>OSM vs official.</b> A building in one source is matched with a building in the other if they overlap by more than half of the smaller one.</li>
</ul>
<h3>Limitations</h3>
<ul>
<li>{WALK_SPEED_KMH} km/h and {METRES_PER_FLOOR} m per floor are assumptions, not standards.</li>
<li>A building counts as housing as a whole. A shop on the ground floor does not lower MXI; sheds and garages count as non-housing and do lower it.</li>
<li>The names and thresholds of the morphotypes come from BlocksNet, not from us. Different groups can have the same name.</li>
<li>Each block is one point on the walking network. For a few blocks another choice of point would change the time by a few minutes,
and a few blocks lie far from the network. In the large blocks the point can be in a forest.</li>
<li>Land use is what the cadastre allows, not what is really there.</li>
<li>People per block are a share of the town total. The census is from 2021 and the pupils from 2026.</li>
<li>School places are the pupils, not the real capacity. The ages of the children in each block are not known.</li>
<li>Both building sources were downloaded on {esc(dates['etak_ehr_hooned'])}, but each is updated on its own schedule: OSM by volunteers at any time, the register by the state.</li>
<li>The basemap is for orientation only (Maa- ja Ruumiamet); it is not part of the analysis.</li>
</ul>
<p class="tech">Technical note: BlocksNet 1.0.0a9; Spacematrix uses KMeans with {nbnum['morphotype_params']['spacematrix_n_clusters']} clusters,
random_state {nbnum['morphotype_params']['spacematrix_random_state']}, scikit-learn {esc(nbnum['morphotype_params']['scikit_learn'])}.
The full list with numbers is in <code>PLAN.md</code> in the repository.</p>
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
    ["MXI of the town (living / all floor area, gross)", f"{nbnum['mxi_town']:.3f}", "Charts, Methods"],
    ["Pairs of blocks faster by more than 2 min with the cycleways", f"{num(nbnum['cycleway_pairs_faster_over_2min'])} of {num(nbnum['cycleway_pairs'])} ({pct(nbnum['cycleway_share_faster_over_2min'])})", "Key findings"],
    ["Vacant dwelling area, census 2021 (RL21218)", f"{num(stats['vacant_dwelling_area_m2_2021_haapsalu_linn'])} of {num(stats['all_dwelling_area_m2_2021_haapsalu_linn'])} m² ({pct(vacant_share, 0)})", "Key findings"],
    ["Population from net floor area of residential buildings / from footprint × floors", f"{num(popcheck['population_net'])} / {num(popcheck['population_gross'])} people", "Population, Key findings"],
]
chk_rows = [[esc(c["name"]), c["nb"], c["dash"], "OK" if c["ok"] else "<b>DIFFERENT</b>"] for c in checks]
T["checks"] = f"""
<h2>Checks</h2>
<p>Every number on this page is calculated twice: once in the analysis notebook and once when this page is built. The table puts the two side by side.
<b>{n_ok} of {len(checks)} rows agree</b>{'' if n_bad == 0 else f'; <b>{n_bad} differ</b>'}.</p>
{table(['Indicator', 'Notebook', 'Dashboard', 'Result'], chk_rows, 'checks')}
<h3>Numbers read from the notebook (not recalculated here)</h3>
{table(['Number', 'Value', 'Used in'], taken_rows)}
<p class="tech">Technical note: the notebook values are in <code>data/notebook_numbers.json</code>. To re-run, execute <code>notebook.ipynb</code>
(it rewrites <code>data/</code>), then <code>python build_dashboard.py</code>.</p>
"""

leaflet_js = (LEAFLET / "leaflet.js").read_text(encoding="utf-8")
leaflet_css = (LEAFLET / "leaflet.css").read_text(encoding="utf-8")
leaflet_licence = (LEAFLET / "LICENSE").read_text(encoding="utf-8").strip()
assert "</script" not in leaflet_js and "-->" not in leaflet_licence and "--" not in leaflet_licence

readme = ROOT / "README.md"
r = readme.read_text(encoding="utf-8")
a, z = "<!-- key-findings:start -->", "<!-- key-findings:end -->"
assert r.count(a) == 1 and r.count(z) == 1
block = a + "\n" + "\n".join(f"- {x}" for x in FINDINGS) + "\n" + z
r = r[:r.index(a)] + block + r[r.index(z) + len(z):]
readme.write_text(r, encoding="utf-8")

# ---------------------------------------------------------------- the page: one sticky map, sections scroll and drive it
import re
import base64
import urllib.parse

# Colours of this page only (the old dashboard.html was written above with its own colours)
LAND_COLOURS.update({"residential": "#E5B25D", "business": "#E8604C", "industrial": "#7C5E99", "transport": "#8C97A3",
                     "recreation": "#5FA88A", "special": "#2A6F97", "agriculture": "#A67C52", "mixed": "#D8CBB3"})
Q2_COLOURS.update({"official": "#12355B", "osm": "#F0A030", "absent": "#C2306E"})
PALETTE = ["#2A6F97", "#8FC1B5", "#E5B25D", "#E8604C", "#7C5E99", "#5FA88A", "#A67C52", "#8C97A3"]
NA_COLOUR = "#E3DACA"
lu_items2 = [(k, int(v), LAND_COLOURS.get(k), None) for k, v in emb["land_use_display"].value_counts().items()]
sm_names = sorted(n for n in emb["morphotype_spacematrix"].unique() if n != "not defined")
st_names = sorted(n for n in emb["morphotype_strelka"].unique() if n != "not defined")
MORPH = {"spacematrix": {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(sm_names)},
         "strelka": {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(st_names)}}

sm_items_c = []
_ks = emb[emb["spacematrix_cluster"].notna()].groupby("morphotype_spacematrix")["spacematrix_cluster"].apply(lambda x: sorted(int(v) for v in x.unique()))
for (name, cl), n_ in (emb.groupby(["morphotype_spacematrix", "spacematrix_cluster"], dropna=False).size().items()):
    if name != "not defined":
        ks = _ks[name]
        label = name if len(ks) == 1 else f"{name} (group {ks.index(int(cl)) + 1} of {len(ks)})"
        sm_items_c.append((label, int(n_), MORPH["spacematrix"][name], None))
sm_items_c.append(("not defined (no buildings)", int((emb["morphotype_spacematrix"] == "not defined").sum()), NA_COLOUR, None))
st_items_c = [((k if k != "not defined" else "not defined (no buildings)"), int(v),
               NA_COLOUR if k == "not defined" else MORPH["strelka"][k], None) for k, v in st_counts.items()]
mxi_hist = hist_svg(emb["mxi"].dropna(), "mxi (living share of floor area)")
acc_hist = hist_svg(reg["median_accessibility"], "median walking time to the other blocks, min")

bands = [(0, 10), (10, 15), (15, 20), (20, 30), (30, 60)]
band_items = []
for lo, hi in bands:
    ch = int(emb.loc[(t_basic > lo) & (t_basic <= hi), "children_7_15"].sum()) if lo else int(emb.loc[t_basic <= hi, "children_7_15"].sum())
    band_items.append((f"{lo}–{hi} min" if lo else f"up to {hi} min", ch, None, None))
band_items.append((f"over {bands[-1][1]} min", int(emb.loc[t_basic > bands[-1][1], "children_7_15"].sum()), None, None))

status_label = {"no_etak_tag": "OSM, no maaamet:ETAK tag", "etak_id_in_town_layer": "OSM, ETAK id is in the official town layer",
                "etak_id_in_bbox_only": "OSM, ETAK id only outside the town",
                "absent_from_official_data": "OSM, ETAK id absent from official data (possibly demolished, not verified)"}
q2_status_items = [(status_label[k], int(v), Q2_COLOURS["absent"] if k == "absent_from_official_data" else Q2_COLOURS["osm"], None)
                   for k, v in mq["status"].value_counts().items()]
q2_kind_items = [(f"Official, {k}", int(v), Q2_COLOURS["official"], None) for k, v in oq["kind"].value_counts().head(4).items()]

SC_ORDER = [k for k in gs["land_use_display"].value_counts().index]
SC_LEGEND = ('<div class="lg">' + "".join(f'<span><i style="background:{LAND_COLOURS.get(k, "#999")}"></i>{esc(k)}</span>' for k in SC_ORDER)
             + '<span>larger dot = large block</span></div>')
res_blocks = int((emb["land_use_display"] == "residential").sum())
top10_share = float(top10["population_block"].sum() / N["pop"])
n_dev = int((emb["fsi"] > 0).sum())
high_rise = int((emb["l"] >= 9).sum())
lead = {
    "landuse": f"{num(res_blocks)} of {num(N['blocks'])} blocks are residential by their cadastral purpose, but {pct(non_res_pop)} "
               f"of the people live in blocks of another class.",
    "population": f"{num(N['pop_census'])} people are spread over {num(pop_blocks)} blocks with residential buildings; the 10 most populated "
                  f"blocks hold {pct(top10_share, 0)} of them. The median is {num(dens.median(), 0)} people per hectare.",
    "density": f"Typical built blocks are low and loose: of {num(n_dev)} blocks with buildings the median floor space index (fsi) is "
               f"{emb.loc[emb['fsi'] > 0, 'fsi'].median():.2f} and the median block has {emb['l'].median():.1f} floors on average"
               f"{'; no block reaches the high-rise group' if high_rise == 0 else ''}.",
    "access": f"Walking between blocks takes a median of {num(N['acc_med'], 1)} min; the most remote block has a median of "
              f"{num(N['acc_max'], 1)} min to all others.",
    "schools": f"{children_line}: {pct(walk[10]['share'])} within 10 min, {pct(walk[15]['share'])} within 15 min.",
    "q2": f"{num(N['off_un'])} official buildings have no OSM pair and {num(N['osm_un'])} OSM buildings have no official pair; "
          f"{num(N['osm_un_absent'])} of them carry an ETAK id absent from current official data (possibly demolished, not verified).",
}
note = {
    "landuse": "Cadastral land-use purpose (legal), not actual use. A block is <i>mixed</i> if its largest class covers less than "
               f"{int(MIXED_SHARE * 100)} % of the parcels.",
    "population": "The census total of Haapsalu linn is distributed over the blocks by the net enclosed floor area of their residential buildings in the register; it is not "
                  f"a count per block. The scale is clipped at the 95th percentile ({num(scale['pph'], 0)} people per hectare).",
    "density": f"fsi = floor area / block area; gsi = footprint / block area; L = fsi / gsi; OSR = (1 − gsi) / fsi; "
               f"MXI = living share of the gross floor area. The fsi scale is clipped at the 95th percentile ({scale['fsi']:.2f}). "
               "Morphotypes are BlocksNet results (thresholds and cluster names are BlocksNet's, not ours).",
    "access": f"Walking network of OpenStreetMap at {WALK_SPEED_KMH} km/h (a conditional assumption). The scale is clipped at the "
              f"98th percentile ({scale['acc'][1]:.0f} min).",
    "schools": "Basic schools (red stars) are the two municipal schools of the main calculation; their places are the pupils of "
               "2026, not capacity. Demand: children 7-15 of the census 2021, distributed by population. PGS § 7 (3) is met "
               f"on foot: {pct(walk[60]['share'])} of the children are within 60 min.",
    "q2": "A pair is an official and an OSM building whose overlap is more than 50 % of the smaller one. Only numbers, no conclusions.",
}

def tech(txt):
    return f'<p class="tech">Technical note: {txt}</p>'


def kcard(label, value, line):
    return f'<div class="kcard"><small>{esc(label)}</small><b>{value}</b><span>{esc(line)}</span></div>'


cards_html = "".join([
    kcard("Population", num(N['pop_census']), "census 2021, distributed over blocks"),
    kcard("Urban blocks", num(N['blocks']), f"{num(N['built_up'])} with buildings"),
    kcard("Buildings", num(N['off']) + " / " + num(N['osm']), "official / OpenStreetMap"),
    kcard("Children 7\u201315", num(N['children']), "census 2021"),
    kcard("Basic school pupils", num(N['places']), "two municipal schools, 2026"),
    kcard("OSM match", pct(N['match_town']), "official buildings with an OSM pair")])


def fig(title, svg, mapid=None, cap=""):
    m = f' data-mapid="{mapid}"' if mapid else ""
    return f'<figure class="chart"{m}><figcaption>{esc(title)}</figcaption>{svg}{f"<p class=note>{cap}</p>" if cap else ""}</figure>'


def body_of(key):
    return re.sub(r"^\s*<h2>.*?</h2>", "", T[key], count=1, flags=re.S)


FONTS_HTML = (f'<p><b>Fonts</b>: Fraunces (&copy; The Fraunces Project Authors) for headings and numbers, and Source Sans 3 '
              f'(&copy; Adobe) for text, both under the <a href="https://openfontlicense.org">SIL Open Font License 1.1</a>. They are embedded '
              f'in this page (latin subset, from Google Fonts); the licence texts are in <a href="{REPO_URL}/tree/main/vendor/fonts">'
              f'<code>vendor/fonts/</code></a>. The lace pattern is a simple geometric drawing inspired by Haapsalu lace shawls.</p>')
summary_body = (
    f"<p>This table describes {num(len(reg))} blocks. The {N['large']} large blocks are listed below it, because they would distort the averages. "
    "<i>N</i> is the number of blocks that have a value; <i>missing</i> is the number that do not "
    "(for example, blocks without buildings have no average floors, OSR or MXI). The <i>median</i> is the middle value.</p>"
    "<p class=\"note\">gsi = share of the block covered by buildings; fsi = floor space index (floor area per m² of block); "
    "l = average number of floors; osr = open space ratio (free land per m² of floor area); "
    "mxi = share of the floor area that is housing. Times are on foot.</p>"
    + table(['Indicator', 'N', 'Mean', 'Median', 'Min', 'Max', 'Missing'], sum_rows)
    + "<h3>Large blocks</h3>" + table(['Block', 'Area, km²', 'People', 'gsi', 'fsi', 'l', 'osr', 'mxi', 'Walk, min', 'School, min'], big_rows)
    + '<div class="split2">' + fig("Floor space index (fsi), blocks with buildings", hist_svg(reg.loc[reg['fsi'] > 0, 'fsi'], 'fsi (floor space index)'))
    + fig("Average number of floors (l)", hist_svg(reg['l'].dropna(), 'l (average number of floors)')) + "</div>")
details_html = "".join(f'<details><summary>{esc(t)}</summary><div class="body">{b}</div></details>' for t, b in [
    ("Summary statistics", summary_body), ("Methods & limitations", body_of("methods")),
    ("Data & credits", body_of("sources") + FONTS_HTML), (f"Checks: {n_ok} of {len(checks)} agree", body_of("checks"))])

NAV = [("overview", "Overview"), ("landuse", "Land use"), ("population", "Population"), ("density", "Density"),
       ("access", "Accessibility"), ("schools", "Schools"), ("q2", "OSM vs official"), ("details", "Details")]
nav_html = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in NAV)

def _uri(svg):
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


LACE = _uri("<svg xmlns='http://www.w3.org/2000/svg' width='32' height='16' viewBox='0 0 32 16' fill='none' stroke='#8FC1B5' stroke-width='1'>"
            "<path d='M0 8 Q8 0 16 8 T32 8'/><path d='M16 4.5 L19.5 8 L16 11.5 L12.5 8 Z'/>"
            "<circle cx='8' cy='2.2' r='1.1' fill='#8FC1B5'/><circle cx='24' cy='13.8' r='1.1' fill='#8FC1B5'/></svg>")
LATTICE = _uri("<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 56 56' fill='none' stroke='#8FC1B5' stroke-width='1'>"
               "<path d='M28 2 L54 28 L28 54 L2 28 Z'/><path d='M28 12 L44 28 L28 44 L12 28 Z'/><circle cx='28' cy='28' r='3'/>"
               "<circle cx='28' cy='2' r='1.6' fill='#8FC1B5'/><circle cx='28' cy='54' r='1.6' fill='#8FC1B5'/>"
               "<circle cx='2' cy='28' r='1.6' fill='#8FC1B5'/><circle cx='54' cy='28' r='1.6' fill='#8FC1B5'/>"
               "<circle cx='0' cy='0' r='2.4' fill='#8FC1B5'/><circle cx='56' cy='0' r='2.4' fill='#8FC1B5'/>"
               "<circle cx='0' cy='56' r='2.4' fill='#8FC1B5'/><circle cx='56' cy='56' r='2.4' fill='#8FC1B5'/></svg>")
FONT_DIR = ROOT / "vendor" / "fonts"


def _font(family, fname):
    b64 = base64.b64encode((FONT_DIR / fname).read_bytes()).decode("ascii")
    return (f'@font-face{{font-family:"{family}";font-style:normal;font-weight:400 700;font-display:swap;'
            f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}\n')


FONT_CSS = _font("Fraunces", "Fraunces-latin-variable.woff2") + _font("Source Sans 3", "SourceSans3-latin-variable.woff2")
CSS2 = FONT_CSS + """
:root{--bg:#F4EDE1;--card:#FBF7F0;--fg:#12355B;--mut:#4A6078;--line:#DCCFB8;--acc:#2A6F97;--coral:#E8604C;--coral-dk:#B93F2E;--sea:#8FC1B5;--shadow:0 2px 10px rgba(18,53,91,.09)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 "Source Sans 3",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
h1,h2,.lead,.card b,details>summary{font-family:Fraunces,Georgia,"Times New Roman",serif}
.card b,.lead,h1,h2,table,ul.kf,.hl,details>summary,.legend,.chart{font-variant-numeric:lining-nums tabular-nums}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
a{color:var(--acc)}code{font-size:.9em}
a:focus-visible,summary:focus-visible,.pt:focus-visible,.btn:focus-visible{outline:3px solid var(--coral);outline-offset:2px}
.hero{position:relative;overflow:hidden;padding:36px 0 40px}
.hero::before{content:"";position:absolute;inset:0;background:url(""" + LATTICE + """) repeat;opacity:.6;-webkit-mask-image:linear-gradient(100deg,transparent 40%,#000 100%);mask-image:linear-gradient(100deg,transparent 40%,#000 100%)}
.hero::after{content:"";position:absolute;left:0;right:0;bottom:6px;height:16px;background:url(""" + LACE + """) repeat-x center}
.hero .wrap{position:relative}
.hero h1{font-size:clamp(32px,5vw,50px);font-weight:600;line-height:1.1;letter-spacing:-.01em;margin:0 0 10px}
.hero .sub{font-size:clamp(17px,2vw,20px);color:var(--mut);max-width:760px;margin:0 0 16px}
.hero .meta{display:flex;flex-wrap:wrap;gap:10px 20px;align-items:center;color:var(--mut);font-size:15px}
.btn{display:inline-block;background:var(--coral-dk);color:#fff!important;padding:9px 20px;border-radius:999px;text-decoration:none;font-weight:600;font-size:16px;box-shadow:var(--shadow)}
.btn:hover{background:#9C3324}
nav.top{position:sticky;top:0;z-index:2000;background:rgba(244,237,225,.97);border-bottom:1px solid var(--line)}
nav.top .wrap{display:flex;flex-wrap:wrap;gap:2px 18px;padding:8px 20px}
nav.top a{font-size:15px;color:var(--fg);text-decoration:none;padding:2px 1px;border-bottom:3px solid transparent}
nav.top a:hover{border-bottom-color:var(--sea)}
nav.top a.on{border-bottom-color:var(--coral);font-weight:700}
section{padding:0 0 36px;scroll-margin-top:84px}
section+section::before{content:"";display:block;height:16px;background:url(""" + LACE + """) repeat-x center;margin:0 0 30px}
#overview{padding-top:26px}
h2{font-size:clamp(26px,3.2vw,34px);font-weight:600;margin:0 0 8px}h3{font-size:17px;margin:16px 0 6px}
.lead{font-size:clamp(21px,2.7vw,29px);line-height:1.3;font-weight:500;margin:0 0 10px;max-width:940px}
.note{color:var(--mut);font-size:15px;max-width:920px}
.hl{color:var(--coral-dk);font-weight:700}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow)}
.card b{display:block;font-size:clamp(24px,2.4vw,30px);font-weight:600;line-height:1.15;color:var(--acc)}.card span{font-size:14px;color:var(--mut)}
.cards.top{grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:1fr}
@media (min-width:700px){.cards.top{grid-template-columns:repeat(3,minmax(0,1fr))}}
.kcard{position:relative;display:flex;flex-direction:column;gap:3px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 12px 11px;box-shadow:var(--shadow)}
.kcard::before{content:"";position:absolute;left:14px;right:14px;top:0;height:4px;border-radius:0 0 4px 4px;background:var(--acc)}
.kcard:nth-child(3n+2)::before{background:var(--coral)}
.kcard:nth-child(3n)::before{background:var(--sea)}
.kcard small{font-size:11px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;line-height:1.2;color:var(--mut)}
.kcard b{font-family:Fraunces,Georgia,"Times New Roman",serif;font-weight:600;font-size:clamp(17px,5vw,28px);line-height:1.1;white-space:nowrap;color:var(--fg);font-variant-numeric:lining-nums tabular-nums}
.kcard span{font-size:13px;line-height:1.2;color:var(--mut)}
ul.kf{list-style:none;margin:8px 0 4px;padding:0;font-size:18.5px}
ul.kf li{position:relative;padding-left:24px;margin:8px 0}
ul.kf li::before{content:"";position:absolute;left:3px;top:.62em;width:8px;height:8px;background:var(--coral);transform:rotate(45deg)}
.split{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:22px;align-items:start;margin-top:12px}
.split2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.mapbox{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}
.map{height:clamp(440px,74vh,720px);background:#DCE9EA;isolation:isolate}
.leaflet-container{font-family:inherit}
.modes{display:flex;flex-wrap:wrap;gap:4px 16px;padding:10px 14px;font-size:15px}.modes:empty{display:none}
.legend{padding:10px 14px 12px;font-size:14px;line-height:1.45;color:var(--fg)}
.legend .bar{height:10px;max-width:260px;border:1px solid #6b7c8f;margin:3px 0}.legend .lr{display:flex;justify-content:space-between;max-width:260px}
.legend .sw{display:inline-block;width:12px;height:12px;margin:0 5px 0 0;vertical-align:-2px;border:1px solid #6b7c8f}
.legend .it{display:inline-block;margin:0 14px 2px 0}
.side{min-width:0}
figure.chart{margin:0 0 18px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 14px;box-shadow:var(--shadow)}
figure.chart figcaption{font-weight:700;font-size:16px;margin-bottom:4px}
.chart svg{width:100%;height:auto;max-width:560px}
.chart .bar{fill:var(--acc)}.chart .bl,.chart .bv{fill:var(--fg);font-size:11px}
.chart .gr{stroke:var(--line);stroke-width:.6}.chart .tk,.chart .gt,.chart .ax{fill:var(--mut);font-size:10px}
.chart .gl{stroke:#6b7c8f;stroke-width:1}.chart .go{stroke:#6b7c8f;stroke-width:1;stroke-dasharray:4 3}
.chart .lg{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:14px;margin-top:6px}.chart .lg i{display:inline-block;width:11px;height:11px;border-radius:50%;border:1px solid var(--fg);margin-right:4px;vertical-align:-1px}
.chart .pt{cursor:pointer}.chart circle.pt{stroke:var(--fg);stroke-width:.6}.chart .pt:hover,.chart .pt:focus{stroke:var(--coral);stroke-width:2}
.tw{overflow-x:auto;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px;background:var(--card)}
thead th{background:#F1E8D8;color:var(--fg)}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
td:not(:first-child),th:not(:first-child){text-align:right}table.checks td:last-child{text-align:left}
details{background:var(--card);border:1px solid var(--line);border-radius:16px;margin:12px 0;box-shadow:var(--shadow)}
details>summary{cursor:pointer;padding:15px 20px;font-weight:600;font-size:21px}
details>.body{padding:0 20px 20px}
.bm{display:flex;flex-direction:column;align-items:flex-end;font-size:13px;line-height:1.4;color:var(--fg)}
.bm .bmb{width:34px;height:34px;padding:0;display:flex;align-items:center;justify-content:center;background:rgba(251,247,240,.96);border:1px solid var(--line);border-radius:8px;cursor:pointer;box-shadow:var(--shadow)}
.bm .bmb:hover{background:#fff}
.bm .bmp{margin-top:4px;background:rgba(251,247,240,.97);border:1px solid var(--line);padding:6px 10px;border-radius:8px;box-shadow:var(--shadow)}
.bm .bmp[hidden]{display:none}.bm label{display:block;white-space:nowrap}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:3px}
footer{padding:10px 0 56px;color:var(--mut);font-size:14px}
@media (max-width:800px){
.split{grid-template-columns:1fr}
.map{height:470px}
.wrap{padding:0 16px}nav.top .wrap{padding:6px 16px;gap:2px 14px}
.hero{padding:26px 0 36px}.hero::before{opacity:.35;-webkit-mask-image:linear-gradient(100deg,transparent 60%,#000 100%);mask-image:linear-gradient(100deg,transparent 60%,#000 100%)}
section{scroll-margin-top:96px}
ul.kf{font-size:17px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

config2 = dict(tiles=TILES, attribution=f"Aluskaart: Maa- ja Ruumiamet {BASEMAP_YEAR}", landColours=LAND_COLOURS, q2Colours=Q2_COLOURS,
               scale=scale, kinds=kinds, morph=MORPH)
data2 = json.dumps({"config": config2, "blocks": blocks_fc, "boundary": boundary_fc, "schools": schools_fc, "points": points},
                   ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")

def hl(x):
    t = re.sub(r"(\d[\d.,]*(?:\u2013\d[\d.,]*)?\s?(?:%|\u00d7))", r'<strong class="hl">\1</strong>', esc(x))
    return re.sub(r"^(\d+)", r'<strong class="hl">\1</strong>', t) if t[:1].isdigit() else t


HOC = '<span class="hov">Hover or click</span><span class="tap">Tap</span>'
note3 = dict(note)
note3["landuse"] = note["landuse"] + '<span class="tap"> Move the map with two fingers.</span>'
note3["density"] = ("Colour the map by fsi, MXI or a BlocksNet morphotype. " + HOC + " a dot of the chart or a block of the map "
                    "to find it on both.")
note3["population"] = note["population"]
DEFAULT_MODE = {"landuse": "landuse", "population": "population", "density": "fsi", "access": "access", "schools": "time", "q2": "q2"}


def radios(name, items, checked):
    return ('<div class="modes3" role="radiogroup">' + "".join(
        f'<label><input type="radio" name="{name}" value="{v}"{" checked" if v == checked else ""}> {esc(t)}</label>'
        for v, t in items) + "</div>")


def sec3(sid, title, body):
    return (f'<section id="{sid}" data-card="{CARDS[sid]}"><h2>{esc(title)}</h2><p class="lead">{lead[sid]}</p>'
            f'<p class="note">{note3[sid]}</p>{body}</section>')


def more(title, inner):
    return f'<details class="more"><summary>{esc(title)}</summary><div class="body">{inner}</div></details>'


def morph_items(col, colours, with_clusters):
    g = emb.groupby(col).agg(n=("block_id", "size"), k=("spacematrix_cluster", "nunique"))
    items = []
    for name in sorted(x for x in g.index if x != "not defined"):
        n_, k_ = int(g.loc[name, "n"]), int(g.loc[name, "k"])
        label = f"{name} · {k_} clusters" if with_clusters and k_ > 1 else name
        items.append((label, n_, colours[name], None))
    items.append(("not defined (no buildings)", int(g.loc["not defined", "n"]) if "not defined" in g.index else 0, NA_COLOUR, None))
    return items


sm_group = morph_items("morphotype_spacematrix", MORPH["spacematrix"], True)
st_group = morph_items("morphotype_strelka", MORPH["strelka"], False)
assert len(sm_group) <= 7 and len(st_group) <= 7
morph_chart = ('<figure class="chart"><figcaption>Blocks by morphotype (BlocksNet)</figcaption>'
               '<div class="modes3"><label><input type="radio" name="morphchart" value="sm" checked> Spacematrix</label>'
               '<label><input type="radio" name="morphchart" value="st"> Strelka</label></div>'
               f'<div class="morphchart" data-k="sm">{bars_svg(sm_group, aria="Blocks by Spacematrix morphotype")}'
               '<p class="note">Groups with the same name are added up.</p></div>'
               f'<div class="morphchart" data-k="st" hidden>{bars_svg(st_group, aria="Blocks by Strelka morphotype")}'
               '<p class="note">The Strelka types follow fixed rules from BlocksNet (floors, density and share of housing). They are not our own norms.</p></div></figure>')

body3 = {
    "landuse": fig("Blocks by land-use class", bars_svg(lu_items2, aria="Blocks by land use"))
    + more("More on land use",
           f"<p>Each block gets the land-use class that covers most of its land. A block where the largest class covers less than {int(MIXED_SHARE * 100)} % of the land is called mixed. "
           "The classes come from the cadastre, which records what each parcel may be used for, not what is really there.</p>"
           "<p>The table shows, for each class, how many blocks it has, how many people live in them and how much land they cover.</p>"
           + table(['Class', 'Blocks', 'Population', 'Share of population', 'Area, km²'], lu_rows)
           + tech("OpenStreetMap land use is not used; the class with the largest share of parcel area wins (BlocksNet assign_land_use).")),
    "population": fig("10 blocks with the most people", bars_svg(top_items, aria="Top 10 blocks by population"), None,
                      "Distributed census population. " + HOC + " a bar to find the block on the map.")
    + more("More on population",
           f"<p>The census counts people for the whole town, not for single blocks. We share the town total of {num(N['pop_census'])} people "
           "between the blocks in proportion to the floor area of their residential buildings in the building register.</p>"
           f"<p>Why not estimate it directly? Dividing the floor area of residential buildings by the average living space per person ({popcheck['living_area_per_person_m2']} m²) "
           f"would give {num(popcheck['population_net'])} people, {popcheck['ratio_net_to_official']:.2f} times the census. "
           f"Using building footprint × floors would give {num(popcheck['population_gross'])}, {popcheck['ratio_gross_to_official']:.2f} times. "
           f"One known reason: in the census, about {vacant_share * 100:.0f} % of the floor area of dwellings stands empty. So the real census total is shared out instead.</p>"
           + tech("home floor area = net enclosed floor area (suletud netopind) of residential buildings in the register, including stairs and corridors, not only flats; the second estimate uses footprint × floors with the floors of the register.")),
    "density": radios("mode-density", [("fsi", "Floor space index (fsi)"), ("mxi", "MXI (living share)"),
                                       ("spacematrix", "Spacematrix morphotype"), ("strelka", "Strelka morphotype")], "fsi")
    + fig("Spacematrix: fsi against gsi", scatter() + SC_LEGEND, None,
          "Dot colour = land-use class. Solid lines: constant L (mean floors); dashed: constant OSR.")
    + morph_chart
    + more("More on density",
           "<p><b>How to read the numbers.</b> The floor space index (fsi) is the floor area per m² of block. "
           "The ground space index (gsi) is the share of the block covered by buildings. L is the average number of floors. "
           "The open space ratio (OSR) is the free land per m² of floor area. MXI is the share of the floor area that is housing.</p>"
           f"<p>On the map the fsi colours stop at {scale['fsi']:.2f}, the value that 95 out of 100 blocks with buildings stay under, "
           "so a few very dense blocks do not hide the differences between the rest.</p>"
           "<p><b>How the morphotypes were made.</b> BlocksNet groups blocks that look alike (similar number of floors, similar density "
           "and a similar share of housing) and names each group after its typical block. Some groups end up with the same name: "
           "they are similar but not identical, so they are added up on the main card.</p>"
           + fig("All Spacematrix groups", bars_svg(sm_items_c, aria="Blocks by Spacematrix group"),
                 cap=f"Each bar is one group of blocks. Names shared by several groups: {esc('; '.join(dup_names)) if dup_names else 'none here'}.")
           + fig("Housing share (MXI) of the blocks with buildings", mxi_hist,
                 cap="A building counts as housing if it has a dwelling use, as a whole. A shop on the ground floor does not lower the value; "
                     "sheds and garages count as non-housing and do lower it.")
           + tech(f"KMeans, {nbnum['morphotype_params']['spacematrix_n_clusters']} clusters, random_state "
                  f"{nbnum['morphotype_params']['spacematrix_random_state']}, scikit-learn {esc(nbnum['morphotype_params']['scikit_learn'])}; "
                  "names and thresholds are BlocksNet's.")),
    "access": fig("Median walking time to the other blocks", acc_hist),
    "schools": radios("mode-schools", [("time", "Walking time"), ("p10", "Served within 10 min"), ("p15", "within 15 min"),
                                       ("p20", "within 20 min")], "time")
    + fig("Children aged 7-15 by walking time to the nearest basic school", bars_svg(band_items, aria="Children by walking time"))
    + more("More on schools",
           f"<p>This table counts the {num(N['children'])} children aged 7\u201315 by walking time to the nearest of the two municipal basic schools. "
           "The children are shared between the blocks in proportion to the population, because the census has no ages by block.</p>"
           + table(['Walking time', 'Children', 'Share of the children', 'Blocks'], w_rows)
           + "<p><b>Places at school.</b> Here every school place goes to one child who lives within the walking time. "
             "The second table shows what share of the children get a place. A school has as many places as it had pupils in 2026, "
             "because the register has no capacity figure. So the result shows how well the schools are placed, "
             "not whether there are enough places.</p>"
           + table(['Walking time', 'Share of children with a place', 'Blocks where some children get no place'], p_rows)
           + tech(f"BlocksNet competitive_provision (strong provision), limits of {PROVISION[0]}, {PROVISION[1]} and {PROVISION[2]} minutes; walking speed {WALK_SPEED_KMH} km/h.")),
    "q2": '<div class="cards two">' + card(num(N['off_un']), 'official buildings without an OSM pair (of ' + num(N['off']) + ')')
    + card(num(N['osm_un']), 'OSM buildings without an official pair (of ' + num(N['osm']) + ')')
    + card(pct(N['floors_off']), 'official buildings with floors in the register')
    + card(pct(N['levels_osm']), 'OSM buildings with building:levels') + '</div>'
    + '<div class="modes3">' + "".join(
        f'<label><input type="checkbox" data-q2="{k}" checked> <i class="dot" style="background:{Q2_COLOURS[k]}"></i>{t}</label>'
        for k, t in [("official", "official, no OSM pair"), ("osm", "OSM, no official pair"),
                     ("absent", "OSM, possibly demolished, not verified")]) + "</div>"
    + fig("Buildings without a pair", bars_svg(q2_status_items + q2_kind_items, aria="Buildings without a pair")),
}
titles3 = {"landuse": "Land use", "population": "Population", "density": "Density", "access": "Accessibility",
           "schools": "Schools", "q2": "OSM vs official"}
def card_attr(title, lead_txt, kpis):
    return esc(json.dumps({"title": title, "lead": lead_txt, "kpi": kpis}, ensure_ascii=False))


CARDS = {
    "overview": card_attr("Haapsalu urban blocks", "Haapsalu (Estonia) cut into urban blocks and described by land use, population, density, "
                          "walking access and schools.", [[num(N['pop_census']), "inhabitants, census 2021"], [num(N['blocks']), "urban blocks"]]),
    "landuse": card_attr("Land use", lead["landuse"], [[f"{num(res_blocks)} of {num(N['blocks'])}", "blocks are residential"],
                                                       [pct(non_res_pop), "of people in other classes"]]),
    "population": card_attr("Population", lead["population"], [[num(dens.median(), 0), "people per hectare, median"],
                                                                [pct(top10_share, 0), "live in the 10 largest blocks"]]),
    "density": card_attr("Density", lead["density"], [[f"{emb.loc[emb['fsi'] > 0, 'fsi'].median():.2f}", "median fsi"],
                                                      [f"{emb['l'].median():.1f}", "floors, median block"]]),
    "access": card_attr("Accessibility", lead["access"], [[num(N['acc_med'], 1) + " min", "median walking time"],
                                                          [num(N['acc_max'], 1) + " min", "most remote block"]]),
    "schools": card_attr("Schools", lead["schools"], [[pct(walk[10]['share']), "of children within 10 min"],
                                                      [pct(walk[15]['share']), "within 15 min"]]),
    "q2": card_attr("OSM vs official", lead["q2"], [[num(N['off_un']), "official buildings without a pair"],
                                                    [num(N['osm_un']), "OSM buildings without a pair"]]),
    "details": card_attr("Details", "Methods and limitations, data sources and credits, summary statistics and the checks table.",
                         [[f"{n_ok} of {len(checks)}", "checks agree"]]),
}
story_html = "".join(sec3(k, titles3[k], body3[k]) for k in ["landuse", "population", "density", "access", "schools", "q2"])

CSS3 = """
/* scrollytelling layout */
.cards.two{grid-template-columns:repeat(2,minmax(0,1fr))}
.modes3{display:flex;flex-wrap:wrap;gap:4px 16px;margin:10px 0;font-size:15px}
.story{display:block}
.mapwrap{position:relative;height:100%;border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow);isolation:isolate;background:#DCE9EA}
#map{position:absolute;inset:0;background:#DCE9EA}
.maplegend{position:absolute;left:10px;bottom:10px;z-index:1000;max-width:min(330px,72%);max-height:60%;overflow:auto;background:rgba(251,247,240,.95);
border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-size:13px;line-height:1.4;color:var(--fg);box-shadow:var(--shadow)}
.maplegend .bar{height:10px;max-width:260px;border:1px solid #6b7c8f;margin:3px 0}.maplegend .lr{display:flex;justify-content:space-between;max-width:260px}
.maplegend .sw{display:inline-block;width:12px;height:12px;margin:0 5px 0 0;vertical-align:-2px;border:1px solid #6b7c8f}
.maplegend .it{display:inline-block;margin:0 12px 2px 0}
.lgbtn{display:none}
.tap{display:none}
.aboutbtn{display:none}
.textcol section{padding:30px 0 24px;min-height:88vh;scroll-margin-top:60px}
.textcol section:first-child{padding-top:30px}
.textcol figure.chart{margin:14px 0}
details.more{box-shadow:none;margin:10px 0;border-radius:12px}
details.more>summary{font-size:17px;padding:10px 14px}details.more>.body{padding:0 14px 14px}
.tech{font-size:12px;line-height:1.35;color:var(--mut);margin:10px 0 0}
.tt{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;font:14px "Source Sans 3",system-ui,sans-serif;box-shadow:var(--shadow)}
.leaflet-popup-content{font-size:14px;margin:12px 14px;font-family:"Source Sans 3",system-ui,sans-serif;font-variant-numeric:lining-nums tabular-nums}
.leaflet-popup-content table{font-size:13px}
.chart .hot{stroke:var(--coral)!important;stroke-width:2.6!important}.chart rect.hot{fill:var(--coral)}
@media (min-width:1000px){
.story{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);align-items:start}
.story::before{grid-column:1/-1}
.mapcol{position:sticky;top:46px;height:calc(100vh - 46px);padding:12px 8px 14px 20px}
.textcol{padding:0 28px 0 24px;min-width:0}
}
@media (max-width:999px){
.hov{display:none}.tap{display:inline}
html.app,body.app{height:100%;overflow:hidden}
body.app{font-size:16px}
.app header.hero,.app nav.top,.app #overview,.app .textcol,.app #details,.app footer,.app .story::before{display:none}
body.cover .story,body.cover #details,body.cover .appbar,body.cover #sheet,body.cover nav.top{display:none}
.explore{padding:6px 16px 28px}
.exbtn{display:block;width:100%;font:600 18px "Source Sans 3",system-ui,sans-serif;color:#fff;background:var(--coral-dk);border:0;border-radius:999px;padding:16px 20px;box-shadow:var(--shadow);cursor:pointer}
.app .aboutbtn{display:block;position:absolute;top:10px;right:56px;z-index:1000;font:600 12px "Source Sans 3",system-ui,sans-serif;color:var(--fg);background:rgba(251,247,240,.96);border:1px solid var(--line);border-radius:999px;padding:5px 12px;box-shadow:var(--shadow);cursor:pointer}
.leaflet-popup-content{font-size:12px;line-height:1.3;margin:8px 10px}
.leaflet-popup-content table{font-size:11.5px}
.leaflet-popup-content td{padding:1px 5px}
.leaflet-popup-content-wrapper{border-radius:10px}
.app .insheet{display:block!important}
.app .story{display:block}
.app .mapcol{position:fixed;left:0;right:0;top:0;height:56vh;height:56dvh;padding:6px 8px 4px;background:var(--bg);z-index:1}
.maplegend{left:8px;bottom:8px;max-width:calc(100% - 16px);max-height:80%;padding:0;background:none;border:0;box-shadow:none;font-size:11.5px;line-height:1.3}
.lgbtn{display:inline-block;font:600 12px "Source Sans 3",system-ui,sans-serif;color:var(--fg);background:rgba(251,247,240,.96);border:1px solid var(--line);border-radius:999px;padding:3px 11px;box-shadow:var(--shadow);cursor:pointer}
.maplegend:not(.open) .lgbody{display:none}
.maplegend.open{background:rgba(251,247,240,.96);border:1px solid var(--line);border-radius:10px;padding:6px 8px;box-shadow:var(--shadow)}
.maplegend.open .lgbtn{margin-bottom:4px}
.maplegend .it{margin:0 8px 1px 0}.maplegend .bar{max-width:170px;height:8px}.maplegend .lr{max-width:170px}.maplegend .sw{width:10px;height:10px}
.leaflet-control-attribution{font-size:9px!important;padding:0 4px!important}
.leaflet-control-zoom a{width:28px;height:28px;line-height:28px}
.hero h1{font-size:30px}
h2{font-size:23px}
.lead{font-size:21px;line-height:1.3}
.note{font-size:14px}
ul.kf{font-size:16px}
.card b{font-size:24px}
details>summary{font-size:18px}
.cards.two{grid-template-columns:repeat(2,minmax(0,1fr))}
/* bottom strip of section cards */
.appbar{position:fixed;left:0;right:0;top:56vh;top:56dvh;bottom:0;z-index:2;display:flex;flex-direction:column;padding-bottom:env(safe-area-inset-bottom)}
.stripwrap{position:relative;flex:1;min-height:0;display:flex}
.strip{position:relative;flex:1;min-width:0;display:flex;align-items:flex-start;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;padding:6px 0 4px}
.strip::-webkit-scrollbar{display:none}
.strip::before,.strip::after{content:"";flex:0 0 calc(6% - 6px)}
.appcard{flex:0 0 88%;max-height:100%;margin:0 6px;scroll-snap-align:center;display:flex;flex-direction:column;gap:6px;overflow-y:auto;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:10px 14px 12px;box-shadow:var(--shadow)}
.appcard .ct{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:18px;line-height:1.2}
.appcard>*{flex:none}
.appcard .cl{margin:0;font-size:14px;line-height:1.3}
.appcard .ck{display:flex;gap:8px}
.appcard .kpi{flex:1;min-width:0;background:var(--bg);border-radius:10px;padding:5px 8px}
.appcard .kpi b{display:block;font-family:Fraunces,Georgia,serif;font-size:18px;line-height:1.2;color:var(--acc);font-variant-numeric:lining-nums tabular-nums}
.appcard .kpi span{font-size:12px;color:var(--mut);line-height:1.2;display:block}
.appcard .modes3{margin:0;gap:0 12px;font-size:13px;line-height:1.35}
.appcard .rm{margin-top:4px;align-self:flex-start;font:600 14px "Source Sans 3",system-ui,sans-serif;color:#fff;background:var(--coral-dk);border:0;border-radius:999px;padding:7px 16px;cursor:pointer}
.dots{display:flex;justify-content:center;gap:8px;padding:2px 0 8px}
.dots button{position:relative;width:9px;height:9px;padding:0;border:0;border-radius:5px;background:#c9bda6;transition:width .15s}
.dots button::after{content:"";position:absolute;inset:-9px -4px}
.dots button.on{width:20px;background:var(--coral)}
/* bottom sheet */
#sheet{position:fixed;left:0;right:0;bottom:0;top:5vh;top:5dvh;z-index:3000;display:none;flex-direction:column;background:var(--bg);border-radius:18px 18px 0 0;box-shadow:0 -6px 24px rgba(18,53,91,.28);transform:translateY(105%);transition:transform .26s ease}
#sheet.vis{display:flex}
#sheet.open{transform:none}
.grab{position:relative;display:flex;align-items:center;gap:10px;padding:16px 14px 8px;border-bottom:1px solid var(--line);touch-action:none}
.grab .handle{position:absolute;left:50%;top:6px;width:42px;height:4px;margin-left:-21px;border-radius:2px;background:#c9bda6}
.grab .stitle{font-family:Fraunces,Georgia,serif;font-size:18px}
.grab .sclose{margin-left:auto;font:600 14px "Source Sans 3",system-ui,sans-serif;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 14px;cursor:pointer}
.sbody{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:12px 16px 30px}
.sbody section{min-height:0;padding:0 0 12px}
.sbody .hero{padding:4px 0 26px}
.sbody section[data-card]:not(#overview)>h2,.sbody #details>.wrap>h2{display:none}
}
"""

JS3 = r"""
(function(){
const D=JSON.parse(document.getElementById('data').textContent),C=D.config,LC=C.landColours,QC=C.q2Colours,MC=C.morph,NA='#E3DACA';
const SEQ={blue:['#F6EFDF','#CFE3DC','#8FC1B5','#4F94A6','#1D4E7A'],heat:['#FBEFD5','#F4C98A','#EE9A62','#E8604C','#A8322F'],
rdylgn:['#C9473A','#EE9A62','#F6EFDF','#9CCBBE','#2F8A7A'],green:['#F4F0E4','#CFE3DC','#8FC1B5','#3E8F82','#16524F']};
function hex(h){return [1,3,5].map(i=>parseInt(h.substr(i,2),16))}
function ramp(st,t){t=Math.max(0,Math.min(1,t));const k=t*(st.length-1),i=Math.min(st.length-2,Math.floor(k)),f=k-i,a=hex(st[i]),b=hex(st[i+1]);return 'rgb('+a.map((x,j)=>Math.round(x+(b[j]-x)*f)).join(',')+')'}
function grad(st){return 'linear-gradient(to right,'+st.join(',')+')'}
const fmt={int:v=>v==null?'-':Math.round(v).toLocaleString('en'),f1:v=>v==null?'-':v.toFixed(1),f2:v=>v==null?'-':v.toFixed(2),f3:v=>v==null?'-':v.toFixed(3),
pct:v=>v==null?'-':(100*v).toFixed(1)+' %',osr:v=>v==null?'-':(v>100?'> 100':v.toFixed(2)),txt:v=>v==null?'-':v};
function cbar(t,st,a,b){return '<b>'+t+'</b><div class="bar" style="background:'+grad(st)+'"></div><div class="lr"><span>'+a+'</span><span>'+b+'</span></div>'}
function sw(c,round){return '<span class="sw" style="background:'+c+(round?';border-radius:50%':'')+'"></span>'}
function cat(t,pairs){return '<b>'+t+'</b><br>'+pairs.map(p=>'<span class="it">'+sw(p[1])+p[0]+'</span>').join('')}
function nodata(t){return '<span class="it">'+sw(NA)+t+'</span>'}
const LARGE='<span class="it"><span class="sw" style="background:#fff;border:2px solid #12355B"></span>large block</span>';
const SCHLEG='<span class="it"><span style="color:#d73027;font-size:17px;line-height:1">&#9733;</span> red star: municipal basic schools in the calculation</span><br><span class="it"><span style="font-size:13px">&#9650;</span> triangle: other schools (gymnasium, special school, private school)</span><br>';
function base(p){return p.large_block?{color:'#12355B',weight:2.6}:{color:'#8794A3',weight:.6}}
const prov=n=>({f:p=>{const v=p['provision_strong_'+n];return v==null?{fillColor:NA,fillOpacity:.5}:{fillColor:v>=1?'#3E8F82':'#C9473A',fillOpacity:.8}},
leg:()=>'<b>Served within '+n+' min</b><br><span class="it">'+sw('#3E8F82')+'children served</span><span class="it">'+sw('#C9473A')+'not served</span>'+nodata('no children')+'<br>'+SCHLEG+LARGE,
tip:p=>{const v=p['provision_strong_'+n];return v==null?'no children':(v>=1?'served within '+n+' min':'not served within '+n+' min')}});
const morph=(k,key)=>({f:p=>({fillColor:MC[k][p[key]]||NA,fillOpacity:.85}),
leg:()=>cat((k==='spacematrix'?'Spacematrix':'Strelka')+' morphotype (BlocksNet)',Object.keys(MC[k]).map(n=>[n,MC[k][n]]))+nodata('not defined (no buildings)')+LARGE,
tip:p=>p[key]});
const MODE={
landuse:{f:p=>({fillColor:LC[p.land_use_display]||NA,fillOpacity:.8}),leg:()=>cat('Land use (cadastral purpose)',Object.keys(LC).filter(k=>k!=='agriculture').map(k=>[k,LC[k]]))+LARGE,tip:p=>p.land_use_display},
population:{f:p=>p.population_block>0?{fillColor:ramp(SEQ.blue,p.pph/C.scale.pph),fillOpacity:.85}:{fillColor:NA,fillOpacity:.5},
leg:()=>cbar('People per hectare',SEQ.blue,'0',Math.round(C.scale.pph)+'+')+nodata('no population')+LARGE,tip:p=>p.population_block>0?fmt.f1(p.pph)+' people per ha':'no population'},
fsi:{f:p=>p.fsi>0?{fillColor:ramp(SEQ.blue,p.fsi/C.scale.fsi),fillOpacity:.85}:{fillColor:NA,fillOpacity:.5},
leg:()=>cbar('fsi (floor space index)',SEQ.blue,'0',C.scale.fsi.toFixed(2)+'+')+nodata('no buildings')+LARGE,tip:p=>p.fsi>0?'fsi '+fmt.f2(p.fsi):'no buildings'},
mxi:{f:p=>p.mxi==null?{fillColor:NA,fillOpacity:.5}:{fillColor:ramp(SEQ.green,p.mxi),fillOpacity:.85},
leg:()=>cbar('MXI: living share of the floor area',SEQ.green,'0','1')+nodata('no buildings')+LARGE,tip:p=>p.mxi==null?'no buildings':'MXI '+fmt.f2(p.mxi)},
spacematrix:morph('spacematrix','morphotype_spacematrix'),strelka:morph('strelka','morphotype_strelka'),
access:{f:p=>({fillColor:ramp(SEQ.heat,(p.median_accessibility-C.scale.acc[0])/(C.scale.acc[1]-C.scale.acc[0])),fillOpacity:.85}),
leg:()=>cbar('Median walking time to the other blocks, min',SEQ.heat,Math.round(C.scale.acc[0]),Math.round(C.scale.acc[1])+'+')+LARGE,tip:p=>fmt.f1(p.median_accessibility)+' min'},
time:{f:p=>({fillColor:ramp(SEQ.heat,p.time_to_basic_school_min/C.scale.time),fillOpacity:.85}),
leg:()=>cbar('Walking time to the nearest basic school, min',SEQ.heat,'0',Math.round(C.scale.time)+'+')+'<br>'+SCHLEG+LARGE,tip:p=>fmt.f1(p.time_to_basic_school_min)+' min to a basic school'},
p10:prov(10),p15:prov(15),p20:prov(20),
q2:{f:p=>p.match_rate==null?{fillColor:NA,fillOpacity:.45}:{fillColor:ramp(SEQ.rdylgn,(p.match_rate-.5)/.5),fillOpacity:.65},
leg:()=>cbar('Share of official buildings with an OSM pair',SEQ.rdylgn,'0.5 or less','1')+nodata('no official buildings')+'<br><span class="it">'+sw(QC.official,1)+'official, no OSM pair</span><span class="it">'+sw(QC.osm,1)+'OSM, no official pair</span><span class="it">'+sw(QC.absent,1)+'OSM, possibly demolished, not verified</span>'+LARGE,
tip:p=>p.match_rate==null?'no official buildings':'match rate '+fmt.pct(p.match_rate)}};
const SECMODE={landuse:'landuse',population:'population',density:'fsi',access:'access',schools:'time',q2:'q2'};
const state={mode:Object.assign({},SECMODE),active:null,q2:{official:true,osm:true,absent:true}};
let cur='landuse',sel=null,baseOn=true,closeSheet=function(){};
const isMobile=window.matchMedia('(max-width:999px)').matches;
const ALL=[['Land use','land_use_display','txt'],['People (distributed)','population_block','f1'],['People per hectare','pph','f1'],['fsi','fsi','f3'],['gsi','gsi','f3'],['L (mean floors)','l','f2'],['OSR','osr','osr'],['MXI','mxi','f2'],['Spacematrix','morphotype_spacematrix','txt'],['Strelka','morphotype_strelka','txt'],['Median walking time, min','median_accessibility','f1'],['Time to basic school, min','time_to_basic_school_min','f1'],['Children 7-15','children_7_15','int'],['Served within 10 / 15 / 20 min',null,null],['Official buildings','n_official_q2','int'],['Official without OSM pair','n_official_unmatched','int'],['OSM buildings','n_osm_q2','int'],['OSM without official pair','n_osm_unmatched','int'],['Match rate','match_rate','pct']];
function popup(p){const rows=ALL.map(r=>{if(r[1]===null)return '<tr><td>'+r[0]+'</td><td style="text-align:right">'+[10,15,20].map(t=>{const v=p['provision_strong_'+t];return v==null?'-':(v>=1?'yes':'no')}).join(' / ')+'</td></tr>';
return '<tr><td>'+r[0]+'</td><td style="text-align:right">'+fmt[r[2]](p[r[1]])+'</td></tr>'}).join('');
return '<b>Block '+p.block_id+'</b>'+(p.large_block?' (large block)':'')+'<table>'+rows+'</table>'}
const map=L.map('map',{preferCanvas:true,minZoom:8,maxZoom:19,zoomSnap:.25,scrollWheelZoom:true});
const lg=document.getElementById('maplegend'),lgb=lg.querySelector('.lgbtn');
lgb.addEventListener('click',()=>{const o=lg.classList.toggle('open');lgb.setAttribute('aria-expanded',o)});L.DomEvent.disableClickPropagation(lg);
const tiles=L.tileLayer(C.tiles,{minZoom:8,maxNativeZoom:18,maxZoom:19,attribution:C.attribution}).addTo(map);
const bm=L.control({position:'topright'});bm.onAdd=function(){const d=L.DomUtil.create('div','bm');
d.innerHTML='<button type="button" class="bmb" aria-label="Basemap" aria-expanded="false" title="Basemap"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#12355B" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 16l9 5 9-5"/></svg></button><div class="bmp" hidden><b>Basemap</b><label><input type="radio" name="bm" value="on" checked> Grey map (Maa- ja Ruumiamet)</label><label><input type="radio" name="bm" value="off"> No basemap</label></div>';
L.DomEvent.disableClickPropagation(d);const btn=d.querySelector('.bmb'),pn=d.querySelector('.bmp');
btn.addEventListener('click',()=>{const o=pn.hidden;pn.hidden=!o;btn.setAttribute('aria-expanded',o)});
map.on('click',()=>{pn.hidden=true;btn.setAttribute('aria-expanded',false)});
d.addEventListener('change',e=>{if(e.target.value==='on'){tiles.addTo(map);tiles.bringToBack()}else map.removeLayer(tiles)});return d};bm.addTo(map);
const boundary=L.geoJSON(D.boundary,{style:{color:'#12355B',weight:1.6,fill:false},interactive:false}).addTo(map);
const byId={};
const styleOf=p=>Object.assign({fillOpacity:.5},base(p),MODE[cur].f(p));
const blocks=L.geoJSON(D.blocks,{style:f=>styleOf(f.properties),onEachFeature:(f,l)=>{const id=f.properties.block_id;byId[id]=l;
l.bindTooltip(()=>'<b>Block '+id+'</b> &middot; '+MODE[cur].tip(f.properties),{sticky:true,direction:'top',className:'tt'});
l.on('mouseover',()=>hot(id,true));l.on('mouseout',()=>hot(id,false));l.on('click',()=>select(id,false))}}).addTo(map);
function layerStyle(id){const l=byId[id],p=l.feature.properties;return id===sel?Object.assign(styleOf(p),{color:'#12355B',weight:3.4}):styleOf(p)}
function hot(id,on){const l=byId[id];if(!l)return;if(on){l.setStyle({color:'#E8604C',weight:3.6});l.bringToFront()}else l.setStyle(layerStyle(id));
document.querySelectorAll('.pt[data-id="'+id+'"]').forEach(e=>e.classList.toggle('hot',on))}
function restyle(){blocks.setStyle(f=>styleOf(f.properties));if(sel){byId[sel].setStyle(layerStyle(sel));byId[sel].bringToFront()}
document.getElementById('lgbody').innerHTML=MODE[cur].leg()}
function select(id,zoom){sel=id;restyle();const l=byId[id];l.bindPopup(popup(l.feature.properties),{maxHeight:isMobile?Math.round(document.getElementById('map').clientHeight*0.45)-24:300,maxWidth:isMobile?230:300,autoPanPaddingTopLeft:isMobile?[8,66]:[5,5],keepInView:true}).openPopup(l.getBounds().getCenter());
l.once('popupclose',()=>{if(sel===id){sel=null;l.setStyle(layerStyle(id))}});if(zoom)map.fitBounds(l.getBounds(),{maxZoom:16,padding:[50,50]})}
const sch=L.layerGroup();L.geoJSON(D.schools,{pointToLayer:(f,ll)=>L.marker(ll,{icon:L.divIcon({className:'',iconSize:[22,22],iconAnchor:[11,11],
html:'<div style="font-size:'+(f.properties.basic?24:15)+'px;line-height:22px;text-align:center;color:'+(f.properties.basic?'#d73027':'#111')+';text-shadow:0 0 3px #fff,0 0 3px #fff">'+(f.properties.basic?'&#9733;':'&#9650;')+'</div>'})}).bindPopup('<b>'+f.properties.name+'</b><br>'+f.properties.kind+'<br>Pupils 2026: '+f.properties.students+'<br>'+f.properties.address)}).addTo(sch);
const stTxt={no_osm_pair:'no OSM pair',no_etak_tag:'no maaamet:ETAK tag',etak_id_in_town_layer:'ETAK id is in the official town layer',etak_id_in_bbox_only:'ETAK id only outside the town',absent_from_official_data:'ETAK id is in no official building: possibly demolished, not verified'};
const q2g={official:L.layerGroup(),osm:L.layerGroup(),absent:L.layerGroup()},cv=L.canvas({padding:.5});
D.points.forEach(p=>{L.circleMarker([p[1],p[0]],{renderer:cv,radius:p[2]==='absent'?6:4.5,color:'#fff',weight:1,fillColor:QC[p[2]],fillOpacity:.95}).bindPopup('<b>'+(p[2]==='official'?'Official':'OSM')+' building '+p[5]+'</b><br>'+C.kinds[p[3]]+'<br>'+stTxt[p[4]]).addTo(q2g[p[2]])});
function apply(sec){cur=state.mode[sec];sel=null;map.closePopup();restyle();
map[sec==='schools'?'addLayer':'removeLayer'](sch);Object.keys(q2g).forEach(k=>map[sec==='q2'&&state.q2[k]?'addLayer':'removeLayer'](q2g[k]))}
let fitted=false;function fit(){map.invalidateSize();if(!fitted){map.fitBounds(blocks.getBounds(),{padding:[4,4]});fitted=true}}
fit();window.addEventListener('load',()=>{fitted=false;fit()});
if(window.ResizeObserver)new ResizeObserver(()=>map.invalidateSize()).observe(document.getElementById('map'));
// controls inside the sections
function syncMorph(k){const r=document.querySelector('input[name="morphchart"][value="'+k+'"]');if(r)r.checked=true;
document.querySelectorAll('.morphchart').forEach(d=>d.hidden=d.dataset.k!==k)}
document.addEventListener('change',e=>{const t=e.target;
if(t.name&&t.name.indexOf('mode-')===0){const sec=t.name.slice(5);state.mode[sec]=t.value;state.active=sec;apply(sec);
if(sec==='density'&&(t.value==='spacematrix'||t.value==='strelka'))syncMorph(t.value==='spacematrix'?'sm':'st')}
if(t.name==='morphchart'){syncMorph(t.value);const v=t.value==='sm'?'spacematrix':'strelka';state.mode.density=v;
const r=document.querySelector('input[name="mode-density"][value="'+v+'"]');if(r)r.checked=true;state.active='density';apply('density')}
if(t.dataset&&t.dataset.q2){state.q2[t.dataset.q2]=t.checked;if(state.active==='q2')map[t.checked?'addLayer':'removeLayer'](q2g[t.dataset.q2])}});
// link between the charts and the map
document.addEventListener('mouseover',e=>{const c=e.target.closest&&e.target.closest('.chart .pt');if(c)hot(+c.dataset.id,true)});
document.addEventListener('mouseout',e=>{const c=e.target.closest&&e.target.closest('.chart .pt');if(c)hot(+c.dataset.id,false)});
document.addEventListener('focusin',e=>{const c=e.target.closest&&e.target.closest('.chart .pt');if(c)hot(+c.dataset.id,true)});
document.addEventListener('focusout',e=>{const c=e.target.closest&&e.target.closest('.chart .pt');if(c)hot(+c.dataset.id,false)});
document.addEventListener('click',e=>{const c=e.target.closest&&e.target.closest('.chart .pt');if(c){if(isMobile)closeSheet();select(+c.dataset.id,true)}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('pt')){e.preventDefault();select(+e.target.dataset.id,true)}});
// scroll: the section in the middle of the screen drives the map and the menu
const links=[...document.querySelectorAll('nav.top a')];
function mark(id){links.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+id))}
let io=null;
function observe(){if(io)io.disconnect();const mob=window.matchMedia('(max-width:999px)').matches;
io=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;const id=e.target.id;mark(id);
if(SECMODE[id]&&state.active!==id){state.active=id;apply(id)}}),{rootMargin:mob?'-46% 0px -40% 0px':'-40% 0px -50% 0px'});
document.querySelectorAll('#overview,.textcol section,#details').forEach(s=>io.observe(s))}
window.matchMedia('(max-width:999px)').addEventListener('change',()=>location.reload());
if(!isMobile)observe();
// phone: map on top, strip of section cards at the bottom, bottom sheet with the rest
function initApp(){
const ids=['landuse','population','density','access','schools','q2','details'];
document.body.classList.add('cover');
const bar=document.createElement('div');bar.className='appbar';bar.innerHTML='<div class="stripwrap"><div class="strip" id="strip"></div></div><div class="dots" id="dots"></div>';document.body.appendChild(bar);
const sheet=document.createElement('div');sheet.id='sheet';sheet.setAttribute('role','dialog');sheet.setAttribute('aria-label','More');
sheet.innerHTML='<div class="grab"><span class="handle"></span><b class="stitle"></b><button type="button" class="sclose" aria-label="Close">Close</button></div><div class="sbody" id="sbody"></div>';document.body.appendChild(sheet);
const st=bar.querySelector('#strip'),dots=bar.querySelector('#dots'),sb=sheet.querySelector('#sbody');
ids.forEach((id,k)=>{const s=document.getElementById(id),d=JSON.parse(s.dataset.card),c=document.createElement('div');c.className='appcard';c.dataset.id=id;
c.innerHTML='<div class="ct">'+d.title+'</div><p class="cl">'+d.lead+'</p><div class="ck">'+d.kpi.map(x=>'<div class="kpi"><b>'+x[0]+'</b><span>'+x[1]+'</span></div>').join('')+'</div><div class="cm"></div><button type="button" class="rm" data-open="'+id+'">Read more</button>';
const m=s.querySelector('.modes3');if(m)c.querySelector('.cm').appendChild(m);else c.querySelector('.cm').remove();
st.appendChild(c);const b=document.createElement('button');b.type='button';b.setAttribute('aria-label',d.title);b.dataset.k=k;dots.appendChild(b)});
let curK=-1;
function setCard(k){if(k===curK)return;curK=k;dots.querySelectorAll('button').forEach((b,i)=>b.classList.toggle('on',i===k));const id=ids[k];if(SECMODE[id]){state.active=id;apply(id)}}
function go(k){k=Math.max(0,Math.min(ids.length-1,k));const c=st.children[k],left=c.offsetLeft-(st.clientWidth-c.offsetWidth)/2;try{st.scrollTo({left:left,behavior:'smooth'})}catch(e){st.scrollLeft=left}}
let t=null;st.addEventListener('scroll',()=>{clearTimeout(t);t=setTimeout(()=>{const mid=st.scrollLeft+st.clientWidth/2;let best=0,bd=1e9;[...st.children].forEach((c,i)=>{const d=Math.abs(c.offsetLeft+c.offsetWidth/2-mid);if(d<bd){bd=d;best=i}});setCard(best)},50)},{passive:true});
dots.addEventListener('click',e=>{const b=e.target.closest('button');if(b)go(+b.dataset.k)});
setCard(0);
let held=[],timer=null;
function restore(){clearTimeout(timer);held.reverse().forEach(h=>{h[0].classList.remove('insheet');h[1].insertBefore(h[0],h[2])});held=[]}
function openSheet(id){restore();const s=document.getElementById(id),nodes=[s];
nodes.forEach(n=>{held.push([n,n.parentNode,n.nextSibling]);n.classList.add('insheet');sb.appendChild(n)});
sheet.querySelector('.stitle').textContent=JSON.parse(s.dataset.card).title;sb.scrollTop=0;sheet.classList.add('vis');requestAnimationFrame(()=>requestAnimationFrame(()=>sheet.classList.add('open')))}
closeSheet=function(){if(!sheet.classList.contains('vis'))return;sheet.classList.remove('open');clearTimeout(timer);timer=setTimeout(()=>{restore();sheet.classList.remove('vis')},300)};
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('[data-open]');if(b)openSheet(b.dataset.open)});
sheet.querySelector('.sclose').addEventListener('click',closeSheet);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeSheet()});
let y0=null;
sheet.addEventListener('touchstart',e=>{y0=(e.target.closest('.grab')||sb.scrollTop<=0)?e.touches[0].clientY:null},{passive:true});
sheet.addEventListener('touchmove',e=>{if(y0==null)return;const dy=e.touches[0].clientY-y0;if(dy>0){sheet.style.transition='none';sheet.style.transform='translateY('+dy+'px)'}},{passive:true});
sheet.addEventListener('touchend',e=>{if(y0==null)return;const dy=e.changedTouches[0].clientY-y0;sheet.style.transition='';sheet.style.transform='';y0=null;if(dy>90)closeSheet()});
const ex=document.createElement('div');ex.className='explore';ex.innerHTML='<button type="button" class="exbtn">Explore the map &rarr;</button>';document.getElementById('overview').after(ex);
const ab=document.createElement('button');ab.type='button';ab.className='aboutbtn';ab.textContent='About';document.querySelector('.mapwrap').appendChild(ab);L.DomEvent.disableClickPropagation(ab);
function setApp(on){document.body.classList.toggle('app',on);document.documentElement.classList.toggle('app',on);document.body.classList.toggle('cover',!on);
window.scrollTo(0,0);if(on){map.invalidateSize();fitted=false;fit();restyle()}else closeSheet()}
ex.querySelector('button').addEventListener('click',()=>setApp(true));ab.addEventListener('click',()=>setApp(false))}
if(isMobile)initApp();
apply('landuse');state.active='landuse';
})();
"""

hero3 = f"""<header class="hero"><div class="wrap">
<h1>Haapsalu urban blocks</h1>
<p class="sub">A self-study GIS project: Haapsalu (Estonia) cut into urban blocks with BlocksNet and described by land use, population, density, walking accessibility and schools, plus a comparison of OpenStreetMap buildings with the official building data.</p>
<div class="meta"><span>{esc(AUTHOR)}</span><span>October 2026</span><a class="btn" href="{REPO_URL}">Code on GitHub</a></div>
</div></header>"""
CSS3 += ('#details::before,.story::before{content:"";display:block;height:16px;background:url(' + LACE + ') repeat-x center;margin:0 0 26px}')
page3 = f"""<!doctype html>
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
{CSS2}
{CSS3}
</style>
</head>
<body>
{hero3}
<nav class="top" aria-label="Sections"><div class="wrap">{nav_html}</div></nav>
<section id="overview" data-card="{CARDS['overview']}"><div class="wrap">
<div class="cards top">{cards_html}</div>
<h2>Key findings</h2>
<ul class="kf">{''.join('<li>' + hl(x) + '</li>' for x in FINDINGS)}</ul>
</div></section>
<div class="story">
<div class="mapcol"><div class="mapwrap"><div id="map" aria-label="Map of the urban blocks"></div><div class="maplegend" id="maplegend"><button type="button" class="lgbtn" aria-expanded="false">Legend</button><div class="lgbody" id="lgbody"></div></div></div></div>
<div class="textcol">{story_html}</div>
</div>
<section id="details" data-card="{CARDS['details']}"><div class="wrap"><h2>Details</h2>
{details_html}
</div></section>
<footer><div class="wrap">{esc(AUTHOR)} · self-study project · October 2026</div></footer>
<script id="data" type="application/json">{data2}</script>
<script>
{leaflet_js}
</script>
<script>
{JS3}
</script>
</body>
</html>
"""
out = ROOT / "dashboard.html"
out.write_text(page3, encoding="utf-8")
docs = ROOT / "docs"
docs.mkdir(exist_ok=True)
shutil.copyfile(out, docs / "index.html")
(docs / ".nojekyll").write_text("", encoding="utf-8")

print(f"dashboard.html and docs/index.html: {out.stat().st_size:,} bytes (data {len(data2):,}, leaflet js+css {len(leaflet_js) + len(leaflet_css):,})")
print(f"Checks: {n_ok} of {len(checks)} agree")
w = max(len(c["name"]) for c in checks)
for c in checks:
    print(f"  {'OK       ' if c['ok'] else 'DIFFERENT'} {c['name']:<{w}}  notebook {c['nb']:>8}  dashboard {c['dash']:>8}")
if not mixed_ok:
    print("WARNING: land_use_display 'mixed' does not follow share < 0.5 everywhere")
sys.exit(0 if n_ok == len(checks) else 1)
