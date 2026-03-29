# Phase 2+: Future Overlays, Cross-Tabs, and Statistical Analyses

This document catalogs the analyses we plan to layer onto the base AI exposure map after Phase 1 is up and running. These are organized roughly by data accessibility and analytical complexity — from "straightforward overlay with public data" to "requires serious econometric work and possibly proprietary data."

The point of building the base map first is that it gives us a scaffold to hang all of this on, plus the process of constructing it will teach us things about the data (occupational detail, geographic coverage, edge cases) that will inform how we approach these extensions.

---

## Category 1: Labor Market Outcome Overlays

These answer the question: "Is AI exposure actually showing up in labor market outcomes, and where?"

### 1.1 Employment Trends by AI-Exposed Occupation
- **Source**: BLS Occupational Employment and Wage Statistics (OEWS), annual, occupation × MSA
- **Approach**: For each geographic unit, compute employment change in AI-exposed occupations (top quartile of exposure) vs. non-exposed occupations. Visualize as a differential: "how much faster/slower is employment growing in exposed vs. unexposed jobs in this county?"
- **Data notes**: OEWS is MSA-level, not county. Will need to assign counties to MSAs or aggregate counties to MSA-equivalent units. Non-metro counties will have limited OEWS coverage.

### 1.2 Wage Trends in Exposed Occupations
- **Source**: BLS OEWS (wages by occupation × MSA), ACS PUMS (individual-level wages with occupation codes)
- **Approach**: Are wages compressing or rising in AI-exposed occupations? Theory predicts augmentation → wage premium (AI makes workers more productive) and automation → wage decline (AI substitutes for workers). Test this geographically.
- **Cross-tab**: Compare wage trends in high-augmentation-exposure vs. high-automation-exposure geographies (requires Option C split from base layer doc).

### 1.3 Unemployment by Occupation
- **Source**: Current Population Survey (CPS) microdata, monthly, publicly available via IPUMS
- **Approach**: Occupation-coded unemployment rates over time. Anthropic's labor market paper already did this at the national level and found no systematic increase in unemployment for exposed workers. The geographic question is: does that hold everywhere, or are there local pockets where exposed workers ARE seeing unemployment?
- **Challenge**: CPS samples are thin at the state level for narrow occupations. May need to aggregate to occupation groups and multi-year windows.

### 1.4 Young Worker Entry Rates
- **Source**: CPS microdata (age × occupation × employment status)
- **Approach**: Anthropic found a 14% drop in job-finding rates for 22-25 year olds in exposed occupations. Can we detect geographic variation in this? Are young workers in tech-heavy metros being hit harder?
- **Why it matters**: If AI is closing the entry door for young workers in specific places, those places face a structural workforce aging problem that won't show up in headline unemployment numbers.

### 1.5 Job Postings & Labor Demand Signals
- **Source**: Indeed Hiring Lab (free research data releases), LinkedIn Economic Graph (selected public releases), BLS JOLTS (industry × national)
- **Approach**: Are job postings declining in AI-exposed occupations? Rising for "AI oversight" or "AI-augmented" roles? Indeed publishes sector-level posting trends. LinkedIn has released some occupation-level data for research.
- **Limitation**: Neither source gives occupation × geography at fine resolution in public data. May need to work with summary/sector-level trends or request research access.

---

## Category 2: Structural Vulnerability Indicators

These answer: "Which communities are most vulnerable IF displacement materializes?"

### 2.1 Workforce Concentration Risk
- **Source**: ACS 5-year estimates (occupation counts by county)
- **Approach**: Herfindahl-style index of occupational concentration. Counties where a large share of the workforce is in a small number of AI-exposed occupations are analogous to "company towns" — they lack the occupational diversity to absorb displacement.
- **Visualization**: Overlay concentration risk with exposure level. High exposure + high concentration = highest risk.

