"""
Phase 1 — pull EIP-3009 USDC settlements for every facilitator address
confirmed active by 01_verify_facilitators.py.

Two settlement patterns exist on Base (confirmed empirically — see
notes/PHASE0_DATA_PATH.md) and both are captured here:

  1. "direct forward" — the facilitator submits transferWithAuthorization /
     receiveWithAuthorization directly with (payer, merchant) as the
     transfer's actual parties. The facilitator pays gas but is never a
     party to the token movement. This DOES preserve a visible payer->
     recipient edge on-chain.
  2. "pooled" — the facilitator submits the authorization with itself as the
     recipient (collect leg), then later pays merchants out of its own
     pooled balance via a separate, often-batched call (payout leg). The
     payer->recipient edge is NOT recoverable from the collect leg alone;
     only payer->facilitator and facilitator->(merchant, batched) are.

Strategy per facilitator address F:
  a) Pull every transaction sent BY F (tx.from == F) whose `to` is the USDC
     contract and whose method is an EIP-3009 method. This is the "collect"
     leg regardless of pattern (1) or (2). Base Blockscout's per-address
     transaction list already returns fully decoded `decoded_input` for
     each transaction, so the actual (payer, recipient, value) triple(s)
     come straight out of the list response — no extra per-transaction call
     is needed. `transferWithAuthorization`/`receiveWithAuthorization` decode
     to scalar from/to/value; `batchTransferWithAuthorization` decodes to
     parallel arrays (one or more authorizations bundled in one call) and is
     expanded into one row per authorization.
  c) Separately, pull every USDC token-transfer where F itself is the
     *sender* (F -> someone else) — this is the payout leg for pooling
     facilitators. Tagged as non-attributable to a specific payer.

Output:
  data/raw/settlements_collect.csv  — one row per (payer, recipient, value)
    extracted from a collect-leg transaction. `pooled` column marks whether
    recipient == the facilitator's own address (pattern 2) or a distinct
    address (pattern 1, a true observed payer->provider edge).
  data/raw/settlements_payout.csv   — one row per outgoing transfer FROM a
    pooling facilitator's own address (pattern 2's second leg). Cannot be
    joined to a specific payer.
"""
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module

reg = import_module("00_facilitator_registry")

BLOCKSCOUT = "https://base.blockscout.com/api/v2"
USDC = reg.USDC_BASE.lower()
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
PAGES_DIR = RAW_DIR / "blockscout_pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)

EIP3009_METHODS = {
    "transferWithAuthorization", "receiveWithAuthorization",
    "batchTransferWithAuthorization",
}
MAX_PAGES_PER_ADDRESS = 60  # ~3,000 tx/address; addresses that exceed this are
# reported as "incomplete" rather than left to run indefinitely — some
# relayer addresses have very long histories of non-EIP-3009 traffic that
# never reach an empty page or the lookback cutoff within a reasonable
# number of requests against a free, shared public API.


def get_json(url, params=None, retries=4, cache_key=None):
    if cache_key:
        cache_file = PAGES_DIR / f"{cache_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                if cache_key:
                    (PAGES_DIR / f"{cache_key}.json").write_text(json.dumps(data))
                return data
            if r.status_code == 404:
                return {}
        except requests.RequestException as e:
            print(f"    ! request error ({e}), retry {attempt+1}/{retries}")
        time.sleep(2 * (attempt + 1))
    return None


def ts_to_epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


INCOMPLETE_ADDRESSES = set()


def paginate(path, base_params, cutoff_ts, cache_prefix):
    items_all = []
    params = dict(base_params)
    page = 0
    incomplete = False
    while page < MAX_PAGES_PER_ADDRESS:
        page += 1
        if page % 10 == 0:
            print(f"    ... page {page}", flush=True)
        data = get_json(
            f"{BLOCKSCOUT}{path}", params=params,
            cache_key=f"{cache_prefix}_p{page}",
        )
        if data is None:
            print(f"    ! giving up at page {page} (request failures)")
            incomplete = True
            break
        items = data.get("items", [])
        if not items:
            break
        items_all.extend(items)
        oldest_ts = items[-1].get("timestamp")
        next_params = data.get("next_page_params")
        if oldest_ts and ts_to_epoch(oldest_ts) < cutoff_ts:
            break
        if not next_params:
            break
        params = {**base_params, **next_params}
        time.sleep(0.15)
    else:
        incomplete = True
        print(f"    ! hit MAX_PAGES_PER_ADDRESS ({MAX_PAGES_PER_ADDRESS}) before reaching "
              f"lookback cutoff or end of history — this address's coverage is INCOMPLETE")
    if incomplete:
        INCOMPLETE_ADDRESSES.add(cache_prefix)
    return items_all


def load_kept_facilitators():
    path = RAW_DIR / "facilitator_candidates_checked.csv"
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["keep"] == "True":
                rows.append(row)
    return rows


def decoded_params(decoded_input):
    return {p["name"]: p["value"] for p in (decoded_input or {}).get("parameters", [])}


