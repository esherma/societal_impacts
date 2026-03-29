# AI Displacement Surveillance via Conversational Data

## The Core Idea

Use Anthropic's Clio (or analogous conversation-analysis infrastructure) to build a real-time economic sensor that detects AI-driven job displacement as it propagates across the economy — before it shows up in traditional labor statistics.

The key signal: **conversations where users are searching for jobs and attribute their search to AI-related fears or actual displacement.** These conversations are happening now, likely concentrated in software and adjacent tech roles, but the hypothesis is that this wave will broaden across sectors over time.

## Why This Matters

Traditional economic indicators of displacement — unemployment claims, BLS surveys, earnings reports — are lagging. Moreover, there's a lot of noise in layoff announcements, where companies may attribute layoffs to AI as a signal to investors rather than due to explicit automation achievements.

By the time these classical indicators register a shift, workers have already been affected for months. 



Conversational data from AI assistants may offer something qualitatively different:

- **Leading indicator**: People process anxiety about displacement and begin job searching before formal layoffs or role eliminations occur.
- **Rich context**: Unlike a binary "employed/unemployed" signal, conversations reveal *why* someone is searching, what role they're leaving, what they fear, and what they're looking for.
- **Continuous and organic**: No survey design, no response bias — people are telling an AI assistant what's actually happening in their work lives.

## What You'd Measure

### Primary Signal

Conversations where users are job searching AND the conversation contains evidence that AI is a causal or motivating factor. This could include:

- Explicit statements: "My company replaced my team with AI," "I'm worried AI will make my role obsolete"
- Implicit signals: Job searching in a field known to be AI-disrupted, combined with anxiety language
- Temporal patterns: Upticks in job-search conversations from specific industries or roles

### Dimensions of Interest

- **Occupation/role**: Which jobs are people leaving or fearing they'll lose?
- **Industry/sector**: Where is displacement concentrated, and how is it spreading?
- **Geography**: Are there regional patterns (e.g., tech hubs first)?
- **Displacement stage**: Fear vs. active displacement vs. already displaced
- **Trajectory**: What are displaced workers seeking? Same field? Career change? Retraining?

### The "Wave" Visualization

The aspirational output is a time-series visualization showing AI displacement spreading across occupational categories — starting with software/tech, moving into content/creative, customer service, administrative roles, and beyond. Think of it as a heat map of economic disruption rolling across the labor market in near-real-time.

## Data Requirements & Challenges

### The Hard Part

This project fundamentally depends on access to aggregated, privacy-preserving conversation data at scale. Key challenges:

1. **Access**: Clio is an internal Anthropic tool. This project would likely need to be done *at* Anthropic or in close partnership with them.
2. **Privacy**: Even with Clio's privacy-preserving design, analyzing conversations about sensitive personal situations (job loss, financial anxiety) raises ethical questions that need careful handling.
3. **Classification**: Building a reliable classifier for "AI-displacement-motivated job search" conversations is non-trivial. Need to distinguish:
  - Genuine displacement from general job dissatisfaction
  - AI-specific fears from broader economic anxiety
  - Actual displacement from speculative anxiety
4. **Representativeness**: Claude users are not a random sample of the labor force. They skew tech-literate, younger, and toward knowledge work. The sensor would have strong signal in some sectors and blind spots in others.
5. **Base rates**: Need to establish what "normal" job-search conversation volume looks like to detect meaningful changes.

### What Clio Specifically Offers

*(Based on public descriptions of the tool)*

- Aggregate, anonymized analysis of conversation topics and patterns
- Ability to identify clusters of similar conversations
- Temporal tracking of topic prevalence
- Privacy-preserving by design — no individual conversation access needed

## Potential Study Design

### Phase 1: Feasibility & Baseline

- Establish baseline rates of job-search-related conversations
- Develop taxonomy of AI-displacement signals in conversation data
- Assess whether Clio's granularity is sufficient to distinguish displacement-motivated searches from general job searching

### Phase 2: Cross-Sectional Snapshot

- Map current distribution of AI-displacement conversations by inferred occupation/industry
- Compare to external data on AI adoption rates by sector
- Identify leading-edge sectors where displacement signal is strongest

### Phase 3: Longitudinal Surveillance

- Track changes over time in displacement signal by sector
- Correlate with external labor market indicators (job postings, layoff announcements, BLS data)
- Validate: does the conversational signal lead traditional indicators?

### Phase 4: The Wave

- Build the time-series visualization of displacement propagation
- Develop an "AI displacement index" that could serve as an early warning system
- Publish findings and methodology

## Open Questions

- Could this work with data from other AI assistants (ChatGPT, etc.) or is it Anthropic-specific?
- What's the right unit of analysis — individual conversations, users over time, topic clusters?
- How do you handle the fact that the *population of AI users* is itself changing rapidly? The denominator is moving.
- Is there an IRB / ethics review pathway for this kind of research at Anthropic?
- Could a version of this be done with publicly available data (e.g., Reddit posts about AI displacement) as a proof of concept?

## Relationship to Existing Work

- **Clio papers**: [Anthropic's published work on Clio methodology]
- **AI exposure indices**: Felten et al., Eloundou et al. — these measure *potential* exposure; this project would measure *realized* impact
- **Labor market surveillance**: Google Trends for unemployment, Indeed Hiring Lab — similar philosophy of using digital exhaust as economic indicators
- **Displacement literature**: Acemoglu, Autor, etc. on automation and labor markets

## Alignment with Societal Impacts Team Priorities

This project maps directly onto several responsibilities listed for the Research Scientist, Societal Impacts role:

- **"Using observational tools like Clio to analyze real-world usage patterns and surface insights"** — this is literally a Clio project, proposing a novel use of the tool beyond current Economic Index work.
- **"Generating insights about the societal impact of Anthropic's systems and using this understanding to inform company strategy, research priorities, and policy positions"** — an AI displacement early warning system has obvious policy implications and could inform how Anthropic positions itself on labor market questions.
- **"Sharing your work through research publications and external presentations, and developing tools and frameworks that make AI systems more understandable to policymakers, academics, and civil society"** — this would be of enormous interest to policymakers, labor economists, and the public.

### How It Extends Existing Work

The Economic Index currently maps *what tasks* Claude is used for (via O*NET classification) and measures augmentation vs. automation. This project would add a fundamentally different signal: not how AI is being used as a tool, but how AI's existence is reshaping people's *careers and anxieties*. It's the demand-side complement to the supply-side analysis the team already does.

The AnthropicInterviewer study (N=1,250) captures self-reported attitudes about AI and work through structured interviews. This project would capture *revealed* behavior — people who are actually job searching, not just responding to survey questions about hypothetical futures.

### Candidate Background Fit

- Published work on using consumer platform data for population-level surveillance (Sherman & Shatte, 2021, CLPsych @ NAACL) — same core methodology of extracting societal signals from user-generated text on a tech platform, applied to mental health surveillance via Reddit.
- Experience at an AI governance SaaS company (responsible AI focus) — direct exposure to how organizations are grappling with AI adoption, risk, and workforce implications.
- Technical ML/data science skills for building classifiers, working with large-scale text data, and producing rigorous empirical analysis.

---

*Status: Initial sketch — needs discussion on feasibility, data access pathway, and scoping.*