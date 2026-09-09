"""
Retry pass for script 07 entities that failed with zero cached pages (a
Blockscout timeout at the time, not evidence of zero activity). Reuses
the same cache directory, longer timeout, more retries, patient backoff.
Rewrites data/processed/top50_bazaar_onchain.csv and the shared-payers file
by re-running the full aggregation with whatever is now cached.
"""
import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BLOCKSCOUT = "https://base.blockscout.com/api/v2"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PAGES_DIR = RAW_DIR / "top50_pages"

MAX_PAGES = 15


def get_json(url, params=None, cache_key=None, retries=5):
    if cache_key:
        cache_file = PAGES_DIR / f"{cache_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if cache_key:
                    (PAGES_DIR / f"{cache_key}.json").write_text(json.dumps(data))
                return data
            if r.status_code == 404:
                return {}
        except requests.RequestException as e:
            print(f"    ! request error ({e}), retry {attempt+1}/{retries}")
        time.sleep(3 * (attempt + 1))
    return None


def pull_incoming(payto, cutoff_ts):
    items_all = []
    params = {"token": USDC}
    page = 0
    incomplete = False
    while page < MAX_PAGES:
        page += 1
        data = get_json(
            f"{BLOCKSCOUT}/addresses/{payto}/token-transfers", params=params,
            cache_key=f"{payto}_p{page}",
        )
        if data is None:
            incomplete = True
            break
        items = data.get("items", [])
        if not items:
            break
        items_all.extend(it for it in items if ((it.get("to") or {}).get("hash") or "").lower() == payto)
        oldest_ts = items[-1].get("timestamp")
        next_params = data.get("next_page_params")
        if oldest_ts:
            ts = datetime.fromisoformat(oldest_ts.replace("Z", "+00:00")).timestamp()
            if ts < cutoff_ts:
                break
        if not next_params:
            break
        params = {"token": USDC, **next_params}
        time.sleep(0.15)
    else:
        incomplete = True
    return items_all, incomplete


def main():
    entities = list(csv.DictReader(open(PROCESSED_DIR / "bazaar_entities_ranked.csv")))[:50]
    existing_rows = {r["payTo"]: r for r in csv.DictReader(open(PROCESSED_DIR / "top50_bazaar_onchain.csv"))}
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()

    entity_rows = []
    payer_to_entities = defaultdict(set)
    domain_by_payto = {}

    for i, e in enumerate(entities):
        payto = e["payTo"].lower()
        domain_by_payto[payto] = e["domains"]
        prior = existing_rows.get(payto)
        needs_retry = prior is None or (float(prior["onchain_l30d_usd_volume"]) == 0
                                         and not list(PAGES_DIR.glob(f"{payto}_p1.json")))
        if needs_retry:
            print(f"[retry {i+1}/50] {e['domains'][:40]:40s} {payto}", end=" ... ", flush=True)
            items, incomplete = pull_incoming(payto, cutoff_ts)
            recent = [it for it in items
                      if datetime.fromisoformat(it["timestamp"].replace("Z", "+00:00")).timestamp() >= cutoff_ts]
            payers = set(((it.get("from") or {}).get("hash") or "").lower() for it in recent)
            payers.discard("")
            total = sum(float((it.get("total") or {}).get("value") or 0) / 1e6 for it in recent)
            row = {
                "payTo": payto, "domains": e["domains"],
                "bazaar_l30d_calls": e["l30d_total_calls"],
                "bazaar_l30d_implied_usd": e["l30d_implied_usd_volume"],
                "onchain_l30d_transfer_count": len(recent),
                "onchain_l30d_usd_volume": round(total, 2),
                "onchain_l30d_distinct_payers": len(payers),
                "onchain_incomplete_pull": incomplete,
                "onchain_methods": {},
            }
            print(f"onchain: {len(recent)} transfers, {len(payers)} payers, ${total:,.2f}"
                  + (" [INCOMPLETE]" if incomplete else ""))
        else:
            row = prior
            row["onchain_incomplete_pull"] = row["onchain_incomplete_pull"] == "True"
            payers = set()  # payer set not retained from prior run; re-derive below from cache if present

        entity_rows.append(row)

    # Rebuild payer sets fresh from whatever is cached now (covers both retried
    # and previously-successful entities uniformly).
    entity_payers = {}
    for e in entities:
        payto = e["payTo"].lower()
        payers = set()
        p = 1
        while True:
            f = PAGES_DIR / f"{payto}_p{p}.json"
            if not f.exists():
                break
            data = json.loads(f.read_text())
            for it in data.get("items", []):
                ts = datetime.fromisoformat(it["timestamp"].replace("Z", "+00:00")).timestamp()
                if ts < cutoff_ts:
                    continue
                if ((it.get("to") or {}).get("hash") or "").lower() != payto:
                    continue
                fr = ((it.get("from") or {}).get("hash") or "").lower()
                if fr:
                    payers.add(fr)
            p += 1
        entity_payers[payto] = payers
        for payer in payers:
            payer_to_entities[payer].add(payto)

    out_path = PROCESSED_DIR / "top50_bazaar_onchain.csv"
    with open(out_path, "w", newline="") as f:
        fieldnames = [
            "payTo", "domains", "bazaar_l30d_calls", "bazaar_l30d_implied_usd",
            "onchain_l30d_transfer_count", "onchain_l30d_usd_volume",
            "onchain_l30d_distinct_payers", "onchain_incomplete_pull", "onchain_methods",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in entity_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"\nWrote {out_path}")

    shared = {p: es for p, es in payer_to_entities.items() if len(es) > 1}
    shared_rows = []
    for payer, es in sorted(shared.items(), key=lambda x: -len(x[1])):
        shared_rows.append({
            "payer_address": payer,
            "n_entities_paid": len(es),
            "entities": ";".join(domain_by_payto.get(pt, pt) for pt in es),
        })
    out_path2 = PROCESSED_DIR / "top50_bazaar_shared_payers.csv"
    with open(out_path2, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["payer_address", "n_entities_paid", "entities"])
        w.writeheader()
        for r in shared_rows:
            w.writerow(r)

    print(f"\n{len(shared)} payer wallets paid MORE THAN ONE of the top 50 named entities directly:")
    for r in shared_rows[:30]:
        print(f"  {r['payer_address']}  ->  {r['n_entities_paid']} entities: {r['entities'][:150]}")
    print(f"Wrote {out_path2}")


if __name__ == "__main__":
    main()
