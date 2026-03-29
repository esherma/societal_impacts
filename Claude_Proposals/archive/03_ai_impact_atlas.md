# AI Impact Atlas: Brainstorming Overlays & Cross-Tabs

## The Opportunity Atlas Analogy

The Opportunity Atlas works at **census tract** level (~70,000 units, avg 4,250 people). Anthropic's Economic Index geographic data is at **US state** level (51 units). That's a big granularity gap — but it's a starting point, and the more interesting play is to *synthesize* finer-grained exposure estimates by combining Anthropic's occupation-level data with ACS workforce composition at the county or commuting zone level.

Two tiers of geographic resolution to think about:

- **Tier 1 (Direct)**: State-level, using Anthropic's actual geographic data. Simpler, faster, but coarse.
- **Tier 2 (Synthetic)**: County or commuting zone level, by combining Anthropic's occupation-level AI usage rates with ACS occupation mix data for each geography. More powerful, more assumptions.

---

## The Base Layer: AI Exposure

### Option A: Raw Claude Usage (State-Level)
Anthropic's geographic data gives per-capita Claude usage by state, plus task distributions. Direct measure of where AI adoption is actually happening. DC (3.82) and Utah (3.78) lead; southern/Plains states lag.

### Option B: Synthetic AI Exposure Index (County/CZ-Level)
Construct this by:
1. Taking the Economic Index's occupation-level task usage rates (what % of conversations involve each O*NET task)
2. Taking ACS data on occupation mix by county/commuting zone
3. Computing a weighted exposure score: for each geography, how much of the local workforce is in occupations where Claude is heavily used?

This is analogous to the Bartik/shift-share instrument in labor economics. The occupation-level usage rates are the "national shock," and the local occupation mix is the "exposure share."

### Option C: Augmentation vs. Automation Exposure
The Economic Index distinguishes augmentation from automation at the task level. You could construct *two* exposure indices — one for augmentation-heavy occupations, one for automation-heavy — and map where each concentrates. The policy implications differ: augmentation-heavy regions may see productivity gains; automation-heavy regions may see displacement.

---

## Overlay Ideas: What to Cross-Tab Against AI Exposure

### Tier 1: Labor Market Outcomes (The Obvious Ones)

**1. Employment Trends by AI-Exposed Occupation**
- Source: BLS OEWS (occupation × MSA, annual), QCEW (industry × county, quarterly)
- Question: Are AI-exposed occupations seeing employment declines in high-adoption states vs. low-adoption states?
- Visualization: Choropleth of employment change in top-10 AI-exposed occupations, side-by-side with Claude usage intensity

**2. Wage Trends**
- Source: BLS OEWS, ACS PUMS
- Question: Are wages compressing in AI-exposed occupations? Theory says augmentation → wage premium, automation → wage decline. Do we see this geographically?
- Visualization: Wage growth heat map for AI-exposed vs. non-exposed occupations by state/MSA

**3. Unemployment Rates by Occupation**
- Source: CPS microdata (monthly, occupation-coded)
- Question: Are unemployment rates rising faster in AI-exposed occupations, and where?
- Note: CPS sample is thin at state level for narrow occupations — may need to aggregate occupation groups

**4. Job Postings & Labor Demand**
- Source: Indeed Hiring Lab (free research data), BLS JOLTS
- Question: Are job postings declining in AI-exposed occupations? Rising for "AI oversight" roles?
- Indeed publishes sector-level trends; JOLTS is industry × national. Neither is great at occupation × geography, but directional.

### Tier 2: Structural Vulnerability Indicators

**5. Workforce Composition & Concentration Risk**
- Source: ACS 5-year estimates (county-level occupation mix)
- Question: Which counties/CZs have the highest share of workers in AI-automatable occupations? These are the "company town" equivalents — places where AI displacement would hit hardest because there's limited occupational diversity.
- Visualization: A "concentration risk" map showing geographic vulnerability, analogous to how researchers mapped coal or manufacturing dependence

**6. Educational Attainment & Retraining Capacity**
- Source: ACS (educational attainment by geography), IPEDS (proximity to community colleges/training programs)
- Question: Do AI-exposed regions have the educational infrastructure to absorb displaced workers?
- Cross-tab: AI exposure × distance to nearest community college × educational attainment → "adaptation readiness" score

**7. Broadband Access / Digital Infrastructure**
- Source: FCC Broadband Data Collection
- Question: Is there a digital divide in AI adoption? Do low-broadband areas have lower AI usage even when their occupation mix would predict high usage?
- This tests whether infrastructure is gating adoption, creating a different kind of inequality

