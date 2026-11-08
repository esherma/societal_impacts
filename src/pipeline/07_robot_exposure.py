"""
Step 7: Physical (robot) exposure index alongside the AI index, at county and tract level.

Source: Anthropic, "What work can robots do?" (Sept 30 2026), HuggingFace
  Anthropic/EconomicIndex/robot_exposure/robot_exposure_occupations.csv
  robot_exposure_index: 0–3, time-share-weighted mean of task tiers
    E0 = no robot can do it, E1 = purpose-built cell, E2 = structured facility,
    E3 = unstructured environment (homes, construction sites).

This step also fixes a known Phase 1 limitation: category scores were a SIMPLE mean over
the SOC-6 occupations in each of the 25 ACS groups, so "Logisticians" counted as much as
"Laborers and freight movers". We now also compute EMPLOYMENT-WEIGHTED category scores,
using national employment by detailed Census occupation (ACS 2024 1-year, table B24114,
~565 occupations) mapped to SOC via the Census 2018 occupation crosswalk. (BLS OEWS is the
usual source but bls.gov refuses automated downloads.) Within-group spread matters much
more for the robot index than for the AI index. The MAP keeps the original unweighted method
for both indices (so the published AI index is unchanged and the two are comparable); the
weighted versions (ai_w, robot_w) are kept for sensitivity checks.

Outputs
  data/raw/robot_exposure/robot_exposure_occupations.csv
  data/processed/soc_employment_weights.csv     SOC-6 → national employment (allocated)
  data/processed/occ_category_scores.csv        25 groups × {ai, robot} × {unweighted, emp-weighted}
  data/processed/county_dual_exposure.parquet   5-yr + 1-yr county AI & robot indices
  data/processed/tract_exposure.parquet         (adds ai_w, robot, robot_w columns in place)
"""

import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
CACHE = RAW_DIR / "_cache"
PROC_DIR = ROOT / "data" / "processed"
ROBOT_DIR = RAW_DIR / "robot_exposure"
for d in (CACHE, ROBOT_DIR, PROC_DIR):
    d.mkdir(parents=True, exist_ok=True)

HF = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main"
SF1 = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/1YRData"
B24114_VARS = "https://api.census.gov/data/2024/acs/acs1/groups/B24114.json"  # metadata: no key needed
XWALK = ("https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/"
         "2018-occupation-code-list-and-crosswalk.xlsx")

_spec = importlib.util.spec_from_file_location("acs02", Path(__file__).parent / "02_download_acs.py")
_acs02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_acs02)
OCC_CATEGORIES = _acs02.OCC_CATEGORIES


