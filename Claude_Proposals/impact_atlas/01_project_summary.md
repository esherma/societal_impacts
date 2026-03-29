# AI Impact Atlas: Project Summary

## Vision

Build a geography-based tool for analyzing and forecasting exposure to AI-driven labor market disruptions — an "Opportunity Atlas for AI."

The Opportunity Atlas (Chetty et al.) showed that where you grow up shapes your economic future, and it changed the policy conversation by making neighborhood-level data spatially legible to non-researchers. The AI Impact Atlas aims to do the same for the question of where AI's economic effects are landing: which communities are most exposed, which are best positioned to adapt, and how those answers change as AI capabilities advance.

## Core Idea

Link occupation-level AI exposure data (from Anthropic's Economic Index, Eloundou et al., and related sources) with fine-grained geographic workforce composition data (from the American Community Survey or other Census data) to produce county-level or commuting-zone-level estimates of AI exposure across the United States. Layer outcome data (employment, wages, job postings) and vulnerability indicators (education, income, demographics) on top to create a rich, interactive map that policymakers, researchers, and journalists can explore.

## Why This Matters

Existing work on AI's labor market impacts operates at national or occupation-level aggregates. Anthropic's own labor market impacts paper (March 2026) explicitly contains no geographic analysis — it's all US-aggregate. But the effects of AI on labor markets are inherently geographic: a county where 40% of the workforce does customer service work faces a very different AI future than one dominated by construction or healthcare. Making that variation visible is both novel and policy-relevant.

## Two Modes of Analysis

**Present-state analysis**: Using the latest data on actual AI adoption (Anthropic's "observed exposure" metric, which combines theoretical feasibility with real Claude usage data) to map where AI is currently impacting the workforce, cross-referenced with labor market outcomes.

**Forecasting / scenario analysis**: Using AI capability benchmarks and theoretical exposure scores to model what exposure *would* look like if AI systems reach specific capability thresholds. This could eventually incorporate a toggle: "If AI systems can do X (as measured by benchmark Y), then here's what exposure looks like in your county." This connects AI capabilities research (e.g., METR's software engineering benchmarks, SWE-bench, etc.) directly to labor market geography — making abstract capability improvements tangible for the workforce.

## Phased Approach

The project follows the Opportunity Atlas model: start with a base dataset and map, publish an initial tool and write-up, then progressively add layers and analyses as more data is collected and deeper statistical work is completed.

**Phase 1 — Base Map (Current Focus)**
Construct a synthetic AI exposure index at the county level by combining Anthropic's occupation-level exposure scores with ACS workforce composition data. Ship an interactive map and a short report describing the methodology and initial findings.

**Phase 2 — Outcome Overlays**
Layer labor market outcome data (employment trends, wage changes, job postings, unemployment) onto the base map. Begin cross-tabulating exposure with structural vulnerability indicators (education, income, demographics, industry concentration). Write a more substantial paper analyzing geographic variation in AI exposure and early outcome signals.

**Phase 3 — Forecasting & Causal Analysis**  
Introduce the capability-threshold toggle (scenario modeling). Pursue more rigorous econometric analysis — e.g., using Bartik/shift-share instruments to estimate causal effects of AI exposure on local labor markets. Incorporate additional data sources (Google Trends, freelancer platforms, unemployment claims) as leading indicators. Expand geographic scope (international, if data permits).

**Phase 4 -- Extension to ex-US Geographies**
To the extent feasible, repeat data collection and analyses for other countries (possibly at the sub-country level).


## Relationship to Existing Work

This project sits at the intersection of several research streams:

- **Anthropic's Economic Index** (2025-2026): Provides the occupation-level and task-level AI usage data that forms the foundation of our exposure measure. Their labor market impacts paper introduced the "observed exposure" metric we'll use. Their geographic report provides state-level adoption data we can validate against.
- **Eloundou et al. (2023)**: The theoretical LLM exposure scores (β = 0, 0.5, 1.0 per task) that Anthropic's observed exposure metric builds on.
- **Felten, Raj & Seamans (2023)**: AI occupational exposure index based on AI capabilities mapped to job abilities. A complementary measure — theirs is capability-based, ours incorporates actual usage.
- **Opportunity Atlas (Chetty et al., 2018)**: The methodological and presentation model. Census-tract-level causal estimates of intergenerational mobility, presented as an interactive map.
- **Autor, Dorn & Hanson (2013)**: "The China Shock" — the canonical example of using shift-share instruments to estimate the local labor market effects of a national-level economic disruption. Our approach to constructing geographic AI exposure is directly analogous.

## Deliverables

1. An interactive web-based map tool (the Atlas itself)
2. An initial report/paper describing the methodology and Phase 1 findings
3. Open-source code and data pipeline so others can reproduce and extend
4. Subsequent reports as new layers and analyses are added

---

*Status: Active — moving to implementation of Phase 1 base map.*