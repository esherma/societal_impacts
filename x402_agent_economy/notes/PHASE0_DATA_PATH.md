# Phase 0 — Establishing the data path

Date of investigation: 2026-09-05. All findings below come from live calls made
during this session; every address/hash is independently checked against at
least one source before being used downstream.

## Options evaluated

### 1. Dune Analytics — partially usable, not as primary source
- No `DUNE_API_KEY` (or any Dune credential) is present in this environment, so
  the Dune SQL API (`api.dune.com/api/v1/...`) is not callable — confirmed by a
  ping request returning 404/unauthenticated.
- A public dashboard does exist: **`hashed_official/x402-analytics`**
  (dashboard id 194884, query id 6084845) with a daily tx-count-by-"project"
  series covering roughly June 1 – Sep 1 2026. Fetched via a page summary
  (WebFetch), not the raw API, so treat the numbers below as directional, not
  exact:
  - Top "projects" by daily tx count include **Polygon** (one single day hit
    190,489 txs on Jul 30 2026 — note "Polygon" appears to be a chain, not a
    vendor, so this dashboard is not Base-only), **PayAI** (15k–32k+ txs/day),
    and **pieverse** (spiked to 39k+ txs on May 31 2026 — the name reads as a
    game/mint mechanic, consistent with the brief's warning that historical
    x402 volume is dominated by gamified/memecoin activity).
  - This dashboard is used only as a directional sanity check in Phase 1/2,
    not as a row-level data source, because we cannot execute custom SQL
    against it without an API key.

### 2. BigQuery public blockchain datasets — not usable here
- `bigquery.googleapis.com` is network-reachable (200 on the discovery
  endpoint), but running any query against a public dataset requires a GCP
  project + billing account + `gcloud`/service-account credentials, none of
  which exist in this environment. **Not used.**

### 3. Direct data access — chosen path, with a twist
No RPC/indexer API key (Alchemy, QuickNode, BaseScan/Etherscan) is configured
in this environment either. Two *unauthenticated* options were tested:

- **Public Base JSON-RPC** (`https://mainnet.base.org`): works, but is
  severely constrained for log scanning:
  - Hard cap of **10,000 blocks** per `eth_getLogs` call (`-32614`).
  - A second, tighter cap on *response size regardless of range*: even a
    filtered, single-topic query starts failing with `"backend response too
    large"` (`-32020`) somewhere between 5,000 and 8,000 blocks once the
    result set passes roughly 7,000–8,000 log rows.
  - Measured base rate: the `AuthorizationUsed` topic alone (topic0
    `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5`,
    see below) fires **~1.5 times per block** on the USDC contract, i.e.
    roughly **5.8–6.0 million events over a 90-day window**
    (90 days × 43,200 blocks/day, confirmed block time = 2.00s exactly from
    two on-chain timestamps 1,000,000 blocks apart). That volume includes
    *all* EIP-3009 usage on Base USDC — spend permissions, subscriptions,
    wallet features, etc. — not just x402. A full unfiltered pull of this
    event via public RPC, at ~5,000-block chunks, is ~780 requests just to
    enumerate — and every one of those events still needs its parent
    transaction pulled to learn who sent it (the log itself doesn't carry
    `tx.from`), which is another 5.8M RPC calls. **Not tractable inside this
    session with a free public RPC.**
  - Other free public RPCs tried (`base.llamarpc.com`, `base-rpc.publicnode.com`,
    `base.meowrpc.com`, `base.drpc.org`, `1rpc.io/base`) were each worse:
    down, archive-gated, `eth_getLogs` unsupported, timing out, or capped at
    50 blocks/call.

- **Base Blockscout REST API** (`https://base.blockscout.com/api/v2`, no key
  required): this is a hosted indexer, not a raw log scanner, and it changes
  the economics completely. It exposes:
  - `/addresses/{addr}/token-transfers?token={usdc}` — pre-decoded ERC-20
    Transfer rows (from, to, value, method, tx hash, timestamp) for one
    address, paginated.
  - `/addresses/{addr}/counters` — cheap activity check (tx count, transfer
    count) before committing to a full pull.
  - `/transactions/{hash}` and `/transactions/{hash}/logs` — full decoded
    calldata (`decoded_input`) and decoded logs, so `transferWithAuthorization`
    / `AuthorizationUsed` are returned already parsed, no ABI work needed.
  - `/search?q=...` — free-text search over addresses/tokens/names.

  **This is the chosen path.** It lets us query *by known facilitator
  address* directly (pull only the rows that touch a facilitator), instead of
  scanning the entire chain's USDC log stream. Direct RPC is still used
  opportunistically to cross-check specific facts (e.g., independently
  recomputing the `AuthorizationUsed` topic hash, spot-checking a raw log).

## Facts confirmed independently before relying on them