def fetch(url: str, out: Path) -> Path:
    if out.exists():
        return out
    print(f"  GET {url}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    out.write_bytes(r.content)
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def soc_prefix(code: str) -> str:
    """Census SOC codes can be broad ('13-1020') or wildcards ('47-50XX'). Return a prefix
    that matches the SOC-6 codes they contain. (Detailed SOC codes never end in 0.)"""
    code = code.strip().rstrip("X")
    if len(code) == 7 and code.endswith("0"):
        code = code.rstrip("0")
    return code


def national_soc_weights(soc6: pd.Series) -> pd.Series:
    """National employment for each SOC-6 code in `soc6`. A Census occupation covering
    several SOC-6 codes splits its employment equally among those present."""
    vars_ = json.loads(fetch(B24114_VARS, CACHE / "b24114_vars.json").read_text())["variables"]
    labels = {k[:-1]: v["label"].split("!!")[-1] for k, v in vars_.items()
              if k.startswith("B24114_") and k.endswith("E") and k != "B24114_001E"}
    dat = pd.read_csv(fetch(f"{SF1}/acsdt1y2024-b24114.dat", CACHE / "acsdt1y2024-b24114.dat"),
                      sep="|", dtype=str)
    us = dat[dat["GEO_ID"] == "0100000US"].iloc[0]
    emp = pd.DataFrame([(t, int(us[k.replace("_", "_E")])) for k, t in labels.items()],
                       columns=["title", "emp"])

    xw = pd.read_excel(fetch(XWALK, CACHE / "occ_xwalk_2018.xlsx"), "Summary of 2018 Changes",
                       header=2, dtype=str)
    xw = xw.iloc[:, :3]
    xw.columns = ["soc", "census_code", "title"]
    xw = xw.dropna(subset=["soc", "title"]).assign(k=lambda d: d["title"].map(norm))
    emp = emp.assign(k=emp["title"].map(norm)).merge(
        xw.drop_duplicates("k")[["k", "soc"]], on="k", how="left")
    missing = emp["soc"].isna().sum()
    assert missing == 0, f"{missing} B24114 occupations failed to match the crosswalk"

    socs = pd.Series(sorted(set(soc6)))
    alloc = pd.Series(0.0, index=socs)
    unassigned = 0
    for _, row in emp.iterrows():
        hit = socs[socs.str.startswith(soc_prefix(row["soc"]))]
        if hit.empty:
            unassigned += row["emp"]
            continue
        alloc[hit] += row["emp"] / len(hit)
    print(f"  national employment {emp['emp'].sum():,}; {unassigned / emp['emp'].sum():.1%} "
          f"in Census occupations with no scored SOC-6 code")
    return alloc


def category_scores(scores: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """scores: index soc6, columns ai, robot (NaN allowed). Returns 25 rows in canonical order."""
    rows = []
    for m, f, label, prefixes in OCC_CATEGORIES:
        sub = scores[scores.index.to_series().apply(lambda s: any(s.startswith(p) for p in prefixes))]
        w = weights.reindex(sub.index).fillna(0)
        row = {"occ_category": label, "n_soc": len(sub), "national_emp": int(w.sum())}
        for col in ["ai", "robot"]:
            ok = sub[col].notna()
            row[f"{col}_unweighted"] = sub.loc[ok, col].mean()
            row[f"{col}_weighted"] = np.average(sub.loc[ok, col], weights=w[ok]) if w[ok].sum() > 0 \
                else sub.loc[ok, col].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def county_index(tidy: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    labels = [label for _, _, label, _ in OCC_CATEGORIES]
    piv = tidy.pivot_table(index="fips", columns="occ_category", values="employment",
                           aggfunc="sum", fill_value=0)[labels]
    sh = piv.div(piv.sum(axis=1).replace(0, np.nan), axis=0)
    c = cat.set_index("occ_category").loc[labels]
    return pd.DataFrame({
        "workers": piv.sum(axis=1),
        "ai": sh.values @ c["ai_unweighted"].values,       # = existing map index
        "ai_w": sh.values @ c["ai_weighted"].values,
        "robot": sh.values @ c["robot_unweighted"].values,  # same method as the map's AI index
        "robot_w": sh.values @ c["robot_weighted"].values,
    }, index=piv.index)


def main():
    print("Robot exposure (HuggingFace)…")
    rob = pd.read_csv(fetch(f"{HF}/robot_exposure/robot_exposure_occupations.csv",
                            ROBOT_DIR / "robot_exposure_occupations.csv"))
    rob["soc"] = rob["onetsoc_code"].str[:7]
    robot = rob.groupby("soc")["robot_exposure_index"].mean()

    ai = pd.read_csv(RAW_DIR / "labor_market_impacts" / "job_exposure.csv",
                     dtype={"occ_code": str}).set_index("occ_code")["observed_exposure"]
    scores = pd.concat([ai.rename("ai"), robot.rename("robot")], axis=1)
    both = scores.dropna()
    print(f"  {robot.size} SOC-6 robot scores, {ai.size} AI scores, {len(both)} overlap; "
          f"occupation-level corr(AI, robot) = {both.corr().iloc[0, 1]:.2f}")

    print("National employment weights (ACS B24114 + Census 2018 crosswalk)…")
    w = national_soc_weights(scores.index.to_series())
    w.rename("national_emp").rename_axis("soc").to_csv(PROC_DIR / "soc_employment_weights.csv")

    cat = category_scores(scores, w)
    cat.to_csv(PROC_DIR / "occ_category_scores.csv", index=False)
    print("\nCategory scores (AI ×100, robot 0–3):")
    for _, r in cat.iterrows():
        print(f"  {r['occ_category'][:45]:<45s} AI {r['ai_unweighted']*100:5.1f}→{r['ai_weighted']*100:5.1f}"
              f"   robot {r['robot_unweighted']:.2f}→{r['robot_weighted']:.2f}")

    print("\nCounty indices…")
    out = []
    for name, f in [("5yr", "acs_county_occupations_tidy.parquet"), ("1yr", "acs_1yr_county_occupations_tidy.parquet")]:
        c = county_index(pd.read_parquet(RAW_DIR / f), cat).assign(dataset=name)
        out.append(c.reset_index())
        wts = c["workers"]
        rk = c[["ai", "ai_w", "robot", "robot_w"]].rank()
        print(f"  {name}: n={len(c)}  corr(AI, robot)={c[['ai', 'robot']].corr().iloc[0, 1]:.2f}  "
              f"rank corr AI unweighted vs weighted={rk[['ai', 'ai_w']].corr().iloc[0, 1]:.3f}  "
              f"robot unweighted vs weighted={rk[['robot', 'robot_w']].corr().iloc[0, 1]:.3f}")
    pd.concat(out).to_parquet(PROC_DIR / "county_dual_exposure.parquet", index=False)

    print("Tract indices…")
    tr = pd.read_parquet(PROC_DIR / "tract_exposure.parquet")
    sh = tr[[f"sh_{i:02d}" for i in range(len(OCC_CATEGORIES))]].to_numpy()
    tr["ai_w"] = np.where(tr["workers"] > 0, sh @ cat["ai_weighted"].to_numpy(), np.nan)
    tr["robot"] = np.where(tr["workers"] > 0, sh @ cat["robot_unweighted"].to_numpy(), np.nan)
    tr["robot_w"] = np.where(tr["workers"] > 0, sh @ cat["robot_weighted"].to_numpy(), np.nan)
    tr.to_parquet(PROC_DIR / "tract_exposure.parquet", index=False)
    v = tr.dropna(subset=["robot"])
    print(f"  {len(v):,} tracts; corr(AI, robot) = {v[['exposure', 'robot']].corr().iloc[0, 1]:.2f}")


if __name__ == "__main__":
    main()
