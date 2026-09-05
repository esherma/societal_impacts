# Measuring the x402 agent payment economy on Base

Exploratory measurement project: is there an observable population of
autonomous agents paying for services via the x402 protocol on Base, and do
individual payer wallets transact with multiple different providers over
time? See `FINDINGS.md` for the results and `notes/PHASE0_DATA_PATH.md` for
the data-access investigation that shaped the approach.

## Pipeline

All scripts are plain Python 3 (`pip install -r scripts/requirements.txt`)
hitting free, unauthenticated public APIs — no API keys are configured or
required, but see `notes/PHASE0_DATA_PATH.md` for why that also bounds what
this pipeline can do relative to Dune/BigQuery/paid RPC.

```bash
cd scripts
python3 01_verify_facilitators.py          # confirm candidate facilitator addresses have real on-chain activity
python3 02_pull_facilitator_transfers.py   # pull EIP-3009 settlements for confirmed facilitators (--lookback-days N)
python3 03_build_recipient_table.py        # label recipients, report unlabeled volume fraction
python3 04_build_payer_graph.py            # payer-level features + providers-per-payer distribution
```

Each script reads the previous script's CSV output from `data/raw/` or
`data/processed/`; re-running is idempotent (Blockscout API responses are
cached page-by-page under `data/raw/blockscout_pages/`).

## Data sources

- **Base Blockscout** (`https://base.blockscout.com/api/v2`) — primary
  source. Free, no key, decoded logs/calldata.
- **Public Base JSON-RPC** (`https://mainnet.base.org`) — used only to
  independently spot-check specific facts (contract address, event topic
  hash), not for bulk extraction (see Phase 0 notes for why).
- Facilitator address candidates: on-chain BaseScan/Blockscout name tags
  (highest confidence) plus the community registry
  `https://facilitators.x402.watch/` (unverified at the source; every
  address is re-checked against real on-chain activity by
  `01_verify_facilitators.py` before use).

## Outputs

- `data/raw/facilitator_candidates_checked.csv` — every candidate facilitator
  address considered, and why it was kept or dropped.
- `data/raw/settlements_collect.csv` — payer -> (recipient or facilitator)
  settlement events, with a `pooled` flag distinguishing directly-observed
  payer->provider edges from payer->facilitator-pool edges.
- `data/raw/settlements_payout.csv` — pooling facilitators' outgoing payouts
  (not attributable to a specific payer).
- `data/processed/recipients_labeled.csv` — Phase 2 deliverable.
- `data/processed/payer_features.csv` — Phase 3/4 deliverable.