- **USDC contract on Base is
  `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.** Confirmed via BaseScan
  (labeled "Circle: USDC Token", verified proxy, `FiatTokenProxy`) and
  Base Blockscout (returns the live token metadata: symbol `USDC`, decimals 6,
  circulating supply, exchange rate ≈ $1.00). Independent sources agree.
- **`AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)`**
  topic hash: computed locally with Keccak-256
  (`Crypto.Hash.keccak`, not SHA3) as
  `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5`. As a
  sanity check on the hashing method itself, the same code produced
  `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` for
  `Transfer(address,address,uint256)`, which is the universally known ERC-20
  Transfer topic — confirms the computation is correct.
- **The EIP-3009 hypothesis holds, with a caveat.** Pulled a real transaction
  (`0x7e395c125198b6634fe2264d7e4fed043e8a33f1b78470bbffd3ea928d8aebad`) sent
  by a BaseScan/Blockscout-labeled address ("Coinbase: x402 Facilitator 1",
  tag links to `docs.cdp.coinbase.com/x402/welcome`). Its decoded calldata is
  exactly `transferWithAuthorization(from=<payer>, to=<facilitator>, value=990000, ...)`
  and it emits exactly two logs: `AuthorizationUsed` and `Transfer`. No third,
  x402-specific event exists on-chain that names the resource/merchant being
  paid for.
- **Important architectural finding — the "pooling" problem.** For this
  Coinbase-labeled address, USDC does **not** flow directly from payer to
  merchant in one transaction. The observed pattern across its transfer
  history is two separate legs:
  1. **Collect**: payer → facilitator address, via `transferWithAuthorization`
     / `receiveWithAuthorization` / a custom `batchTransferWithAuthorization`.
  2. **Payout**: facilitator address → merchant address(es), via a different,
     wrapped call (method selector `0xcef6d209`, invoked through the
     facilitator's own EIP-7702 delegation, sometimes bundling **two
     different recipients in one transaction**).
  There is no on-chain field linking a specific collect-leg transaction to a
  specific payout-leg transaction or recipient. **This means that, for
  facilitators that pool funds this way, the true payer→provider edge is not
  observable in public settlement data — only payer→facilitator and
  facilitator→(some recipient, batched with others) are.** This is a first-
  order threat to the Phase 3 question and is treated as a headline finding,
  not a footnote (see FINDINGS.md).
  - This has only been directly confirmed for the one facilitator address we
    decoded transaction-by-transaction. It is *not* assumed to generalize to
    every facilitator without evidence — the pipeline checks each facilitator
    it can find data for and records whether its `transferWithAuthorization`
    calls target the facilitator's own address (pooling) or a distinct
    third-party address (direct forward, which *would* preserve a visible
    payer→provider edge).

## Facilitator address candidates

No single authoritative on-chain registry of x402 facilitators exists. Two
sources were used, with different confidence levels:

1. **On-chain labels** (BaseScan / Blockscout name tags) — highest
   confidence, since these are curated by the block explorer, not
   self-reported. Only one address carries an explicit x402 facilitator tag
   at the time of writing: `0xdbdf3d8ed80f84c35d01c6c9f9271761bad90ba6`
   ("Coinbase: x402 Facilitator 1").
2. **`facilitators.x402.watch`**, a third-party community registry (fetched
   via WebFetch on 2026-09-05) listing ~16 named facilitators (Coinbase,
   Questflow, Heurist, X402rs, PayAI, CodeNut, AurraCloud, OpenX402, KAMIYO,
   Thirdweb, Daydreams, Ultravioleta DAO, Mogami, 402104, xEcho, Virtuals
   Protocol) and dozens of addresses across Base/Polygon/Solana. **This is an
   unauthenticated, self-reported community site — not verified as accurate.**
   Spot checks during this session found it to be a mix of live and stale
   data: e.g. three of the "X402rs" Base addresses and three of the "PayAI"
   Base addresses it lists show **zero transactions and zero token transfers**
   on Base Blockscout, while the Coinbase entry it lists matches the
   independently-labeled address above. **Every address from this registry is
   re-checked for actual on-chain activity (`/addresses/{addr}/counters`)
   before being used in the pipeline, and addresses with zero activity are
   dropped and logged, not silently kept.**

## Scope decision

Given the above, three things are downsized relative to the original brief,
and stated here rather than silently:

1. **Facilitator coverage is bounded by what we can verify.** We only trust
   an address as a "known facilitator" if (a) it carries an on-chain
   BaseScan/Blockscout label naming it as one, or (b) it appears in the
   x402.watch registry **and** shows real on-chain USDC/EIP-3009 activity when
   checked directly. Addresses that fail both checks are excluded, and the
   excluded list is kept in `data/raw/facilitator_candidates_checked.csv` for
   transparency.
2. **90-day window is attempted, but the achievable resolution depends on
   which facilitators turn out to be active.** Because we pull per-address
   history from Blockscout (not a full-chain scan), the cost no longer scales
   with total chain volume — but a facilitator with genuinely enormous volume
   (e.g., if the true Coinbase daily volume matches the "100M payments"
   figure) will need pagination limits; those are documented per-facilitator
   in the pipeline output, not assumed away.
3. **The payer→provider edge is only trustworthy where a facilitator does
   direct forwarding.** For pooling facilitators, Phase 3's bipartite graph
   is built from the **collect leg** (payer → facilitator), and the
   "provider" dimension collapses to "which facilitator," not "which
   merchant" — this is reported as a hard limitation, not smoothed over.
