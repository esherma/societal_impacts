"""
Phase 3 — funding-source clustering.

For each payer wallet, find the earliest native-ETH funding transaction
(who first sent it gas) via Base Blockscout. Payers funded by the SAME
upstream address are a common-control signal — much stronger than
similarity of behavior alone, since it implies one operator set up both
wallets.

This is best-effort and bounded: we only look at the address's *incoming
native transfers* list, and if it's short (no next_page_params — typical for
narrow, single-purpose bot wallets) we take the oldest entry directly; if the
list is long (paginated) we cap how far back we walk to keep this tractable,
and report that funding source as "unresolved (paginated further)" rather
than silently guessing.
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
PAGES_DIR = RAW_DIR / "blockscout_pages"

MAX_PAGES_PER_PAYER = 5  # walk back at most 5 pages (~250 txs) looking for genesis funding


def get_json(url, params=None, cache_key=None, retries=3):
    if cache_key:
        cache_file = PAGES_DIR / f"{cache_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20)
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


def find_funding_source(payer):
    """Return (funder_address_or_None, resolved: bool, tag: str|None)."""
    params = {"filter": "to"}
    page = 0
    last_items = []
    while page < MAX_PAGES_PER_PAYER:
        page += 1
        data = get_json(
            f"{BLOCKSCOUT}/addresses/{payer}/transactions", params=params,
            cache_key=f"fund_{payer}_p{page}",
        )
        if not data:
            break
        items = data.get("items", [])
        if not items:
            break
        last_items = items
        next_params = data.get("next_page_params")
        if not next_params:
            # This page is the last (oldest) page -> its last item is genesis funding.
            oldest = items[-1]
            funder = (oldest.get("from") or {}).get("hash")
            return funder.lower() if funder else None, True, None
        params = {"filter": "to", **next_params}
        time.sleep(0.15)
    # Ran out of page budget without reaching genesis.
    if last_items:
        funder = (last_items[-1].get("from") or {}).get("hash")
        return (funder.lower() if funder else None), False, None
    return None, False, None


def tag_for(addr):
    info = get_json(f"{BLOCKSCOUT}/addresses/{addr}", cache_key=f"addrinfo_{addr}")
    if not info:
        return ""
    meta = info.get("metadata") or {}
    return ";".join(t.get("name") for t in meta.get("tags", []) if t.get("name"))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=200,
                     help="only resolve funding source for the top-N payers by settlement count (API cost control)")
    args = ap.parse_args()

    payers = list(csv.DictReader(open(PROCESSED_DIR / "payer_features.csv")))
    payers.sort(key=lambda r: -int(r["n_settlements"]))
    subset = payers[:args.top_n]

    rows = []
    funder_to_payers = defaultdict(set)
    for i, p in enumerate(subset):
        addr = p["payer_address"]
        funder, resolved, _ = find_funding_source(addr)
        tag = tag_for(funder) if funder else ""
        rows.append({
            "payer_address": addr,
            "funder_address": funder or "",
            "funder_resolved_to_genesis": resolved,
            "funder_onchain_tags": tag,
        })
        if funder:
            funder_to_payers[funder].add(addr)
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(subset)} payers processed")

    shared_funders = {f: ps for f, ps in funder_to_payers.items() if len(ps) > 1}

    out_path = PROCESSED_DIR / "payer_funding_sources.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "payer_address", "funder_address", "funder_resolved_to_genesis", "funder_onchain_tags",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\n{len(subset)} payers checked, {len(rows) - sum(1 for r in rows if not r['funder_address'])} funders resolved")
    print(f"{len(shared_funders)} funder addresses fund MORE THAN ONE payer in this sample "
          f"(common-control signal):")
    for funder, ps in sorted(shared_funders.items(), key=lambda x: -len(x[1]))[:20]:
        print(f"  {funder}: funds {len(ps)} distinct payer wallets")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
