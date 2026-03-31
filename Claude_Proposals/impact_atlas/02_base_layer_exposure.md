# Phase 1: AI Exposure Base Layer

## Objective

Construct a county-level (or finest feasible geographic unit) AI exposure index for the United States by combining occupation-level AI exposure scores with local workforce composition data. Ship an interactive choropleth map as the first deliverable.

## Approach: Synthetic AI Exposure via Shift-Share

The core method is a Bartik-style shift-share construction:

**AI_Exposure(county) = Σ [ share_of_workforce_in_occupation(county) × exposure_score(occupation) ]**

For each county, we compute a weighted average of occupation-level AI exposure, where the weights are the share of the local workforce employed in each occupation. Counties with lots of customer service reps and programmers will score highly; counties dominated by construction and healthcare will score low.

This is the same logic used in the China shock literature (Autor, Dorn & Hanson 2013) and widely accepted in labor economics for constructing geographic exposure to national-level shocks.

## Data Inputs

### Occupation-Level AI Exposure Scores

**Primary source: Anthropic's labor market impacts data (March 2026)**

Released on HuggingFace at `Anthropic/EconomicIndex/labor_market_impacts/`. This contains:

- **Task-level exposure**: Each O*NET task scored for theoretical AI feasibility (Eloundou β scores: 0, 0.5, 1.0) AND observed Claude usage from the Economic Index
- **Occupation-level exposure**: Tasks aggregated to ~800 occupations, weighted by time-spent-on-task, producing the "observed exposure" metric

The "observed exposure" metric is particularly valuable because it combines *theoretical capability* with *real-world adoption*, weighted toward automation over augmentation. Key occupation scores from the paper: Computer Programmers (74.5%), Customer Service Reps (60%+), Data Entry (60%+), down to near-zero for cooks, mechanics, lifeguards.

**Secondary / complementary sources (for robustness checks)**:

- Felten, Raj & Seamans (2023) — AI Occupational Exposure index (capability-based, no usage data)
- Eloundou et al. (2023) — raw theoretical β scores without the observed usage weighting
- Webb (2020) — patent-based AI exposure measure

Using multiple exposure measures lets us check whether geographic patterns are robust to different definitions of "exposure."

### Geographic Workforce Composition

**Primary source: American Community Survey (ACS) 5-year estimates**

- Available via Census API
- Provides occupation counts by detailed SOC code for every county, MSA, and census tract
- 5-year estimates (e.g., 2019-2023) give reliable counts even for small geographies
- Key table: B24010/B24020 (Sex by Occupation for the Civilian Employed Population 16+) or S2401 (Occupation by Sex and Median Earnings)

**Geographic unit decision**:


| Unit           | N        | Occupation detail                                              | Practical notes                                             |
| -------------- | -------- | -------------------------------------------------------------- | ----------------------------------------------------------- |
| County         | ~3,100   | Good (detailed SOC for large counties, major groups for small) | Familiar to policymakers; good default                      |
| Commuting Zone | ~740     | Good (aggregated from counties)                                | Better labor market boundaries; less familiar               |
| Census Tract   | ~70,000+ | Limited (only major occupation groups)                         | Opportunity Atlas resolution but too noisy for this purpose |
| PUMA           | ~2,350   | Very good (microdata aggregation)                              | Best granularity-detail tradeoff via ACS PUMS               |


**Recommendation**: Start with **county-level** using ACS summary tables. Explore **PUMA-level** as a higher-resolution alternative if ACS PUMS microdata offers sufficient occupational detail. Aggregate to commuting zones as an alternative view.

**Challenge**: ACS detailed-occupation data at the county level may be suppressed for small counties. Will need to assess how much coverage we get at the detailed SOC level vs. needing to use major occupation groups (which are coarser but universally available).

### Crosswalk

O*NET → SOC mapping is straightforward (O*NET codes are extensions of SOC codes). The Anthropic data uses O*NET task statements mapped to SOC. ACS uses SOC. The main question is whether Anthropic's exposure data is at 6-digit SOC detail or aggregated to broader groups — need to verify once we download the data.

## What "Exposure" Means — and the Capabilities Toggle

### Current-State Exposure (v1)

The initial map will use Anthropic's "observed exposure" scores, which reflect **current AI capability AND current adoption patterns** as of late 2025. This is the most conservative and empirically grounded version: it shows where AI is *actually* being used, not where it *theoretically could* be used.

