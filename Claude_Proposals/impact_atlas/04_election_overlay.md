# Election Overlay: Did AI Exposure Shape Voting in 2026 (and Will It in 2028)?

*Status: Prototype shipped (King County, WA, unofficial election-night results). Nov 7, 2026.*

## The question

> Were there differential voting patterns based on (perceived) AI job-disruption potential?

There are two different questions inside this one:

1. **Measured exposure → aggregate vote** (answerable now, ecologically): did places whose
   workforces are more AI-exposed swing differently, *conditional on* the things that already
   drive swing?
2. **Perceived threat → individual vote** (needs survey data): did voters who *believe* AI
   threatens their job vote differently? This is the real question. Precinct data can't
   answer it.

The prototype addresses (1) and lays groundwork for (2).

## What was built

| Piece | File |
|---|---|
| National **census-tract** exposure index (85,382 tracts), same Bartik construction as the county map, plus BA+ share and median income as controls | `src/pipeline/06_tract_exposure.py` → `data/processed/tract_exposure.parquet` |
| King County precinct results (2026 + 2024) and precinct and tract boundaries | `src/pipeline/07_download_elections.py` |
| Area-weighted crosswalks, tract-level regressions, map export | `src/pipeline/08_election_overlay.py` → `src/map/data/elections/king_2026.json` |
| Map page: precinct or tract units; layers for exposure, 2026 D share, swing, BA+; binned scatter; model table | `src/map/elections.html` |

Tract data comes from the ACS **table-based Summary File bulk downloads**, not the Census API.
As of Nov 2026 the API refuses requests that lack a key, and the bulk files include every tract.

### Design choices

- **Why King County.** It posts machine-readable precinct CSVs on election night. WA votes
  entirely by mail, so a large share of ballots is counted early. Boundaries for every year are
  on ArcGIS REST. And there is a wide within-county exposure range (Eastside tech vs.
  south-county logistics).
- **Outcome.** swing = D two-party share in the 2026 US House race minus D two-party share for
  2024 President. 2024 House can't serve as the baseline because CD-9 was D-vs-D in 2024.
  Congressional-district fixed effects absorb candidate effects.
- **Like-for-like snapshots.** The 2026 election-night count is compared with the 2024
  election-night count. Late WA ballots lean young and Democratic. Even so, the 2026 snapshot
  is about 50% of expected ballots versus about 68% for 2024, so the comparison isn't fully
  matched.
- **Inference at the tract level** (n ≈ 492). Exposure is only measured at the tract.
  Precinct-level regressions would count interpolated copies of one tract value as independent
  observations. Precincts are for display only.

## First results (election-night, unofficial — will move)

Effect on swing of +1 SD of tract exposure (1 SD ≈ 2.7 index points), tract-level WLS weighted
by ballots, HC1 SEs:

| Specification | Swing toward D | Turnout ratio 26/24 |
|---|---|---|
| No controls | **−2.00 pp** (0.18) | +0.009 (0.003) |
| + BA+ share | +1.24 pp (0.19) | −0.017 (0.004) |
| + log income, 2024 D share, CD FE | **+0.69 pp** (0.18) | −0.024 (0.004) |

Countywide: 2026 House D 78.3% vs 2024 Harris 77.0% (+1.3 pp), with 535,712 ballots counted
on election night.

**How to read this.** Raw, higher-exposure tracts swung *less* toward Democrats. Exposure
correlates **r = 0.78 with BA+ share**, though, and education is the dominant swing predictor
(r = −0.79 with swing). Once education is controlled the sign flips. That pattern is what
confounding looks like. It is not an AI effect. With r = 0.78 and a noisy ACS education measure,
some residual confounding is still expected, and the exposure coefficient can absorb it. The
+0.7 pp is not a causal estimate and shouldn't be reported as one.

## Why precinct data can't settle this (now or in 2028)

1. **Collinearity with education.** In most metros, occupational AI exposure and college
   education are close to the same variable. Separating them needs either within-education
   variation (e.g. call-center and back-office towns: high exposure, low BA+) or individual data.
