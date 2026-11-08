"""
Step 8: How much does the county map hide? Within- vs between-county variance in exposure.

Uses the national tract file (steps 6–7). For each index (AI, robot), decomposes the
worker-weighted variance across tracts into
    total = between-county (variance of county means) + within-county (tracts around their county mean)

ACS sampling noise. Tract estimates are noisy, and noise lands entirely in the "within" term,
so the raw within share overstates real within-county variation. We estimate each tract's
sampling variance from the C24010 margins of error (delta method, independent cells):
    x = Σ_k s_k e_k,  ∂x/∂n_k = (e_k − x) / N,  Var(n_k) = (MOE_male/1.645)² + (MOE_female/1.645)²
and subtract the worker-weighted mean noise variance from the within term. Covariances
between cells are ignored, so treat the adjusted figure as approximate.

Outputs
  data/processed/geographic_variance.json        decomposition (overall + by county size class)
  data/processed/county_within_spread.parquet    per-county noise-adjusted within-county SD
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent.parent
CACHE = ROOT / "data" / "raw" / "_cache"
PROC_DIR = ROOT / "data" / "processed"

_spec = importlib.util.spec_from_file_location("acs02", Path(__file__).parent / "02_download_acs.py")
_acs02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_acs02)
OCC_CATEGORIES = _acs02.OCC_CATEGORIES

MIN_WORKERS = 200          # drop near-empty tracts (prisons, parks, airports)
MIN_TRACTS_FOR_RANKING = 20


def tract_moes() -> pd.DataFrame:
    """Per-tract variance of each of the 25 category counts, from the cached C24010 file."""
    cols = []
    for m, f, _, _ in OCC_CATEGORIES:
        cols += [f"C24010_M{m:03d}", f"C24010_M{f:03d}"]
    keep = []
    for chunk in pd.read_csv(CACHE / "acsdt5y2024-c24010.dat", sep="|",
                             usecols=["GEO_ID"] + cols, dtype=str, chunksize=200_000):
        keep.append(chunk[chunk["GEO_ID"].str.startswith("1400000US")])
    df = pd.concat(keep, ignore_index=True)
    out = pd.DataFrame({"geoid": df["GEO_ID"].str[9:]})
    for i, (m, f, _, _) in enumerate(OCC_CATEGORIES):
        se_m = pd.to_numeric(df[f"C24010_M{m:03d}"], errors="coerce").clip(lower=0) / 1.645
        se_f = pd.to_numeric(df[f"C24010_M{f:03d}"], errors="coerce").clip(lower=0) / 1.645
        out[f"v_{i:02d}"] = (se_m ** 2 + se_f ** 2).to_numpy()
    return out


def decompose(df: pd.DataFrame, x: str, noise: str) -> dict:
    w = df["workers"].astype(float)
    mu = np.average(df[x], weights=w)
    cm = df.groupby("county_fips5").apply(lambda g: np.average(g[x], weights=g["workers"]),
                                          include_groups=False)
    dev_within = df[x] - df["county_fips5"].map(cm)
    total = np.average((df[x] - mu) ** 2, weights=w)
    within = np.average(dev_within ** 2, weights=w)
    between = total - within
    mean_noise = np.average(df[noise], weights=w)
    within_adj = max(within - mean_noise, 0.0)
    total_adj = between + within_adj
    return {
        "n_tracts": int(len(df)), "n_counties": int(df["county_fips5"].nunique()),
        "sd_total": float(np.sqrt(total)), "sd_noise": float(np.sqrt(mean_noise)),
        "within_share_raw": float(within / total),
        "within_share_adj": float(within_adj / total_adj),
        "noise_share_of_total": float(mean_noise / total),
    }


def main():
    tr = pd.read_parquet(PROC_DIR / "tract_exposure.parquet")
    cat = pd.read_csv(PROC_DIR / "occ_category_scores.csv")
    # 50 states + DC, matching the map (Puerto Rico excluded)
    tr = tr[(tr["workers"] >= MIN_WORKERS) & tr["exposure"].notna() & (tr["state_fips"] != "72")].copy()
    tr = tr.merge(tract_moes(), on="geoid", how="left")
    print(f"{len(tr):,} tracts with ≥{MIN_WORKERS} workers in {tr['county_fips5'].nunique():,} counties")

    sh = tr[[f"sh_{i:02d}" for i in range(25)]].to_numpy()
    V = tr[[f"v_{i:02d}" for i in range(25)]].to_numpy()
    N = tr["workers"].to_numpy(float)
    for idx, col, score_col in [("ai", "exposure", "ai_unweighted"), ("robot", "robot", "robot_unweighted")]:
        e = cat[score_col].to_numpy()
        x = sh @ e
        grad = (e[None, :] - x[:, None]) / N[:, None]
        tr[f"noise_{idx}"] = np.nansum(grad ** 2 * V, axis=1)
        tr[f"x_{idx}"] = tr[col]

    # County size classes by total workers
    cw = tr.groupby("county_fips5")["workers"].sum()
    size = pd.cut(cw, [0, 25_000, 100_000, 500_000, np.inf],
                  labels=["<25k workers", "25k–100k", "100k–500k", "500k+"])
    tr["size_class"] = tr["county_fips5"].map(size)

    results = {}
    for idx in ["ai", "robot"]:
        res = {"overall": decompose(tr, f"x_{idx}", f"noise_{idx}"), "by_size": {}}
        for cls, g in tr.groupby("size_class", observed=True):
            if g["county_fips5"].nunique() >= 5:
                res["by_size"][str(cls)] = decompose(g, f"x_{idx}", f"noise_{idx}")
        results[idx] = res
        o = res["overall"]
        print(f"\n{idx.upper()}: within-county share of tract variance "
              f"{o['within_share_raw']:.0%} raw → {o['within_share_adj']:.0%} after removing "
              f"sampling noise (noise = {o['noise_share_of_total']:.0%} of total)")
        for cls, r in res["by_size"].items():
            print(f"   {cls:<14s} counties={r['n_counties']:>4}  within {r['within_share_raw']:.0%} → "
                  f"{r['within_share_adj']:.0%}")

    # Per-county noise-adjusted within SD
    def county_spread(g):
        w = g["workers"]
        out = {"n_tracts": len(g), "workers": int(w.sum())}
        for idx in ["ai", "robot"]:
            m = np.average(g[f"x_{idx}"], weights=w)
            raw = np.average((g[f"x_{idx}"] - m) ** 2, weights=w)
            noise = np.average(g[f"noise_{idx}"], weights=w)
            out[f"mean_{idx}"] = m
            out[f"sd_{idx}_raw"] = np.sqrt(raw)
            out[f"sd_{idx}"] = np.sqrt(max(raw - noise, 0))
            out[f"p90_p10_{idx}"] = (g[f"x_{idx}"].quantile(.9) - g[f"x_{idx}"].quantile(.1))
        return pd.Series(out)

    spread = tr.groupby("county_fips5").apply(county_spread, include_groups=False)
    spread.reset_index().rename(columns={"county_fips5": "fips"}).to_parquet(
        PROC_DIR / "county_within_spread.parquet", index=False)

    names = pd.read_parquet(ROOT / "data" / "raw" / "acs_county_occupations_tidy.parquet") \
        .groupby("fips")["county_name"].first()
    big = spread[spread["n_tracts"] >= MIN_TRACTS_FOR_RANKING].join(names)
    top = {}
    for idx in ["ai", "robot"]:
        t = big.sort_values(f"sd_{idx}", ascending=False).head(15)
        top[idx] = [{"fips": f, "county": r["county_name"], "n_tracts": int(r["n_tracts"]),
                     "sd": round(float(r[f"sd_{idx}"]), 5), "mean": round(float(r[f"mean_{idx}"]), 5)}
                    for f, r in t.iterrows()]
        print(f"\nMost internally divided on {idx.upper()} (≥{MIN_TRACTS_FOR_RANKING} tracts, noise-adjusted SD):")
        for r in top[idx][:10]:
            print(f"   {r['county']:<40s} sd={r['sd']:.4f}  mean={r['mean']:.4f}  tracts={r['n_tracts']}")
    results["most_divided"] = top
    results["notes"] = {"min_workers_per_tract": MIN_WORKERS, "acs": "2020–2024 5-year C24010"}

    (PROC_DIR / "geographic_variance.json").write_text(json.dumps(results, indent=2, default=float))
    print(f"\nSaved geographic_variance.json, county_within_spread.parquet")


if __name__ == "__main__":
    main()