### 2.2 Educational Attainment & Retraining Capacity
- **Source**: ACS (educational attainment by geography), IPEDS (college/training institution locations)
- **Approach**: Do AI-exposed counties have the educational infrastructure to support workforce transitions? Compute: (a) share of population with bachelor's+ degree, (b) proximity to community colleges and vocational training programs, (c) presence of CS/data science programs specifically.
- **Cross-tab**: Exposure × education → "adaptation readiness" score. High exposure + high education = likely to adapt; high exposure + low education = policy priority.

### 2.3 Industry Diversification
- **Source**: QCEW, County Business Patterns
- **Approach**: Beyond occupational concentration, how diversified is the local *industry* base? A county with high AI exposure but diverse industries might absorb displaced workers into other sectors. One dependent on a single AI-exposed industry (e.g., call center towns) cannot.

### 2.4 Broadband Access / Digital Infrastructure
- **Source**: FCC Broadband Data Collection
- **Approach**: Is there a digital divide in AI adoption potential? Counties with high theoretical exposure but low broadband access face a double bind: they're exposed to displacement from AI used *elsewhere* but can't leverage AI for local productivity gains.
- **This is also a validation test**: Does our synthetic exposure index (which assumes national adoption rates apply locally) overestimate exposure in low-connectivity areas?

---

## Category 3: Socioeconomic Context ("Who Gets Hurt")

These layer equity and distributional questions onto the exposure map.

### 3.1 Income Distribution
- **Source**: ACS, IRS Statistics of Income (county-level income data)
- **Approach**: The Anthropic Economic Index found that higher-income populations are more likely to use AI for augmentation (productivity-enhancing) while lower-income populations see more automation. If this pattern holds geographically within the US, AI could be widening spatial inequality — affluent metros benefit, poorer areas face displacement.
- **Analysis**: Correlate county-level exposure (and aug/auto split) with median household income, Gini coefficient, income quintile shares.

### 3.2 Racial & Ethnic Composition
- **Source**: ACS demographic data
- **Approach**: Are communities of color disproportionately in automation-exposed (vs. augmentation-exposed) geographies? Anthropic's own labor market paper notes that exposed workers are 16pp more likely female and 11pp more likely white — but that's at the occupation level nationally. The geographic distribution may look different.
- **Note**: Careful framing is essential. The Opportunity Atlas handled this thoughtfully — presenting racial breakdowns as a factual input to equity-focused policy, not as deterministic claims.

### 3.3 Age Distribution & Retirement Proximity
- **Source**: ACS
- **Approach**: Counties with older workforces in AI-exposed occupations face a different challenge than those with younger workers. Older workers are less likely to retrain but also closer to retirement — the displacement impact may be more acute but shorter-duration. Young workers face longer-term career disruption.

### 3.4 Poverty & Financial Fragility
- **Source**: ACS (poverty rates), FDIC Survey of Household Economics, Federal Reserve Household Debt and Credit Report (state-level)
- **Approach**: Communities that are already economically fragile AND face high AI exposure are the highest policy priority. Overlay poverty rates, food insecurity indicators, and consumer debt levels with exposure.

---

## Category 4: Leading Indicators & Sentiment

These are more speculative and data-messy, but potentially the most forward-looking.

### 4.1 Google Trends Displacement Anxiety
- **Source**: Google Trends (DMA-level, ~210 geographic units)
- **Searches**: "AI replacing jobs," "AI taking my job," "learn prompt engineering," "career change AI," "will AI replace [occupation]"
- **Approach**: Do search trends for displacement-related queries correlate with our AI exposure index? Do they *lead* actual labor market changes?
- **Precedent**: Google Trends was used effectively during COVID to nowcast unemployment before official statistics caught up. Same logic applies here.

### 4.2 Freelancer Rate Compression
- **Source**: Upwork/Fiverr (scraped or API-accessed rate data by category)
- **Approach**: Freelance categories directly hit by generative AI (copywriting, graphic design, translation, basic coding) should show rate compression if AI is substituting for human labor. Geographic signal is weak (freelancers work remotely), but *occupational* signal is strong and complements the geographic analysis.
- **Data access**: Some scraping possible; Upwork has released limited summary data. Would need to build a collection pipeline.

