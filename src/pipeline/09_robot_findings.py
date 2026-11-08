"""
Step 9: Headline findings for the AI vs. robot exposure write-up.

Reads the outputs of steps 4, 6 and 7 (no downloads) and writes the numbers quoted in
Claude_Proposals/impact_atlas/06_robot_findings.md and on the personal-website project page.

  1. Bivariate tercile table (terciles by county COUNT; shares are of all US workers).
  2. Socioeconomic gradient across tracts: worker-weighted AI / robot exposure by
     median-household-income quintile, and tract correlations with the BA+ share.
  3. Occupation mix of AI-heavy vs. robot-heavy counties (which groups drive the split).
  4. Most exposed large counties (100k+ workers) and state worker-weighted means.

Both indices use the unweighted category means used on the map.

Output
  data/processed/robot_findings.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent.parent
PROC = ROOT / "data" / "processed"
ATLAS = ROOT / "src" / "map" / "data" / "atlas.json"


def wavg(x, w):
    return float(np.average(x, weights=w))


def main():
    atlas = json.loads(ATLAS.read_text())
    if "occ_robot" not in atlas:
        raise SystemExit("atlas.json has no robot layer; run steps 7 and 4 first")

    rows = [
        {"fips": k, "name": f"{v['n']}, {v['s']}", "state": v["s"], "w": v["w"],
         "ai": v["e"], "robot": v["r"], "sh": v["sh"]}
        for k, v in atlas["counties_5yr"].items()
    ]
    d = pd.DataFrame(rows)
    sh = np.array(d.pop("sh").tolist())
    total_w = d.w.sum()

    out = {}

    # 1. Correlation and bivariate terciles (by county count, like the map's legend).
    out["county_corr"] = float(d.ai.corr(d.robot))
    d["ai_t"] = pd.qcut(d.ai, 3, labels=False)
    d["robot_t"] = pd.qcut(d.robot, 3, labels=False)
    cells = (d.groupby(["ai_t", "robot_t"])
               .agg(n_counties=("fips", "size"), workers=("w", "sum"))
               .reset_index())
    cells["worker_share"] = cells.workers / total_w
    out["terciles"] = cells.to_dict(orient="records")

    # 2. Tract socioeconomic gradient.
    t = pd.read_parquet(PROC / "tract_exposure.parquet")
    t = t[(t.workers > 0) & (t.median_hh_income > 0) & (t.state_fips != "72")]   # 50 states + DC, as on the map
    t = t.dropna(subset=["median_hh_income", "robot"])
    t["inc_q"] = pd.qcut(t.median_hh_income, 5, labels=False)
    grad = []
    for q, g in t.groupby("inc_q"):
        grad.append({"income_quintile": int(q) + 1,
                     "median_income": float(g.median_hh_income.median()),
                     "ai": wavg(g.exposure, g.workers),
                     "robot": wavg(g.robot, g.workers)})
    out["income_gradient"] = grad
    out["richest_vs_poorest_ai_ratio"] = grad[-1]["ai"] / grad[0]["ai"]
    out["poorest_vs_richest_robot_ratio"] = grad[0]["robot"] / grad[-1]["robot"]
    out["tract_corr_ai_robot"] = float(t.exposure.corr(t.robot))

    tb = t[(t.workers >= 200) & t.ba_plus.notna()]
    out["tract_corr_ba"] = {"ai": float(tb.exposure.corr(tb.ba_plus)),
                            "robot": float(tb.robot.corr(tb.ba_plus)),
                            "n_tracts": int(len(tb))}

    # 3. Occupation mix: high-AI/low-robot vs. low-AI/high-robot counties.
    A = ((d.ai_t == 2) & (d.robot_t == 0)).values
    R = ((d.ai_t == 0) & (d.robot_t == 2)).values
    mix = pd.DataFrame({
        "occ": atlas["occ_names"],
        "share_ai_heavy": np.average(sh[A], axis=0, weights=d.w.values[A]),
        "share_robot_heavy": np.average(sh[R], axis=0, weights=d.w.values[R]),
        "ai_score": atlas["occ_exp"],
        "robot_score": atlas["occ_robot"],
    })
    mix["gap"] = mix.share_robot_heavy - mix.share_ai_heavy
    out["occupation_mix"] = mix.sort_values("gap").to_dict(orient="records")

    # 4. Places.
    big = d[d.w >= 100_000]
    cols = ["name", "w", "ai", "robot"]
    out["top_ai_large"] = big.nlargest(10, "ai")[cols].to_dict(orient="records")
    out["top_robot_large"] = big.nlargest(10, "robot")[cols].to_dict(orient="records")
    st = (d.groupby("state")
            .apply(lambda g: pd.Series({"ai": wavg(g.ai, g.w), "robot": wavg(g.robot, g.w),
                                        "workers": g.w.sum()}), include_groups=False)
            .reset_index().sort_values("ai"))
    out["states"] = st.to_dict(orient="records")

    path = PROC / "robot_findings.json"
    path.write_text(json.dumps(out, indent=2, default=float))
    print(f"wrote {path}")
    print(f"  county corr {out['county_corr']:.2f}, tract corr {out['tract_corr_ai_robot']:.2f}")
    hi_ai = cells[(cells.ai_t == 2) & (cells.robot_t == 0)].worker_share.item()
    hi_r = cells[(cells.ai_t == 0) & (cells.robot_t == 2)].worker_share.item()
    both = cells[(cells.ai_t == 2) & (cells.robot_t == 2)].worker_share.item()
    print(f"  worker share: AI-heavy {hi_ai:.1%}, robot-heavy {hi_r:.1%}, high on both {both:.2%}")
    print(f"  AI richest/poorest {out['richest_vs_poorest_ai_ratio']:.2f}x, "
          f"robot poorest/richest {out['poorest_vs_richest_robot_ratio']:.2f}x")
    print(f"  tract corr with BA share: AI {out['tract_corr_ba']['ai']:.2f}, "
          f"robot {out['tract_corr_ba']['robot']:.2f}")


if __name__ == "__main__":
    main()
