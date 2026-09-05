"""
Phase 3/4 — build the payer->recipient bipartite graph and payer-level
behavioral features.

Only DIRECT settlements (settlements_collect.csv rows with pooled == False)
give a true, on-chain-visible payer->provider edge. Pooled collect-leg rows
tell us a payer paid *a facilitator*, not which provider — those are kept
as payer->facilitator edges, clearly separated, so the "providers per payer"
question is answered twice: once on the (smaller, but trustworthy) direct
edge set, and once treating "facilitator used" as a coarse proxy for
provider diversity (explicitly labeled as a weaker signal).

Output: data/processed/payer_features.csv
"""
import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import statistics


def shannon_entropy_normalized(counts):
    """0 = all mass in one bucket (very non-diurnal/bursty), 1 = perfectly
    uniform across buckets (consistent with either a flat robotic cadence or
    enough volume to average out any human diurnal pattern)."""
    total = sum(counts)
    if total == 0:
        return None
    n_buckets = len(counts)
    h = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    max_h = math.log2(n_buckets)
    return h / max_h if max_h > 0 else None

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def main():
    collect = list(csv.DictReader(open(RAW_DIR / "settlements_collect.csv")))

    # payer -> list of (timestamp, recipient_or_facilitator, value, pooled)
    payer_events = defaultdict(list)
    for r in collect:
        payer = r["payer_address"]
        if not payer:
            continue
        try:
            val = float(r["value_raw"]) / (10 ** int(r["decimals"] or 6))
        except (TypeError, ValueError):
            val = 0.0
        pooled = r["pooled"] == "True"
        edge_target = r["facilitator_address"] if pooled else r["recipient_address"]
        payer_events[payer].append({
            "ts": parse_ts(r["timestamp"]),
            "target": edge_target,
            "value": val,
            "pooled": pooled,
            "facilitator": r["facilitator_address"],
        })

    rows = []
    direct_multi_provider_payers = 0
    for payer, events in payer_events.items():
        events.sort(key=lambda e: e["ts"])
        n = len(events)
        direct_events = [e for e in events if not e["pooled"]]
        direct_recipients = {e["target"] for e in direct_events}
        all_targets = {e["target"] for e in events}  # direct recipients + facilitators paid into
        facilitators_used = {e["facilitator"] for e in events}

        inter_times = [events[i + 1]["ts"] - events[i]["ts"] for i in range(n - 1)]
        lifetime_s = events[-1]["ts"] - events[0]["ts"] if n > 1 else 0
        values = [e["value"] for e in events]

        if len(direct_recipients) > 1:
            direct_multi_provider_payers += 1

        mean_val = statistics.mean(values) if values else 0
        stdev_val = statistics.pstdev(values) if len(values) > 1 else 0
        cv_value = (stdev_val / mean_val) if mean_val else None

        # Phase 4 — diurnal cycle: hour-of-day histogram (UTC) entropy.
        # Low entropy = activity concentrated in a few hours (could be a
        # human timezone pattern OR a scheduled bot); high entropy = spread
        # evenly across the day (consistent with an always-on agent, or with
        # too little data to tell).
        hour_counts = [0] * 24
        for e in events:
            hour_counts[datetime.fromtimestamp(e["ts"], tz=timezone.utc).hour] += 1
        diurnal_entropy = shannon_entropy_normalized(hour_counts) if n >= 5 else None

        # Burst structure: fraction of gaps under 60s (rapid-fire calls).
        burst_frac_under_60s = (
            sum(1 for dt in inter_times if dt < 60) / len(inter_times)
            if inter_times else None
        )

        rows.append({
            "payer_address": payer,
            "n_settlements": n,
            "n_direct_settlements": len(direct_events),
            "n_distinct_direct_recipients": len(direct_recipients),
            "n_distinct_facilitators_used": len(facilitators_used),
            "n_distinct_targets_any": len(all_targets),
            "total_value_usdc": round(sum(values), 6),
            "mean_value_usdc": round(mean_val, 6),
            "stdev_value_usdc": round(stdev_val, 6),
            "cv_value": round(cv_value, 4) if cv_value is not None else None,
            "first_seen_utc": datetime.fromtimestamp(events[0]["ts"], tz=timezone.utc).isoformat(),
            "last_seen_utc": datetime.fromtimestamp(events[-1]["ts"], tz=timezone.utc).isoformat(),
            "lifetime_seconds": round(lifetime_s, 1),
            "median_inter_tx_seconds": round(statistics.median(inter_times), 1) if inter_times else None,
            "min_inter_tx_seconds": round(min(inter_times), 1) if inter_times else None,
            "diurnal_entropy_normalized": round(diurnal_entropy, 3) if diurnal_entropy is not None else None,
            "burst_frac_under_60s": round(burst_frac_under_60s, 3) if burst_frac_under_60s is not None else None,
        })

    out_path = PROCESSED_DIR / "payer_features.csv"
    fieldnames = [
        "payer_address", "n_settlements", "n_direct_settlements",
        "n_distinct_direct_recipients", "n_distinct_facilitators_used",
        "n_distinct_targets_any", "total_value_usdc", "mean_value_usdc",
        "stdev_value_usdc", "cv_value", "first_seen_utc", "last_seen_utc",
        "lifetime_seconds", "median_inter_tx_seconds", "min_inter_tx_seconds",
        "diurnal_entropy_normalized", "burst_frac_under_60s",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    n_payers = len(rows)
    print(f"{n_payers} distinct payer wallets")
    print(f"Payers with >1 distinct DIRECT recipient (true on-chain multi-provider signal): "
          f"{direct_multi_provider_payers} ({direct_multi_provider_payers/n_payers:.1%})" if n_payers else "no payers")
    dist = defaultdict(int)
    for r in rows:
        dist[r["n_distinct_direct_recipients"]] += 1
    print("Distribution of distinct-direct-recipients-per-payer:")
    for k in sorted(dist):
        print(f"  {k}: {dist[k]} payers")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
