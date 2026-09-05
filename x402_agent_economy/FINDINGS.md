# Measuring the x402 agent payment economy on Base — Findings

Data pulled 2026-09-05. Pipeline: `scripts/00`–`06`. Raw and processed data
in `data/raw/` and `data/processed/`. Full data-access investigation in
`notes/PHASE0_DATA_PATH.md`.

**Update (same day, after initial pass)**: `scripts/06_pull_bazaar_registry.py`
pulls Coinbase's own x402 Bazaar discovery registry — a live, unauthenticated,
first-party API most of the findings below did not originally use. It changes
the picture meaningfully; see "Phase 2 addendum" below before treating the
original recipient/volume numbers as complete.

## TL;DR

- We found **1,170 distinct payer wallets** making **17,337 EIP-3009
  settlements** worth **$6,195 in USDC** through **53 independently-verified
  x402 facilitator addresses** on Base, spanning (per-address) up to 90 days
  back to as far as Blockscout's history goes for low-volume addresses.
- **Cross-provider rotation is real, not trivial, but it's a minority
  behavior**: 123 of 1,170 payers (**10.5%**) paid more than one distinct
  recipient address directly; one wallet paid **44 distinct recipients**.
  This is the core question the brief asked, and the answer is a qualified
  yes — visible, but concentrated in a long tail, not the norm.
- **Payment behavior looks programmatic, not human.** 76% of payers with
  ≥2 settlements pay the *same amount* essentially every time (value
  coefficient of variation < 0.05); a third burst multiple payments within
  60 seconds of each other; and where we have enough events to measure a
  daily pattern (n≥5), activity concentrates strongly in a few hours of the
  day rather than spreading evenly (median normalized entropy 0.20 of 1.0).
- **A separate, independent signal points the same way**: among the top 150
  payers by activity, one single funding wallet supplied the initial gas for
  **40 of them** — a strong common-control signal, i.e., one operator running
  many nominally-separate payer wallets.
- **Our observed volume ($6,195) is far below the public reporting cited in
  the brief (~$41M cumulative, ~$28K/day).** We do not believe our filter is
  wrong — see "What this data does NOT support" — but this gap is real and
  reported, not smoothed over. The likely explanation is coverage, not
  methodology: our facilitator list is almost certainly incomplete (see
  below), and a large share of x402 volume, per a public Dune dashboard we
  could view but not query, moves through non-Base surfaces and gamified
  activity we deliberately did not chase.

## What we measured

- **Chain**: Base mainnet only.
- **Asset**: native USDC, `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`,
  independently confirmed via BaseScan and Blockscout (not taken on faith
  from the brief).
- **Mechanism**: EIP-3009 `transferWithAuthorization` /
  `receiveWithAuthorization` / `batchTransferWithAuthorization` calls
  submitted by addresses we independently confirmed are x402 facilitators.
- **Window**: targeted 90 days; actual per-address coverage varies (see
  "Coverage caveats").

## How we got the data (short version)

No paid API access (Dune, BigQuery, Alchemy/QuickNode) was available in this
environment. We evaluated all three per the brief's Phase 0 instructions —
full writeup in `notes/PHASE0_DATA_PATH.md`. In short: Dune has a relevant
public dashboard but no queryable API key was available; BigQuery is
network-reachable but requires GCP credentials we don't have; free public
Base RPC (`mainnet.base.org`) cannot scan the chain's full
`AuthorizationUsed` event stream (~1.5 events/block, ~6M events over 90
days, mostly unrelated to x402 — hits both a 10,000-block range cap and a
tighter, undocumented response-size cap around 5,000–8,000 blocks).

**Chosen path**: the free, unauthenticated **Base Blockscout REST API**
(`base.blockscout.com/api/v2`), which lets us query *by known facilitator
address* — pulling only the transactions a facilitator actually sent,
already fully decoded (`decoded_input`), rather than scanning the whole
chain. This is what made the analysis tractable at all without paid infra.

## A finding we did not expect: two different settlement architectures

