"""
Phase 1/2 extension — pull Coinbase CDP's own x402 Bazaar discovery registry.

This is a live, unauthenticated, first-party API
(api.cdp.coinbase.com/platform/v2/x402/discovery/resources) listing every
resource that opted into the Bazaar via the CDP facilitator. Unlike our
on-chain reconstruction, this comes straight from the facilitator's own
accounting: each resource carries a real payTo address, price, and a
`quality` block with 30-day call count and unique-payer count — ground
truth we don't have to infer.

Important scope note: this ONLY covers resources using the Coinbase CDP
facilitator with the Bazaar extension enabled. Resources on other
facilitators (Heurist, X402rs, PayAI, etc. from our on-chain pipeline) are
NOT in this registry unless they separately also register with CDP. So this
is a different, overlapping-but-not-identical slice of the ecosystem from
scripts 00-05, not a superset or subset.

Output: data/raw/bazaar_resources.csv (one row per resource x accepts-entry).
"""
import csv
import json
import time
from pathlib import Path

import requests

API = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
PAGES_DIR = RAW_DIR / "bazaar_pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)

LIMIT = 100


def get_json(url, params, cache_key, retries=4):
    cache_file = PAGES_DIR / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                cache_file.write_text(json.dumps(data))
                return data
        except requests.RequestException as e:
            print(f"  ! request error ({e}), retry {attempt+1}/{retries}")
        time.sleep(2 * (attempt + 1))
    return None


def main():
    offset = 0
    total = None
    rows = []
    page = 0
    while total is None or offset < total:
        page += 1
        data = get_json(API, {"limit": LIMIT, "offset": offset}, cache_key=f"p{page}_o{offset}")
        if data is None:
            print(f"! giving up at offset {offset}")
            break
        pagination = data.get("pagination", {})
        total = pagination.get("total", 0)
        items = data.get("items", [])
        if not items:
            break
        for it in items:
            quality = it.get("quality") or {}
            for accept in it.get("accepts", []):
                rows.append({
                    "resource": it.get("resource"),
                    "description": (it.get("description") or "")[:200],
                    "serviceName": it.get("serviceName"),
                    "tags": ";".join(it.get("tags") or []),
                    "curated": it.get("curated"),
                    "network": accept.get("network"),
                    "asset": accept.get("asset"),
                    "scheme": accept.get("scheme"),
                    "payTo": (accept.get("payTo") or "").lower(),
                    "amount_raw": accept.get("amount") or accept.get("maxAmountRequired"),
                    "l30DaysTotalCalls": quality.get("l30DaysTotalCalls"),
                    "l30DaysUniquePayers": quality.get("l30DaysUniquePayers"),
                    "lastCalledAt": quality.get("lastCalledAt"),
                })
        offset += LIMIT
        if page % 10 == 0:
            print(f"  page {page}, offset {offset}/{total}", flush=True)
        time.sleep(0.1)

    out_path = RAW_DIR / "bazaar_resources.csv"
    with open(out_path, "w", newline="") as f:
        fieldnames = [
            "resource", "description", "serviceName", "tags", "curated",
            "network", "asset", "scheme", "payTo", "amount_raw",
            "l30DaysTotalCalls", "l30DaysUniquePayers", "lastCalledAt",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\n{page} pages, {len(rows)} resource-accepts rows -> {out_path}")
    print(f"Bazaar reports {total} total resources")


if __name__ == "__main__":
    main()
