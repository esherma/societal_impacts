"""
Step 8: Election overlay — did 2026 midterm voting shift differently by AI exposure?

Prototype geography: King County, WA (FIPS 53033).

Question: conditional on where a place started politically (2024) and on the things
that already drive partisan swing (education, income, congressional district), did
precincts / tracts with higher AI labor-market exposure swing differently in 2026?

Construction
  outcome  swing = D two-party share, 2026 US House  −  D two-party share, 2024 President
           (2024 House is not usable as a baseline: CD-9 was D-vs-D in 2024.)
  exposure tract Bartik index from step 6 (Anthropic observed exposure × ACS occupation mix)
  snapshot both years use the ELECTION-NIGHT precinct drop, so the count stage is held
           (roughly) constant. 2026 election night is ~50% of expected final ballots vs
           ~68% in 2024 — re-run once final 2026 results post (~Nov 25).

Geographic joins (all area-weighted, in EPSG:2926 WA State Plane N, ft):
  • tract → 2026 precinct: precinct exposure / BA+ / income = worker- (or adult-)
    weighted mean of the tracts it overlaps, assuming uniform density within a tract.
  • 2024 precinct → 2026 precinct: 2024 vote counts split by share of source-precinct area.
  • precinct → tract: votes split by share of precinct area (for the tract-level model).

Inference is done at the TRACT level (n≈495), because exposure is only measured at the
tract; precinct-level regressions would treat interpolated copies of the same tract value
as independent observations.

Outputs
  data/processed/king_precinct_overlay.parquet
  data/processed/king_tract_overlay.parquet
  src/map/data/elections/king_2026.json    (precinct + tract GeoJSON, model results)
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

ROOT = Path(__file__).parent.parent.parent
CACHE = ROOT / "data" / "raw" / "_cache" / "elections"
PROC_DIR = ROOT / "data" / "processed"
MAP_OUT = ROOT / "src" / "map" / "data" / "elections"
MAP_OUT.mkdir(parents=True, exist_ok=True)

COUNTY = "53033"
CRS_FT = 2926
SNAP_26 = "election_night"
SNAP_24 = "election_night"

PRES_24 = "President and Vice President of the United States President and Vice President of the United States"
HARRIS, TRUMP = "Kamala D. Harris / Tim Walz", "Donald J. Trump / JD Vance"


# ── Results parsing ────────────────────────────────────────────────────────
def parse_2026(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d[d["Precinct"] != "ELECTIONS OFFICE"]
    house = d[d["Race"].str.contains("United States Representative", na=False)]
    party = house["Party"].fillna("")
    g = house.assign(
        dem=np.where(party.str.contains("Democratic") & (house["CounterGroup"] == "Total"), house["SumOfCount"], 0),
        rep=np.where(party.str.contains("Republican") & (house["CounterGroup"] == "Total"), house["SumOfCount"], 0),
        bal=np.where(house["CounterType"] == "Times Counted", house["SumOfCount"], 0),
        reg=np.where(house["CounterType"] == "Registered Voters", house["SumOfCount"], 0),
    ).groupby("Precinct").agg(
        dem=("dem", "sum"), rep=("rep", "sum"), bal=("bal", "sum"), reg=("reg", "sum"),
        cd=("CongressionalDistrict", "first"),
    )
    # Sanity: every House race in King County must be exactly one D vs one R
    cands = house[party.str.contains("Democratic|Republican")].groupby("Race")["Party"].nunique()
    assert (cands == 2).all(), f"2026 House races not all D-vs-R: {cands.to_dict()}"
    return g


def parse_2024(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d[(d["Precinct"] != "ELECTIONS OFFICE") & (d["Race"] == PRES_24)]
    return d.assign(
        dem=np.where(d["CounterType"] == HARRIS, d["SumOfCount"], 0),
        rep=np.where(d["CounterType"] == TRUMP, d["SumOfCount"], 0),
        bal=np.where(d["CounterType"] == "Times Counted", d["SumOfCount"], 0),
        reg=np.where(d["CounterType"] == "Registered Voters", d["SumOfCount"], 0),
    ).groupby("Precinct")[["dem", "rep", "bal", "reg"]].sum()


# ── Geometry helpers ───────────────────────────────────────────────────────
def load_precincts(year: int) -> gpd.GeoDataFrame:
    g = gpd.read_file(CACHE / f"king_votdst_{year}.geojson").to_crs(CRS_FT)
    g["geometry"] = g.geometry.make_valid()
    g = g.dissolve(by="NAME", as_index=False)  # a few precincts are multipart
    g["p_area"] = g.area
    return g[["NAME", "votdst", "geometry", "p_area"]]


def load_tracts() -> gpd.GeoDataFrame:
    t = gpd.read_file(f"zip://{CACHE / 'tl_2024_53_tract.zip'}")
    t = t[t["COUNTYFP"] == COUNTY[2:]].to_crs(CRS_FT)
    ex = pd.read_parquet(PROC_DIR / "tract_exposure.parquet")
    t = t.merge(ex, left_on="GEOID", right_on="geoid", how="left")
    t["t_area"] = t.area
    return t


def intersect(a: gpd.GeoDataFrame, b: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    x = gpd.overlay(a, b, how="intersection", keep_geom_type=True)
    x["x_area"] = x.area
    return x


def wavg(df, val, w):
    m = df[val].notna() & (df[w] > 0)
    return (df.loc[m, val] * df.loc[m, w]).sum() / df.loc[m, w].sum() if m.any() else np.nan


# ── Regression (weighted least squares, HC1 SEs) ───────────────────────────
def wls(y, X, w, names):
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1) & np.isfinite(w) & (w > 0)
    y, X, w = y[m], X[m], w[m]
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], y * sw
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = yw - Xw @ beta
    n, k = Xw.shape
    bread = np.linalg.pinv(Xw.T @ Xw)
    meat = (Xw * resid[:, None]).T @ (Xw * resid[:, None])
    V = bread @ meat @ bread * n / (n - k)
    se = np.sqrt(np.diag(V))
    r2 = 1 - (resid ** 2).sum() / (((yw - np.average(y, weights=w) * sw) ** 2).sum())
    return {"n": int(n), "r2": round(float(r2), 3),
            "coef": {nm: [round(float(b), 5), round(float(s), 5)] for nm, b, s in zip(names, beta, se)}}


def residualize(v, Z, w):
    m = np.all(np.isfinite(Z), axis=1) & np.isfinite(v)
    out = np.full_like(v, np.nan, dtype=float)
    sw = np.sqrt(w[m])
    b, *_ = np.linalg.lstsq(Z[m] * sw[:, None], v[m] * sw, rcond=None)
    out[m] = v[m] - Z[m] @ b
    return out


def binscatter(x, y, w, nbins=20):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(w)
    x, y, w = x[m], y[m], w[m]
    edges = np.quantile(x, np.linspace(0, 1, nbins + 1))
    idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, nbins - 1)
    return [{"x": round(float(np.average(x[idx == i], weights=w[idx == i])), 5),
             "y": round(float(np.average(y[idx == i], weights=w[idx == i])), 5),
             "n": int((idx == i).sum())}
            for i in range(nbins) if (idx == i).any()]


def main():
    print("Loading results…")
    r26 = parse_2026(CACHE / f"king_2026_{SNAP_26}.csv")
    r24 = parse_2024(CACHE / f"king_2024_{SNAP_24}.csv")
    print(f"  2026 ({SNAP_26}): {len(r26):,} precincts, {r26['bal'].sum():,} ballots, "
          f"House D2P {r26['dem'].sum() / (r26['dem'].sum() + r26['rep'].sum()):.3f}")
    print(f"  2024 ({SNAP_24}): {len(r24):,} precincts, {r24['bal'].sum():,} ballots, "
          f"Pres D2P {r24['dem'].sum() / (r24['dem'].sum() + r24['rep'].sum()):.3f}")

    print("Loading geometry…")
    p26 = load_precincts(2026).merge(r26, left_on="NAME", right_index=True, how="left")
    p24 = load_precincts(2024).merge(r24, left_on="NAME", right_index=True, how="left")
    tr = load_tracts()
    print(f"  {len(p26):,} 2026 precincts, {len(p24):,} 2024 precincts, {len(tr):,} tracts")

    # ── 2024 votes → 2026 precincts ─────────────────────────────────────
    x = intersect(p24[["NAME", "geometry", "p_area", "dem", "rep", "bal", "reg"]].rename(columns={"NAME": "src"}),
                  p26[["NAME", "geometry"]])
    frac = x["x_area"] / x["p_area"]
    for c in ["dem", "rep", "bal", "reg"]:
        x[c + "24"] = x[c] * frac
    v24 = x.groupby("NAME")[["dem24", "rep24", "bal24", "reg24"]].sum()
    p26 = p26.merge(v24, left_on="NAME", right_index=True, how="left")
    unchanged = p26["NAME"].isin(p24["NAME"]).mean()
    print(f"  2024→2026 interpolation: {unchanged:.0%} of 2026 precinct names also existed in 2024")

    # ── Tract attributes → 2026 precincts ───────────────────────────────
    tcols = ["GEOID", "geometry", "t_area", "exposure", "workers", "ba_plus", "adults_25p", "median_hh_income"]
    xt = intersect(tr[tcols], p26[["NAME", "geometry"]])
    xt["w_workers"] = xt["workers"] * xt["x_area"] / xt["t_area"]
    xt["w_adults"] = xt["adults_25p"] * xt["x_area"] / xt["t_area"]
    attrs = xt.groupby("NAME").apply(lambda g: pd.Series({
        "exposure": wavg(g, "exposure", "w_workers"),
        "ba_plus": wavg(g, "ba_plus", "w_adults"),
        "median_hh_income": wavg(g, "median_hh_income", "w_adults"),
        "main_tract": g.loc[g["x_area"].idxmax(), "GEOID"],
    }), include_groups=False)
    p26 = p26.merge(attrs, left_on="NAME", right_index=True, how="left")

    p26["d2p26"] = p26["dem"] / (p26["dem"] + p26["rep"])
    p26["d2p24"] = p26["dem24"] / (p26["dem24"] + p26["rep24"])
    p26["swing"] = p26["d2p26"] - p26["d2p24"]
    p26["turnout26"] = p26["bal"] / p26["reg"]
    p26["turnout24"] = p26["bal24"] / p26["reg24"]

    # ── Precinct votes → tracts (inference unit) ────────────────────────
    def to_tracts(pre, cols, suffix):
        xx = intersect(pre[["NAME", "geometry", "p_area"] + cols], tr[["GEOID", "geometry"]])
        f = xx["x_area"] / xx["p_area"]
        for c in cols:
            xx[c] = xx[c] * f
        return xx.groupby("GEOID")[cols].sum().add_suffix(suffix)

    t26 = to_tracts(p26.assign(cdn=1), ["dem", "rep", "bal", "reg"], "26")
    t24 = to_tracts(p24, ["dem", "rep", "bal", "reg"], "24")
    # Congressional district: the CD holding most of the tract's 2026 ballots
    xcd = intersect(p26[["NAME", "geometry", "p_area", "bal", "cd"]], tr[["GEOID", "geometry"]])
    xcd["b"] = xcd["bal"] * xcd["x_area"] / xcd["p_area"]
    tcd = xcd.groupby(["GEOID", "cd"])["b"].sum().reset_index().sort_values("b").drop_duplicates("GEOID", keep="last")

    T = (tr.drop(columns="geometry").set_index("GEOID")
           .join(t26).join(t24).join(tcd.set_index("GEOID")["cd"]))
    T["d2p26"] = T["dem26"] / (T["dem26"] + T["rep26"])
    T["d2p24"] = T["dem24"] / (T["dem24"] + T["rep24"])
    T["swing"] = T["d2p26"] - T["d2p24"]
    T["turnout26"] = T["bal26"] / T["reg26"]
    T["turnout24"] = T["bal24"] / T["reg24"]
    T["turnout_ratio"] = T["turnout26"] / T["turnout24"]
    T = T[(T["bal26"] >= 50) & (T["workers"] >= 200) & T["exposure"].notna()]
    print(f"  {len(T):,} tracts in the analysis sample")

    # ── Models ─────────────────────────────────────────────────────────
    ez = (T["exposure"] - T["exposure"].mean()) / T["exposure"].std()
    w = T["bal26"].to_numpy(float)
    cds = sorted(T["cd"].dropna().unique())
    cd_fe = np.column_stack([(T["cd"] == c).astype(float) for c in cds[1:]])
    one = np.ones(len(T))
    controls = np.column_stack([T["ba_plus"], np.log(T["median_hh_income"]), T["d2p24"], cd_fe])
    ctrl_names = ["ba_plus", "log_income", "d2p24_baseline"] + [f"cd_{int(c)}" for c in cds[1:]]

    models = {}
    for outcome in ["swing", "turnout_ratio"]:
        y = T[outcome].to_numpy(float)
        models[outcome] = {
            "bivariate": wls(y, np.column_stack([one, ez]), w, ["const", "exposure_sd"]),
            "education_only": wls(y, np.column_stack([one, ez, T["ba_plus"]]), w,
                                  ["const", "exposure_sd", "ba_plus"]),
            "full": wls(y, np.column_stack([one, ez, controls]), w, ["const", "exposure_sd"] + ctrl_names),
        }
    for outcome, ms in models.items():
        print(f"\n  {outcome}: effect of +1 SD exposure")
        for k, m in ms.items():
            b, s = m["coef"]["exposure_sd"]
            print(f"    {k:<15s} {b:+.4f} (SE {s:.4f})  n={m['n']}  R²={m['r2']}")

    # Binned scatters: raw, and Frisch–Waugh residualized on the full control set
    Z = np.column_stack([one, controls])
    sw_ = T["swing"].to_numpy(float)
    ex_ = T["exposure"].to_numpy(float)
    bins = {
        "raw": binscatter(ex_, sw_, w),
        "residualized": binscatter(residualize(ex_, Z, w) + np.average(ex_, weights=w),
                                   residualize(sw_, Z, w) + np.average(sw_, weights=w), w),
    }

    # ── Save tabular outputs ───────────────────────────────────────────
    pcols = ["NAME", "votdst", "cd", "main_tract", "exposure", "ba_plus", "median_hh_income",
             "dem", "rep", "bal", "reg", "dem24", "rep24", "bal24", "reg24",
             "d2p26", "d2p24", "swing", "turnout26", "turnout24"]
    p26[pcols].to_parquet(PROC_DIR / "king_precinct_overlay.parquet", index=False)
    T.reset_index().drop(columns=[c for c in T.columns if c.startswith("sh_")]) \
        .to_parquet(PROC_DIR / "king_tract_overlay.parquet", index=False)

    # ── Map export ─────────────────────────────────────────────────────
    def r(v, n=4):
        return None if v is None or not np.isfinite(v) else round(float(v), n)

    def geo(gdf, props_fn, tol):
        g = gdf.copy()
        g["geometry"] = g.geometry.simplify(tol, preserve_topology=True)
        g = g.to_crs(4326)
        # d3-geo is spherical and wants CLOCKWISE exterior rings (the opposite of RFC 7946);
        # counter-clockwise rings render as "the whole globe minus this polygon".
        g["geometry"] = shapely.orient_polygons(g.geometry.values, exterior_cw=True)
        feats = []
        for _, row in g.iterrows():
            gj = json.loads(gpd.GeoSeries([row.geometry]).to_json(to_wgs84=False))["features"][0]["geometry"]
            feats.append({"type": "Feature", "properties": props_fn(row), "geometry": gj})
        fc = {"type": "FeatureCollection", "features": feats}
        return json.loads(json.dumps(fc), parse_float=lambda s: round(float(s), 5))

    precinct_fc = geo(p26, lambda x: {
        "id": x["NAME"], "cd": None if pd.isna(x["cd"]) else int(x["cd"]),
        "e": r(x["exposure"]), "ba": r(x["ba_plus"], 3), "inc": r(x["median_hh_income"], 0),
        "d26": int(x["dem"]) if pd.notna(x["dem"]) else None,
        "r26": int(x["rep"]) if pd.notna(x["rep"]) else None,
        "b26": int(x["bal"]) if pd.notna(x["bal"]) else None,
        "d2p26": r(x["d2p26"]), "d2p24": r(x["d2p24"]), "sw": r(x["swing"]),
        "to26": r(x["turnout26"], 3), "to24": r(x["turnout24"], 3),
    }, tol=40)

    trg = tr.set_index("GEOID").join(T[["d2p26", "d2p24", "swing", "turnout_ratio", "bal26", "cd"]], how="inner")
    tract_fc = geo(trg.reset_index(), lambda x: {
        "id": x["GEOID"], "e": r(x["exposure"]), "ba": r(x["ba_plus"], 3),
        "inc": r(x["median_hh_income"], 0), "w": int(x["workers"]),
        "d2p26": r(x["d2p26"]), "d2p24": r(x["d2p24"]), "sw": r(x["swing"]),
        "tr": r(x["turnout_ratio"], 3), "b26": r(x["bal26"], 0),
    }, tol=40)

    county_d26 = r26["dem"].sum() / (r26["dem"].sum() + r26["rep"].sum())
    county_d24 = r24["dem"].sum() / (r24["dem"].sum() + r24["rep"].sum())
    payload = {
        "meta": {
            "jurisdiction": "King County, WA",
            "snapshot_2026": SNAP_26, "snapshot_2024": SNAP_24,
            "ballots_2026": int(r26["bal"].sum()), "ballots_2024": int(r24["bal"].sum()),
            "registered_2026": int(r26["reg"].sum()),
            "county_d2p26_house": r(county_d26), "county_d2p24_pres": r(county_d24),
            "county_swing": r(county_d26 - county_d24),
            "exposure_sd": r(T["exposure"].std(), 5), "exposure_mean": r(T["exposure"].mean(), 5),
            "corr_exposure_ba": r(T[["exposure", "ba_plus"]].corr().iloc[0, 1], 3),
            "n_tracts": int(len(T)), "n_precincts": int(len(p26)),
            "acs": "ACS 2020–2024 5-year (C24010, B15003, B19013)",
        },
        "models": models,
        "bins": bins,
        "precincts": precinct_fc,
        "tracts": tract_fc,
    }
    out = MAP_OUT / "king_2026.json"
    out.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"\nSaved {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