The brief's working hypothesis — a facilitator relays a payer's signed
authorization straight to the merchant — turns out to be **one of two
patterns actually in use on Base**:

1. **Direct forward** (the overwhelmingly dominant pattern in our data:
   17,336 of 17,337 collect-leg rows, 99.99%): the facilitator submits
   `transferWithAuthorization(payer, merchant, amount, ...)` with the payer
   and the real merchant as the transfer's two actual parties. The
   facilitator only pays gas. **This preserves a genuine, on-chain-visible
   payer→provider edge** — this is what makes Phase 3 answerable at all.
2. **Pooled / custody**: the facilitator submits the authorization with
   *itself* as recipient (a "collect" leg), then separately pays merchants
   out of its own balance later, in batched transactions that can bundle
   multiple unrelated merchant payouts together. We confirmed this pattern
   is real by manually decoding a historical transaction from the
   BaseScan-labeled "Coinbase: x402 Facilitator 1" address
   (`0xdbdf3d8ed80f84c35d01c6c9f9271761bad90ba6`): a
   `transferWithAuthorization` call moving USDC from a payer into that
   facilitator's own address, followed later by a `redeemDelegations` call
   (MetaMask's Delegation/Gator framework) paying out to two unrelated
   merchant addresses in a single transaction. **For this pattern, the
   payer→provider edge does not exist in public data** — only
   payer→facilitator and facilitator→(some merchant, batched) are visible,
   and they cannot be joined without off-chain reconciliation data the
   facilitator alone holds.

This matters for interpreting our headline numbers: that specific pooling
example predates our 90-day window (from Oct/Nov 2025), and within the
window we could actually pull, that same facilitator's addresses show
almost entirely direct-forward traffic. **We cannot rule out that pooling
is a larger share of total x402 volume than our data shows — only that it
is not how most of what we could observe recently settles.** Every
settlement row is tagged `pooled: true/false` in
`data/raw/settlements_collect.csv` for exactly this reason.

## Facilitator coverage and its limits

We checked 57 candidate facilitator addresses on Base and confirmed **53**
have real on-chain USDC/EIP-3009 activity (full accept/reject list:
`data/raw/facilitator_candidates_checked.csv`). Sources:

- **On-chain name tags** (BaseScan/Blockscout) — highest confidence. Only
  one address in our list carries an explicit tag ("Coinbase: x402
  Facilitator 1").
- **`facilitators.x402.watch`**, a third-party community registry — every
  address from it was independently re-checked for real activity before
  use; 4 of 57 candidates failed this check and were dropped (visible in
  the CSV, not silently discarded).

Confirmed facilitators, by brand, and how many of their addresses we
verified active: Coinbase CDP (10), Questflow (10), Heurist (8), X402rs (6),
PayAI (4), CodeNut (4), AurraCloud (3), OpenX402 (2), and one address each
for Daydreams, Ultravioleta DAO, Mogami, 402104, xEcho, and Virtuals
Protocol.

**A striking pattern**: nearly every brand operates many separate relayer
addresses (Coinbase alone: 10), each with a comparatively modest transaction
history (tens to low thousands of calls). This looks like deliberate
load-balancing/rotation across relayer wallets rather than one address
handling all traffic — which is also *why* per-address volume looked small
enough to make this pipeline tractable on a free API, and *why* our total
observed volume is very likely a fraction of true total volume: **we have
no way to know how many relayer addresses per brand we're missing**, and
brand-new or undiscovered facilitators are invisible to this method
entirely.

## Coverage caveats (read before trusting any count above)

- Per-facilitator-address pulls are capped at 60 pages (~3,000 transactions)
  to keep this tractable on a shared free API. **4 of 53 addresses hit this
  cap or a request failure before reaching either the 90-day cutoff or the
  end of their history** — their contribution to every number above is a
  lower bound, not complete. Full list: `data/raw/incomplete_pulls.txt`.
- For low-volume addresses, coverage actually extends well past 90 days
  (our earliest observed settlement is from **2025-10-24**, ~10 months back)
  because pagination simply reached the address's genesis transaction before
  reaching a page cap. For high-volume addresses, coverage is closer to a
  true 90-day window. **The window is not uniform across facilitators.**
- We did not attempt to enumerate facilitators beyond the sources above.
  Genuine x402 activity through any facilitator address not in our list is
  excluded, not zero.

## Phase 2 — recipients

`data/processed/recipients_labeled.csv`: **275 distinct recipient
addresses**, $6,195 total volume (direct settlements only — pooled volume in
our data is negligible, $0.01).

- **100% of recipient volume is "unknown" by name/category.** We checked
  every recipient address for a BaseScan/Blockscout name tag; none had one.
  This is reported honestly, not smoothed over — **the unlabeled fraction is
  100%, and every conclusion about *what kind* of service these providers
  are is bounded by that.** We did not guess.
- We could still distinguish **contract vs. externally-owned account**: 54
  of 275 recipients (20%) are smart contracts, 221 (80%) are plain wallets.
  This is consistent with x402's design — the protocol checks payment at the
  HTTP layer, so a "provider" only needs a wallet address, not an on-chain
  contract — but it also means most recipients look like individual
  operators or small services, not identifiable platforms.
- **Per-facilitator payment-size fingerprints are informative even without
  names.** Some facilitators show a handful of fixed price points (Coinbase
  CDP: 7 distinct values across 441 settlements; Daydreams: 3 distinct
  values; 402104: 11) — consistent with metered API/inference pricing tiers.
  Others show far more variation (Questflow: 265 distinct values across 500
  settlements; xEcho: 302 distinct values across 2,200) — consistent with
  either variable-cost billing (e.g., token-metered inference) or a more
  heterogeneous mix of use cases we can't distinguish from here. Heurist (a
  publicly known decentralized GPU compute marketplace) shows very low,
  tightly clustered payment sizes (median $0.01, 26 distinct values across
  4,892 settlements) — the single clearest fingerprint of metered compute
  billing in our data.
- We explicitly did **not** find or label any gamified/pay-to-mint activity
  within our confirmed-facilitator dataset — but we also did not go looking
  inside individual recipient addresses' broader activity to rule it out.
  Two of our confirmed facilitator brands (Virtuals Protocol, an AI-agent
  tokenization platform, and Mogami) have names associated with token/agent
  launch ecosystems; we flag this as **unresolved**, not excluded, per the
  brief's instruction to label conservatively.

## Phase 2 addendum — Coinbase's own Bazaar registry gives real names and much bigger numbers

`scripts/06_pull_bazaar_registry.py` calls `api.cdp.coinbase.com/platform/v2/x402/discovery/resources`
— a live, unauthenticated, first-party endpoint that lists every resource
registered with the CDP facilitator's Bazaar extension, each with a real
`payTo` address, price, and a `quality` block (`l30DaysTotalCalls`,
`l30DaysUniquePayers`) computed by Coinbase's own facilitator accounting —
not inferred by us. We pulled the full registry: **16,556 resources**, of
which **16,101 are on Base mainnet**.

**This is a fundamentally different, mostly non-overlapping slice of the
ecosystem from Phases 1–4 above.** Only 7 of our 275 on-chain-derived
recipient addresses also appear as Bazaar `payTo` addresses — the two
methods are sampling largely different facilitator populations (our pipeline
leans on Heurist/X402rs/Questflow/etc.; the Bazaar only covers CDP-facilitator
merchants that opted into the discovery extension).

**Named, recognizable companies do show up** — something the on-chain-only
approach in Phases 1–4 could not produce (100% of those 275 recipients had
zero on-chain name tags):

- **Bitrefill** (`api.bitrefill.com`) — real gift-card/bill-pay company;
  $27,000 implied 30-day volume from just 168 calls (enterprise-scale, not
  micropayments).
- **Chainlink** (`agents.chain.link`) — 52,422 calls in 30 days at $0.01
  each; a metered micro-service, not a headline dollar figure, but by far
  the highest call volume of any single identified brand.
- **Apify** (`agi.apify.com`, `api.apify.com`) — real web-scraping/automation
  platform.
- **Arkham Intelligence** (`api.arkm.com`) and **Nansen** (`api.nansen.ai`)
  — both real, known on-chain analytics companies.

**We did not find Stripe or any major neocloud (Together, Fireworks,
Replicate, RunPod, CoreWeave, Hyperbolic, Modal, etc.) as a first-party
Bazaar-registered merchant.** The only "Stripe" hits are a third-party
company-research API (`predictleads`) selling data *about* Stripe, not
Stripe itself, and the one "Baseten" hit is a third-party proxy wrapping
Baseten's API, not Baseten's own listing. This is consistent with (not
proof of) the architectural reason given previously: Stripe's x402
implementation mints a fresh, disposable receiving address per transaction,
which structurally can't appear as a stable, repeated `payTo` in a registry
like this one. Major neoclouds may simply not have opted into Coinbase's
specific discovery index, even where they support x402 directly (Hyperbolic
has a public x402 integration with no published address, per our own check).

**Aggregate volume implied by this registry is bigger than what we found
on-chain, and we should not take Coinbase's self-reported numbers as ground
truth either.** Summing `price × l30DaysTotalCalls` across all 16,101 Base
resources gives **$37,095** in implied 30-day volume ($10,095 excluding the
single Bitrefill outlier) — both bigger than our entire on-chain figure of
$6,195 accumulated across a much longer window. But we spot-checked one
entity (Arkham) directly against real on-chain transfers to that `payTo`
address and found the **on-chain rate implies substantially more than the
399 calls/30-days Coinbase reports** — 50 confirmed `transferWithAuthorization`
calls landed in under 2 days from a single payer alone. So the Bazaar's
self-reported quality metrics likely *undercount* real usage too; neither
source alone should be trusted as complete.

**The clearest evidence yet for the core research question came from this
spot-check, not from the original pipeline.** The heavy payer found while
verifying Arkham's numbers (`0x27AbCDdd44c4959aC729D080703e677f13A3248c`)
paid **29 distinct recipient addresses in its 50 most recent transactions**,
including confirmed Bazaar entries for **Apify** and a data-feed company
(`theaslangroupllc.com`, energy/stablecoin data APIs), alongside Arkham
itself. This is a real, named, on-chain-verified example of a single agent
wallet rotating across multiple identifiable commercial providers — exactly
what Phase 3 was looking for, just found through the Bazaar cross-reference
rather than the original facilitator-address pipeline.

**What this addendum does not support**: we have not re-run Phases 3/4
(payer graph, behavioral features) against Bazaar-identified recipients —
`data/processed/bazaar_entities_ranked.csv` is a registry snapshot, not
settlement-level data, so it can't feed the payer-feature pipeline directly
without pulling each `payTo` address's own on-chain transfer history (as we
did manually for Arkham). That's the natural next step, not yet done.