**8. Industry Concentration (Herfindahl-style)**
- Source: QCEW, County Business Patterns
- Question: How diversified is the local economy? Regions with high AI exposure AND low industry diversity are most at risk.

### Tier 3: Socioeconomic Context (The "Who Gets Hurt" Layers)

**9. Income Distribution & Inequality**
- Source: ACS, IRS SOI (county-level income data)
- Question: Is AI adoption correlated with existing income inequality? The Economic Index found higher-income countries use Claude more for augmentation — does this hold within the US at state level?
- The Anthropic finding that higher-income populations augment more is key: if this holds geographically, AI could be *widening* geographic inequality.

**10. Racial/Ethnic Composition × AI Exposure**
- Source: ACS demographic data
- Question: Are communities of color disproportionately concentrated in automation-exposed (vs. augmentation-exposed) occupations? This is the equity question.
- Careful framing needed, but it's exactly the kind of analysis the Opportunity Atlas did.

**11. Age Distribution**
- Source: ACS
- Question: Are regions with older workforces (less likely to retrain) also the ones with high automation exposure? Or is there a natural buffer because older workers are in less AI-exposed roles?

**12. Poverty & Financial Fragility**
- Source: ACS, FDIC Survey of Household Economics (for financial resilience indicators)
- Question: Overlay AI exposure with existing poverty rates. Communities that are already economically fragile AND facing AI displacement are the policy priority.

### Tier 4: Leading Indicators & Sentiment (More Speculative)

**13. Google Trends Signals**
- Source: Google Trends (DMA-level)
- Searches: "AI replacing jobs," "learn to code," "career change," "prompt engineering course," "AI taking my job"
- Question: Do search trends for displacement anxiety correlate with local AI exposure? Do they lead actual labor market changes?

**14. Freelancer Platform Rate Compression**
- Source: Scraped or API-accessed Upwork/Fiverr data
- Question: Are freelance rates declining in AI-exposed categories (copywriting, graphic design, translation)? Geographic signal is limited (freelancers are everywhere) but occupation signal is strong.

**15. Housing Market / Migration Indicators**
- Source: Zillow, Redfin, ACS migration data
- Question: Are people moving away from AI-exposed labor markets? Housing price trends in tech-heavy MSAs vs. others.

---

## Most Promising Combinations for an MVP

For a first-pass interactive app, I'd recommend these layers:

### Base Map
- **Synthetic AI Exposure Index** (county or CZ level): ACS occupation mix × Economic Index task usage rates
- Split into **augmentation exposure** and **automation exposure** as separate toggles

### Core Overlays (all publicly available, relatively clean)
1. **Employment change** in AI-exposed occupations (BLS OEWS)
2. **Workforce concentration risk** — % of local workforce in top AI-exposed occupations (ACS)
3. **Educational attainment** — share with bachelor's or higher (ACS)
4. **Median household income** (ACS)
5. **Broadband access** (FCC)

### Stretch Overlays (messier data, higher payoff)
6. **Google Trends displacement anxiety** (DMA-level)
7. **Racial composition × exposure** (ACS)
8. **CDC PLACES mental distress** estimates (census-tract level)

---

## Geographic Unit Decision

| Unit | Pros | Cons |
|------|------|------|
| State | Directly maps to Anthropic data | Too coarse for policy; 51 units |
| Commuting Zone | Natural labor market boundaries; ~740 units | Less familiar to policymakers; ACS data sometimes thin |
| County | ~3,100 units; familiar; good ACS coverage | Doesn't respect labor market boundaries |
| Census Tract | Opportunity Atlas level; most granular | Overkill for occupation-level analysis; noisy |

**Recommendation**: Start at **county level** for the base map (familiar, good data coverage), with an option to aggregate to commuting zones for the labor economics audience. State-level panel for direct Anthropic data comparisons.

---

## The Pitch

"The Opportunity Atlas showed that where you grow up shapes your economic future. The AI Impact Atlas shows that where you *work* shapes how AI is reshaping your economic present — and not everyone is equally prepared."

---

## Technical Notes for the App

- **Stack**: Could be a React app with Mapbox/Leaflet, or a simpler Observable/D3 notebook to prototype fast
- **Data pipeline**: Python scripts to pull ACS (via Census API), BLS (via BLS API), merge with Economic Index data, output GeoJSON
- **Hosting**: GitHub Pages for static, or a simple Streamlit/Gradio app for interactive filtering
- **Scope for Claude Code phase**: This is where the analysis work would shift — pulling data, computing exposure indices, building the visualization

---

*Status: Brainstorm — needs Eli's input on which overlays are most interesting and what geographic resolution to target first.*
