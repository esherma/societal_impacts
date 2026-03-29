# AI Impact Atlas

**Goal**: Build a geography-based tool for analyzing and forecasting exposure to AI-driven labor market disruptions — an "Opportunity Atlas for AI."

Inspired by Chetty et al.'s Opportunity Atlas, which made neighborhood-level economic mobility data spatially legible to non-researchers, the aim is to do the same for AI's economic impacts: which communities are most exposed, which are best positioned to adapt, and how those answers change as AI capabilities advance.

## The Core Idea

Existing research on AI's labor market impacts operates at national or occupation-level aggregates. Anthropic's own labor market impacts paper (March 2026) contains no geographic analysis. But the effects of AI on labor markets are inherently geographic: a county where 40% of the workforce does customer service work faces a very different AI future than one dominated by construction or healthcare.

The plan is to link occupation-level AI exposure data (from Anthropic's Economic Index, Eloundou et al., and related sources) with fine-grained geographic workforce composition data (ACS/Census) to produce county-level estimates of AI exposure across the US, layered with outcome data and vulnerability indicators.

## Methodology

The core construction is a Bartik-style shift-share:

```
AI_Exposure(county) = Σ [ share_of_workforce_in_occupation(county) × exposure_score(occupation) ]
```

This is the same logic used in the China Shock literature (Autor, Dorn & Hanson 2013) for constructing geographic exposure to national-level economic shocks.

## Project Structure

```
/
├── src/                    # Source code (data pipelines, map, analysis)
├── data/                   # Data files (raw inputs, processed outputs)
└── Claude_Proposals/       # Project ideation and design documentation
    ├── impact_atlas/       # AI Impact Atlas — active development
    │   ├── 01_project_summary.md
    │   ├── 02_base_layer_exposure.md
    │   └── 03_future_overlays_and_analyses.md
    └── speculative/        # Exploratory ideas for future AI impacts projects
        ├── 01_clio_displacement_surveillance.md
        └── 02_interviewer_project_ideas.md
```

## Roadmap

**Phase 1 — Base Map (Active)**
Construct a synthetic AI exposure index at the county level by combining Anthropic's occupation-level exposure scores with ACS workforce composition data. Ship an interactive choropleth map and a short methodology report.

**Phase 2 — Outcome Overlays**
Layer labor market outcomes (employment trends, wage changes, job postings) and structural vulnerability indicators (education, income, demographics, industry concentration) onto the base map.

**Phase 3 — Forecasting & Causal Analysis**
Introduce a capability-threshold toggle for scenario modeling ("if AI achieves X on benchmark Y, exposure looks like this"). Pursue shift-share IV and difference-in-differences analyses to estimate causal effects on local labor markets.

**Phase 4 — International Extension**
Repeat data collection and analyses for other countries, to the extent feasible.

## Data Sources

| Data | Source | Use |
|------|--------|-----|
| Occupation-level AI exposure scores | [Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex) | Primary exposure measure |
| Theoretical LLM exposure (β scores) | Eloundou et al. (2023) | Robustness check |
| AI Occupational Exposure Index | Felten, Raj & Seamans (2023) | Robustness check |
| Workforce composition by county | ACS 5-year estimates (Census API) | Geographic weights |
| County shapefiles | Census TIGER/Line | Map geometry |
| State-level Claude usage | Anthropic geographic report | Validation |

## Deliverables

1. Interactive web-based map (the Atlas)
2. Methodology report and initial findings write-up
3. Open-source code and data pipeline for reproducibility
4. Subsequent reports as new layers and analyses are added

## Related Work

- **Opportunity Atlas** (Chetty et al., 2018) — methodological and presentation model
- **China Shock** (Autor, Dorn & Hanson, 2013) — canonical shift-share approach for geographic economic shocks
- **Anthropic Economic Index** (2025–2026) — source of occupation-level observed exposure metrics
- **Eloundou et al. (2023)** — theoretical LLM task feasibility scores