### 4.3 Reddit / Social Media Sentiment
- **Source**: Reddit (r/cscareerquestions, r/webdev, r/graphic_design, r/writing, r/freelance, etc.)
- **Approach**: These subreddits have large corpora of workers in AI-exposed occupations discussing displacement fears, career pivots, and wage competition. Sentiment analysis over time by subreddit (as a proxy for occupation) would complement the atlas.
- **Connection to prior work**: Eli's CLPsych paper (Sherman & Shatte 2021) used Reddit data for population-level mental health surveillance — same methodology, different outcome variable.

### 4.4 Housing & Migration
- **Source**: Zillow/Redfin (housing prices by zip code), ACS migration data (county-to-county flows)
- **Approach**: If AI displacement hits specific labor markets hard enough, you'd eventually see out-migration and housing price effects. Very lagged, but would be a powerful "hard outcome" confirmation of earlier signals.

---

## Category 5: Statistical & Econometric Analyses

These go beyond visualization to rigorous causal or predictive modeling.

### 5.1 Shift-Share Instrument for Causal Effects
- **Design**: Use the Bartik-style construction from the base map as an *instrument* rather than just a descriptive index. The logic: local AI exposure (determined by pre-existing occupation mix × national AI adoption patterns) is plausibly exogenous to local labor market shocks, so we can use it to estimate the *causal* effect of AI exposure on local employment, wages, etc.
- **Outcome variables**: Employment growth, wage growth, unemployment rate changes, young worker entry rates
- **Precedent**: Directly follows Autor, Dorn & Hanson (2013) on the China Shock. Well-understood methodology with known strengths and limitations.
- **Caveat**: The standard Bartik critique applies — if AI adoption correlates with unobservable local characteristics (e.g., local tech culture, venture capital density), the instrument may not be as exogenous as assumed.

### 5.2 Difference-in-Differences: Pre/Post ChatGPT
- **Design**: Compare labor market outcomes in high-exposure vs. low-exposure counties before and after November 2022 (ChatGPT launch) or some other natural breakpoint.
- **Parallel trends assumption**: Pre-2022 trends in employment/wages should be similar across exposure groups. If they diverge after 2022, that's evidence of AI impact.
- **Anthropic's paper did a version of this nationally** (unemployment trends pre/post ChatGPT for exposed vs. unexposed occupations). Doing it *geographically* is the novel contribution.

### 5.3 Predictive Modeling of Displacement Risk
- **Design**: Combine exposure index, structural vulnerability indicators, and early outcome data into a composite "displacement risk score" for each county. This is less causally rigorous but potentially more useful for policymakers who want to target interventions.
- **Method**: Could range from simple weighted index to gradient-boosted model trained on early-mover counties to predict which others will follow.

### 5.4 Validation Against Anthropic's State-Level Data
- **Design**: Aggregate our synthetic county-level exposure estimates to the state level and compare against Anthropic's direct state-level Claude usage measures.
- **Purpose**: This is a necessary sanity check. If our synthetic estimates don't correlate with actual observed AI usage patterns, something is wrong with the construction. If they do correlate but imperfectly, the residuals are interesting — they tell you where AI adoption is higher or lower *than predicted by occupation mix alone*, pointing to other factors (culture, infrastructure, policy).

---

## Prioritization

After the base map is live, the suggested order of attack is:

1. **Category 2 overlays (vulnerability indicators)** — mostly ACS data we'll already have from building the base map. Low marginal effort, high policy value.
2. **Validation (5.4)** — needed to establish credibility before any serious publication.
3. **Option C augmentation/automation split** — the most impactful extension to the base exposure layer.
4. **Category 1 labor market outcomes** — requires pulling new data (OEWS, CPS) but well-understood methodology.
5. **Category 3 equity overlays** — important for policy audience; mostly ACS data.
6. **Category 5 econometric work** — this is where the paper-worthy contributions are, but it requires all the above to be in place first.
7. **Category 4 leading indicators** — most novel but also most speculative and data-intensive.

---

*Status: Brainstorm catalog — to be revisited after Phase 1 base map is complete.*