### Theoretical Exposure (v1.5)

A second layer using the raw Eloundou β scores (theoretical feasibility regardless of current adoption). This answers: "If everything that's theoretically possible with current LLMs were actually deployed, what would exposure look like?" The gap between observed and theoretical exposure is itself an interesting map — it shows where there's latent displacement risk that hasn't materialized yet.

### Capability-Threshold Forecasting (Future)

The more ambitious version: a toggle that says "If AI systems achieve capability level X on benchmark Y, then exposure changes as follows." This requires:

- Mapping specific capability benchmarks (METR task completion, SWE-bench, etc.) to the Eloundou task feasibility framework
- Defining which tasks "unlock" at which capability thresholds
- Recomputing exposure under each scenario

This is complex but powerful — it turns the atlas from a static snapshot into a scenario planning tool. It's also what would make the tool genuinely useful for forward-looking policy. Deferred to Phase 3 but worth building the data architecture to support from the start.

## Implementation Plan

### Step 1: Download and validate exposure data

- Pull Anthropic's `labor_market_impacts` data from HuggingFace
- Examine structure: what level of SOC detail? What variables exactly?
- Pull Eloundou scores for comparison

### Step 2: Pull ACS workforce composition

- Census API: county-level occupation counts (ACS 5-year, most recent available)
- Assess occupational detail available vs. what's needed
- Build SOC crosswalk between ACS occupation categories and Anthropic's exposure codes

### Step 3: Compute county-level exposure index

- Join exposure scores to ACS occupation counts
- Compute weighted average exposure per county
- Produce both "observed exposure" and "theoretical exposure" versions
- Output as a table: FIPS code, county name, state, exposure score(s), top contributing occupations

### Step 4: Build the map

- Get county-level GeoJSON/TopoJSON shapefiles (Census TIGER/Line)
- Join exposure data to geometries
- Build interactive choropleth (Mapbox, Leaflet, or D3)
- Add hover/click details: county name, exposure score, top exposed occupations, workforce size
- Deploy as a static site (GitHub Pages) or lightweight app

### Step 5: Validate and sanity-check

- Do the geographic patterns make sense? (Tech hubs should be high; rural agricultural counties should be low)
- Compare county-level synthetic estimates against Anthropic's state-level direct data — do they correlate?
- Check sensitivity to different exposure measures (Anthropic vs. Felten vs. Eloundou)
- Check sensitivity to occupation detail level (detailed SOC vs. major groups)

## Output

An interactive map at [TBD URL] showing AI exposure by county across the US, with:

- A choropleth color scale for exposure intensity
- Toggle between "observed" and "theoretical" exposure
- Click/hover for county detail (exposure score, top exposed occupations, workforce summary)
- Accompanying methodology write-up

This is the foundation everything else builds on.

---

## Things We're Not Going to Do (Yet)

### Direct Claude Usage Mapping (Original "Option A")

Anthropic's geographic data includes state-level Claude usage per capita. One could simply map this directly as a measure of "where AI adoption is happening." We're not pursuing this because:

- It's only 51 data points (states + DC), too coarse for a meaningful atlas
- It measures adoption of *one* AI system, not exposure to AI disruption broadly
- It conflates consumer and professional usage
- Anthropic has already visualized this in their geographic report

However, state-level Claude usage data is valuable as a **validation layer** — our synthetic county-level exposure estimates, aggregated to the state level, should correlate with Anthropic's direct adoption measures. If they don't, that's informative (and concerning). We'll use it for validation in Step 5 but not as the primary map.

### Augmentation vs. Automation Split (Original "Option C")

The Economic Index distinguishes augmentation (human + AI collaborating) from automation (AI replacing human effort) at the task level. One could construct *two* separate exposure indices: one for augmentation-heavy occupations, one for automation-heavy ones, and map where each concentrates geographically. This is analytically important because the policy implications differ: augmentation-heavy regions may see productivity gains and wage premiums, while automation-heavy regions face displacement risk.

We're deferring this because:

- It adds complexity to the base layer before we've validated the simpler version
- The augmentation/automation distinction in Anthropic's data requires careful interpretation (the stated vs. revealed gap from the Interviewer study suggests people misperceive which mode they're in)
- It's a natural "Phase 1.5" extension once the base map is working

This split is a high-priority next step and would make the atlas substantially more useful for policy audiences.

---

*Status: Ready for implementation in Claude Code.*