## Phase 3 — the rotation question

`data/processed/payer_features.csv`: **1,170 distinct payer wallets**.

Distribution of distinct DIRECT recipients per payer (the trustworthy edge,
excluding pooled settlements):

| distinct recipients | payers |
|---|---|
| 1 | 1,047 |
| 2 | 104 |
| 3 | 11 |
| 4 | 2 |
| 6 | 1 |
| 7 | 1 |
| 8 | 1 |
| 12 | 2 |
| 44 | 1 |

**123 of 1,170 payers (10.5%) used more than one distinct recipient.** This
is a real, non-trivial tail — not the "empty or trivially small" outcome the
brief flagged as a valid possibility, but also not the dominant behavior:
90% of payers we observed stuck to a single recipient in this window. We did
not attempt fine-grained timing classification (sequential vs. concurrent
multi-provider use) for the multi-provider group beyond what's in Phase 4 —
that's a natural next step on this same dataset.

**A caveat that cuts against over-reading the 89.5% single-provider
figure**: the funding-source analysis below shows a single operator can
control dozens of nominally separate payer wallets. If that operator
deliberately uses one wallet per provider (plausible for API-key-style
isolation), true agent-level multi-provider behavior would look identical,
in our data, to many separate single-provider payers. **We can distinguish
"providers per wallet" cleanly; we cannot cleanly distinguish "providers per
operator" without the funding-cluster analysis below, which we only ran on
a 150-wallet sample.**