def extract_collect_leg(name, addr, cutoff_ts):
    """Transactions sent by `addr` calling EIP-3009 methods on USDC, decoded
    entirely from the address transaction list (no extra per-tx call)."""
    addr = addr.lower()
    txs = paginate(
        f"/addresses/{addr}/transactions", {"filter": "from"}, cutoff_ts,
        cache_prefix=f"txs_from_{addr}",
    )
    rows = []
    for tx in txs:
        to_hash = (tx.get("to") or {}).get("hash") or ""
        method = tx.get("method") or ""
        if to_hash.lower() != USDC or method not in EIP3009_METHODS:
            continue
        params = decoded_params(tx.get("decoded_input"))
        tx_hash = tx.get("hash")
        common = {
            "facilitator_name": name,
            "facilitator_address": addr,
            "tx_hash": tx_hash,
            "block_number": tx.get("block_number"),
            "timestamp": tx.get("timestamp"),
            "method": method,
        }
        if method == "batchTransferWithAuthorization":
            froms = params.get("from") or []
            tos = params.get("to") or []
            values = params.get("value") or []
            for f_addr, t_addr, val in zip(froms, tos, values):
                rows.append({
                    **common,
                    "payer_address": f_addr.lower(),
                    "recipient_address": t_addr.lower(),
                    "pooled": t_addr.lower() == addr,
                    "value_raw": val,
                    "decimals": 6,
                })
        else:
            f_addr, t_addr, val = params.get("from"), params.get("to"), params.get("value")
            if not f_addr or not t_addr:
                continue
            rows.append({
                **common,
                "payer_address": f_addr.lower(),
                "recipient_address": t_addr.lower(),
                "pooled": t_addr.lower() == addr,
                "value_raw": val,
                "decimals": 6,
            })
    return rows


def extract_payout_leg(name, addr, cutoff_ts):
    """USDC transfers where `addr` (the facilitator itself) is the sender."""
    addr = addr.lower()
    items = paginate(
        f"/addresses/{addr}/token-transfers", {"token": reg.USDC_BASE},
        cutoff_ts, cache_prefix=f"tt_from_{addr}",
    )
    payout_rows = []
    for it in items:
        from_addr = ((it.get("from") or {}).get("hash") or "").lower()
        if from_addr != addr:
            continue  # this is an incoming (collect) row, already covered above
        total = it.get("total") or {}
        payout_rows.append({
            "facilitator_name": name,
            "facilitator_address": addr,
            "tx_hash": it.get("transaction_hash"),
            "block_number": it.get("block_number"),
            "timestamp": it.get("timestamp"),
            "method": it.get("method"),
            "recipient_address": ((it.get("to") or {}).get("hash") or "").lower(),
            "value_raw": total.get("value"),
            "decimals": total.get("decimals"),
        })
    return payout_rows


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=90)
    args = ap.parse_args()

    cutoff_ts = datetime.now(timezone.utc).timestamp() - args.lookback_days * 86400
    facilitators = load_kept_facilitators()
    print(f"Pulling settlements for {len(facilitators)} confirmed facilitators "
          f"(lookback={args.lookback_days}d)\n", flush=True)

    all_collect, all_payout = [], []
    for fac in facilitators:
        name, addr = fac["name"], fac["address"]
        print(f"=== {name} {addr} ===", flush=True)
        collect = extract_collect_leg(name, addr, cutoff_ts)
        print(f"  collect-leg rows: {len(collect)}", flush=True)
        all_collect.extend(collect)
        if any(r["pooled"] for r in collect):
            payout = extract_payout_leg(name, addr, cutoff_ts)
            print(f"  payout-leg rows: {len(payout)} (pooling facilitator)", flush=True)
            all_payout.extend(payout)

    collect_path = RAW_DIR / "settlements_collect.csv"
    with open(collect_path, "w", newline="") as f:
        fieldnames = [
            "facilitator_name", "facilitator_address", "tx_hash", "block_number",
            "timestamp", "method", "payer_address", "recipient_address",
            "pooled", "value_raw", "decimals",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in all_collect:
            w.writerow(r)

    payout_path = RAW_DIR / "settlements_payout.csv"
    with open(payout_path, "w", newline="") as f:
        fieldnames = [
            "facilitator_name", "facilitator_address", "tx_hash", "block_number",
            "timestamp", "method", "recipient_address", "value_raw", "decimals",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in all_payout:
            w.writerow(r)

    print(f"\nWrote {len(all_collect)} collect-leg rows -> {collect_path}")
    print(f"Wrote {len(all_payout)} payout-leg rows -> {payout_path}")
    if INCOMPLETE_ADDRESSES:
        print(f"\n{len(INCOMPLETE_ADDRESSES)} address pulls hit the page cap or a request "
              f"failure before reaching the lookback cutoff (coverage is a lower bound "
              f"for these, not a full {args.lookback_days}-day picture):")
        for a in sorted(INCOMPLETE_ADDRESSES):
            print(f"  {a}")
        incomplete_path = RAW_DIR / "incomplete_pulls.txt"
        incomplete_path.write_text("\n".join(sorted(INCOMPLETE_ADDRESSES)) + "\n")
        print(f"Wrote {incomplete_path}")


if __name__ == "__main__":
    main()