2. **Ecological inference.** A precinct where exposed workers live and which swung tells you
   nothing about whether the exposed workers swung.
3. **Measured ≠ perceived.** The index measures where Claude is *used* for an occupation's tasks.
   Perceived threat may track news exposure, age, or partisanship more than it tracks occupation.
4. **Midterm composition.** Midterm electorates skew toward older, more educated voters, so
   differential turnout gets mixed into the swing measure.

## Did 2026 polls already ask about AI?

Partly. Our reading of the published toplines (verify against the primary releases before
citing):

- The **Fox News Voter Poll** (SSRS, ~80k voters, Oct 19–Nov 3) appears to include AI items on a
  half-sample: importance of "AI and data centers" to the congressional vote, whether AI will do
  more to help or hurt society, local data-center construction, and which party better handles
  AI. *Toplines were read from a model summary of a truncated page and are not verified.*
- **CBS/YouGov exit poll:** prose only. "More voters see AI as doing more to harm society than to
  help it." Majorities in Senate battlegrounds oppose local data centers.
- **AP Voter Poll:** "neither party" was the plurality answer on handling AI. No AI-and-jobs item
  was found.

**Gap.** None of these items asks about AI and *the respondent's own job*. What they measure is
data-center siting and general AI sentiment. No state- or county-level breakdown was published.

## Plan toward 2028

**Before final results (late Nov 2026)**
- [ ] Re-run once King County posts its mid-election and final precinct files. Update `RESULTS`
      in `07_download_elections.py`. Switch both years to `final`.
- [ ] Add 2–4 more counties with fast precinct CSVs and different exposure-by-education profiles.
      Candidates: Ada County ID (CSV is up), Oklahoma (statewide precinct export), Hamilton County
      OH. Ideally include a call-center or back-office county where exposure is high and BA+ is low.
- [ ] Robustness: theoretical (Eloundou β) exposure; the new Anthropic **robot-exposure** index
      (Sept 2026) as a placebo or contrast, since physical-automation exposure has a different
      geography; population-weighted interpolation using 2020 block counts instead of area weights.

**2027**
- [ ] National precinct file: when VEST/Redistricting Data Hub release 2026 precinct results
      with boundaries, run nationally with state FE.
- [ ] Individual-level: when **AP Voter Poll / Fox Voter Poll microdata** reach Roper or ICPSR,
      link respondents' county or ZIP to tract or county exposure. With **CES 2026**, link each
      respondent's *reported occupation* to the occupation-level exposure score. That is a far
      better test than geography, because it measures the voter's own exposure.
- [ ] Pitch a team module for **CES 2028** (proposals typically due ~early 2028):
      *"How likely is it that AI will eliminate or substantially change your job in the next
      5 years?"* plus occupation. That makes "perceived" measurable and lets us compare
      perceived and measured exposure directly.
- [ ] Lobby exit-poll consortia (AP, NEP/Edison, Fox/SSRS) to add an own-job AI item for 2028,
      reported by state.

**Identification ideas worth exploring**
- Within-education comparisons: stratify by BA+ decile and look at exposure slopes within strata.
- Shift-share IV. Exposure here is a Bartik construction, and Borusyak–Hull–Jaravel-style
  exogenous-shares checks apply, so test balance of the occupation shares on 2016–2020 swing.
- Event-study framing: 2016→2020→2024→2026 swing by exposure, with pre-trends visible. A 2026
  divergence would only be meaningful if there were no pre-trends.

## Data notes

- Results: King County Elections, `election-night-results-report.csv` (2024 and 2026), unofficial.
- Boundaries: King County GIS `VOTDST_AREA_418` (current) and `VOTDST_2024_AREA_3068`. TIGER 2024 tracts.
- 99% of 2026 precinct names also existed in 2024. 2024 votes are area-interpolated onto 2026
  precincts. Votes are conserved to within 0.03%.
- King County's metadata on some older layers restricts redistribution. Check the current terms
  before republishing the boundary-derived GeoJSON publicly.