### Funding-source clustering

`data/processed/payer_funding_sources.csv`, run on the top 150 payers by
settlement count: 106 of 150 funding sources resolved to a genesis
transaction. **10 funding addresses fund more than one payer wallet in this
sample**, and one of them funds **40 distinct payer wallets** — by far the
strongest common-control signal in this dataset, well beyond what behavioral
similarity alone could establish. That funding address itself carries no
on-chain name tag; we make no claim about who operates it, per the brief's
scope limit against identity linkage.

## Phase 4 — behavioral signal

Computed for all 1,170 payers where the underlying event count allows it
(full detail in `data/processed/payer_features.csv`):

- **Value regularity**: median coefficient of variation of payment size is
  **0** across payers with ≥2 settlements, and **76%** of them have CV below
  0.05 — i.e., most payers pay the *same amount* essentially every time.
  This is the single strongest programmatic-activity signal we found: fixed
  per-call pricing is a machine-billing pattern, not a human spending
  pattern.
- **Burst structure**: among payers with ≥2 settlements, **32%** have more
  than half of their inter-payment gaps under 60 seconds — rapid-fire calls
  clustered together, consistent with a script making several calls in one
  session.
- **Diurnal cycle**: for the 136 payers active enough to measure (≥5
  settlements), the median normalized hour-of-day entropy is **0.20** (0 =
  all activity in one hour, 1 = perfectly uniform across all 24). Activity
  is concentrated, not spread evenly — but we can't distinguish a human's
  waking hours from a scheduled batch job from this alone; we report the
  concentration, not a cause.
