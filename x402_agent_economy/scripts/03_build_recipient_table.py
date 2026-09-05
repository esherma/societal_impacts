"""
Phase 2 — build the labeled recipient table.

Recipients come from two places, kept distinct because their evidentiary
weight differs:
  - "direct" recipients: the `recipient_address` in settlements_collect.csv
    rows where pooled == False. These are on-chain-confirmed as the actual
    payee of a specific, identifiable payer's authorization.
  - "payout" recipients: addresses in settlements_payout.csv, i.e. who a
    pooling facilitator paid out of its own balance. These are confirmed
    recipients of facilitator funds, but NOT attributable to any single
    payer (see notes/PHASE0_DATA_PATH.md).

Labeling is conservative: we only assign a category when we have a concrete
signal (an on-chain name tag, or the recipient address matching a known
facilitator itself, or a recognizable pattern). Everything else is
"unknown" — and the unlabeled share of volume is reported, not hidden.
"""
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import requests

BLOCKSCOUT = "https://base.blockscout.com/api/v2"
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
PAGES_DIR = RAW_DIR / "blockscout_pages"


def get_json(url, cache_key=None, retries=3):
    if cache_key:
        cache_file = PAGES_DIR / f"{cache_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                if cache_key:
                    (PAGES_DIR / f"{cache_key}.json").write_text(json.dumps(data))
                return data
            if r.status_code == 404:
                return {}
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


def load_facilitator_addresses():
    path = RAW_DIR / "facilitator_candidates_checked.csv"
    addrs = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["keep"] == "True":
                addrs[row["address"].lower()] = row["name"]
    return addrs


def load_settlements():
    collect = list(csv.DictReader(open(RAW_DIR / "settlements_collect.csv")))
    payout_path = RAW_DIR / "settlements_payout.csv"
    payout = list(csv.DictReader(open(payout_path))) if payout_path.exists() else []
    return collect, payout


def classify_by_tags(tags):
    tags_l = [t.lower() for t in tags]
    joined = " ".join(tags_l)
    if any(k in joined for k in ["token", "nft", "meme"]):
        return "gamified_memecoin"
    if any(k in joined for k in ["exchange", "cex", "binance", "coinbase exchange"]):
        return "cex"
    if "facilitator" in joined or "x402" in joined:
        return "facilitator_or_infra"
    return None


def main():
    facilitator_addrs = load_facilitator_addresses()
    collect, payout = load_settlements()

    volume = defaultdict(float)
    count = defaultdict(int)
    for r in collect:
        if r["pooled"] == "True":
            continue  # not a direct provider edge — belongs to the pooled aggregate below
        addr = r["recipient_address"]
        try:
            val = float(r["value_raw"]) / (10 ** int(r["decimals"] or 6))
        except (TypeError, ValueError):
            val = 0.0
        volume[addr] += val
        count[addr] += 1
    for r in payout:
        addr = r["recipient_address"]
        try:
            val = float(r["value_raw"]) / (10 ** int(r.get("decimals") or 6))
        except (TypeError, ValueError):
            val = 0.0
        volume[addr] += val
        count[addr] += 1

    rows = []
    for addr, vol in sorted(volume.items(), key=lambda x: -x[1]):
        info = get_json(f"{BLOCKSCOUT}/addresses/{addr}", cache_key=f"addrinfo_{addr}")
        tags = []
        is_contract = None
        if info:
            is_contract = info.get("is_contract")
            meta = info.get("metadata") or {}
            tags = [t.get("name") for t in meta.get("tags", []) if t.get("name")]
        time.sleep(0.15)

        if addr in facilitator_addrs:
            category = "facilitator_pool_address"
            label_source = "known_facilitator_list"
            confidence = "high"
        else:
            cat = classify_by_tags(tags)
            if cat:
                category, label_source, confidence = cat, "onchain_tag", "medium"
            else:
                category, label_source, confidence = "unknown", "none", "low"
        rows.append({
            "recipient_address": addr,
            "total_usdc_volume": round(vol, 6),
            "settlement_count": count[addr],
            "is_contract": is_contract,
            "category": category,
            "label_source": label_source,
            "confidence": confidence,
        })

    total_volume = sum(r["total_usdc_volume"] for r in rows)
    unlabeled_volume = sum(r["total_usdc_volume"] for r in rows if r["category"] == "unknown")
    unlabeled_frac = (unlabeled_volume / total_volume) if total_volume else float("nan")

    out_path = PROCESSED_DIR / "recipients_labeled.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "recipient_address", "total_usdc_volume", "settlement_count",
            "is_contract", "category", "label_source", "confidence",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"{len(rows)} distinct recipient addresses")
    print(f"Total observed USDC volume: {total_volume:,.2f}")
    print(f"Unlabeled ('unknown') volume fraction: {unlabeled_frac:.1%}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
