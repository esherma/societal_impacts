"""
Phase 0/1 — check every candidate facilitator address for real on-chain
activity before trusting it. Addresses with zero USDC token-transfer activity
are dropped, and the full check result (kept or dropped, and why) is written
to data/raw/facilitator_candidates_checked.csv so the exclusion is visible,
not silent.
"""
import csv
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module

reg = import_module("00_facilitator_registry")

BLOCKSCOUT = "https://base.blockscout.com/api/v2"
OUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_json(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


EIP3009_METHODS = {
    "transferWithAuthorization", "receiveWithAuthorization",
    "batchTransferWithAuthorization", "cancelAuthorization",
}


def check_address(addr):
    addr = addr.lower()
    info = get_json(f"{BLOCKSCOUT}/addresses/{addr}")
    tags = []
    is_contract = None
    if info:
        is_contract = info.get("is_contract")
        meta = info.get("metadata") or {}
        tags = [t.get("name") for t in meta.get("tags", [])]

    # Signal 1: address is itself a party (from or to) to a USDC Transfer —
    # catches "pooling" facilitators that collect funds into their own
    # address before paying merchants out of it.
    usdc_sample = get_json(
        f"{BLOCKSCOUT}/addresses/{addr}/token-transfers",
        params={"token": reg.USDC_BASE},
    )
    usdc_transfer_seen = bool(usdc_sample and usdc_sample.get("items"))

    # Signal 2: address is the *transaction sender* calling an EIP-3009
    # method directly on the USDC contract, even though it is NOT itself a
    # party to the resulting Transfer log — this is the "direct forwarding"
    # pattern (facilitator relays payer's signed authorization straight to
    # the merchant, e.g. transferWithAuthorization(payer, merchant, amount)).
    # Missed by signal 1 alone; confirmed to exist on real facilitators
    # during this investigation (see notes/PHASE0_DATA_PATH.md).
    sent_txs = get_json(
        f"{BLOCKSCOUT}/addresses/{addr}/transactions", params={"filter": "from"}
    )
    direct_forward_seen = False
    if sent_txs:
        for tx in sent_txs.get("items", []):
            to_hash = (tx.get("to") or {}).get("hash") or ""
            method = tx.get("method") or ""
            if to_hash.lower() == reg.USDC_BASE.lower() and method in EIP3009_METHODS:
                direct_forward_seen = True
                break

    return {
        "address": addr,
        "is_contract": is_contract,
        "onchain_tags": ";".join(tags) if tags else "",
        "usdc_transfer_seen": usdc_transfer_seen,
        "direct_forward_seen": direct_forward_seen,
    }


def main():
    rows = []
    seen = set()
    for name, addr, source, chain in reg.FACILITATOR_CANDIDATES:
        if chain != "base":
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        print(f"checking {name:20s} {addr}", end=" ... ", flush=True)
        result = check_address(addr)
        keep = bool(result["usdc_transfer_seen"] or result["direct_forward_seen"])
        result.update({"name": name, "source": source, "keep": keep})
        rows.append(result)
        mode = []
        if result["usdc_transfer_seen"]:
            mode.append("pooled")
        if result["direct_forward_seen"]:
            mode.append("direct-forward")
        print(f"KEEP ({'+'.join(mode)})" if keep else "drop (no USDC activity seen)")
        time.sleep(0.3)  # be polite to the free public API

    out_path = OUT_DIR / "facilitator_candidates_checked.csv"
    fieldnames = [
        "name", "address", "source", "keep", "is_contract",
        "onchain_tags", "usdc_transfer_seen", "direct_forward_seen",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    kept = [r for r in rows if r["keep"]]
    print(f"\n{len(kept)}/{len(rows)} candidate addresses confirmed with real USDC activity.")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