- **Wallet lifetime**: median observed lifetime is effectively instantaneous
  (most payers appear, transact once or a few times close together, and
  aren't seen again in-window) — **544 of 1,170 (46.5%) have exactly one
  settlement**. But there is a persistent tail: **39 payers were active over
  a span longer than 30 days.** This is closer to "mostly burn-and-replace,
  with a real persistent minority" than either pure pattern.
- We did **not** attempt the optional ERC-8004 cross-reference (agent
  registry lookup) — out of scope for the time available on this pass; it's
  a natural extension given the payer address list this pipeline already
  produces.

## What this data does NOT support

- **No claim about total x402 volume** across all facilitators, chains, or
  unidentified/undiscovered Base facilitator addresses — only what we could
  verify. Our $6,195 figure is a floor, not an estimate of the true total;
  the gap to public reporting's ~$41M/~$28K-per-day figures is almost
  certainly a coverage gap (missing facilitator addresses, other chains,
  gamified activity we didn't chase) rather than evidence those figures are
  wrong.
- **No wallet-to-real-identity linkage** was attempted or is supported by
  this analysis, including for the common-control funding cluster found
  above.
- **Providers-per-payer counts for pooled traffic are a lower bound at
  best** — a payer using two providers that share a pooling facilitator is
  invisible to this method. Our data happens to contain almost no pooled
  settlements, but that reflects our 90-day/60-page window, not an
  assumption that pooling doesn't happen at scale.
- **Recipient categorization is not a service-type classification.** We
  found zero on-chain name tags for any of the 275 recipients; contract-vs-
  EOA and payment-size fingerprints are the only signals we have, and they
  are suggestive, not confirmatory, of what kind of service each recipient
  runs.
- **The diurnal and burst statistics describe concentration, not cause.**
  We have not shown these patterns are AI-agent-specific rather than, say,
  a human developer testing a script in short sessions.
