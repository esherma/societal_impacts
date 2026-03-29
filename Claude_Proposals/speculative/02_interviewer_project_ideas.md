# Satellite Project Ideas: AnthropicInterviewer Data

## Dataset Summary

- **N = 1,250** professionals interviewed by Claude about how they use and feel about AI at work
- Three cohorts: General Workforce (1,000), Creatives (125), Scientists (125)
- 10-15 minute adaptive conversations; full transcripts publicly released
- Demographics skew: education (17%), computer/math (16%), arts/design/media (14%)
- Key headline findings: 86% say AI saves time, 69% mention stigma, 55% express anxiety about AI's future impact, 48% envision transitioning to AI oversight roles

## The Stated vs. Revealed Gap

The most striking finding in the original report is buried in the methodology: participants self-reported 65% augmentation / 35% automation, but their *actual Claude usage* showed 47% augmentation / 49% automation. People think they're collaborating with AI more than they actually are.

This is the thread most worth pulling on, because it connects directly to the Clio proposal — self-report data systematically misrepresents what's actually happening, which is exactly the argument for observational (Clio-based) research.

---

## Project Ideas

### 1. Taxonomy of AI Displacement Anxiety (Most Promising)

**Question**: What are the distinct forms of AI-related career anxiety expressed by workers, and how do they vary by occupation, AI usage intensity, and career stage?

**Approach**:
- Code the 1,250 transcripts for displacement-related language (fear of replacement, skill obsolescence, career pivoting, competitive pressure to adopt AI)
- Build a taxonomy: speculative anxiety vs. concrete displacement experience vs. competitive anxiety ("if I don't use it, someone else will") vs. identity threat ("AI can do what I thought made me special")
- Map taxonomy onto occupation, self-reported AI usage, and cohort (general/creative/scientist)
- Use Claude itself as a coding tool (meta!) — develop a classification prompt, validate against human-coded subsample

**Why it matters**:
- 55% expressed anxiety, but "anxiety" is not monolithic. The policy implications differ enormously depending on whether workers fear *replacement* vs. *deskilling* vs. *competitive pressure*
- Directly motivates the Clio project: "Here's the taxonomy from 1,250 interviews — now imagine tracking these signals across millions of conversations in real time"

**Feasibility**: High. The data is public. The analysis is qualitative/NLP coding, well within your skillset.

---

### 2. The AI Oversight Aspiration: Who Wants to "Manage the Robots"?

**Question**: 48% of workers envision transitioning to AI oversight roles. What predicts this aspiration, and how realistic is it?

**Approach**:
- Identify the "oversight aspiration" conversations in transcripts
- Characterize: What do people think "AI oversight" means? Is it specific or vague? Do they have a plan?
- Cross-reference with occupation: Are the people who want to "oversee AI" the ones whose current work is most automatable?
- Compare against O*NET task data to assess whether their envisioned oversight roles actually exist or are emerging

**Why it matters**:
- If half the workforce's adaptation strategy is "I'll supervise the AI," that has massive implications for workforce development, education, and whether the transition will be smooth or brutal
- Could be a cautionary finding: many of these "oversight roles" may not exist at scale

**Feasibility**: High. Transcripts + O*NET data are both public.

---

### 3. Stigma, Secrecy, and the Hidden AI Workforce

**Question**: 69% report stigma around AI use at work. What are the sources and consequences of this stigma?

**Approach**:
- Analyze stigma-related passages: Who are workers hiding AI use from (managers, peers, clients)?
- Categorize stigma types: professional integrity ("it's cheating"), competitive secrecy ("don't want others to know my edge"), quality concern ("people won't trust my work"), identity ("I should be able to do this myself")
- Look for the paradox: workers who simultaneously report high AI value AND high stigma — what's their coping strategy?

**Why it matters**:
- If a large fraction of the workforce is secretly using AI, official adoption statistics undercount real usage, and organizational AI policies are being built on bad data
- Connects to Clio: conversational data captures what people *actually do* with AI, bypassing the stigma filter entirely

**Feasibility**: High. Same transcript analysis.

---

### 4. The Stated/Revealed Augmentation Gap — Deep Dive

**Question**: Why do people think they're augmenting when they're actually automating? What does this tell us about how workers understand their own AI use?

**Approach**:
- This is harder to do with just the interview transcripts — the augmentation/automation behavioral data was from the original study's Clio analysis
- But you could: analyze how people *describe* their AI use in interviews and code it independently for augmentation vs. automation, then compare to the aggregate finding
- Look for linguistic markers: do people who say "I use AI as a brainstorming partner" actually describe workflows that are more like "I have AI write the first draft and I edit"?

**Why it matters**:
- This is arguably the single most important finding for labor economics: workers systematically misperceive the nature of their AI use
- If people think they're augmenting but are actually automating, they may not be developing the skills they'll need when the automation gets better
- Strong motivation for Clio-based observation over self-report

**Feasibility**: Medium. The transcript analysis is doable but the ground truth (actual behavioral data) isn't in the public dataset. Would need to frame as "here's what self-reports suggest, and here's why we need observational data to validate."

---

### 5. Creative Workers: The Emotional Cost of Productivity Gains

**Question**: Creative workers report the highest productivity gains (97% time savings) AND the most emotional conflict. How do these coexist?

**Approach**:
- Deep qualitative analysis of the 125 creative worker transcripts
- Map the emotional landscape: productivity satisfaction, identity threat, market anxiety, peer judgment
- Look for "reconciliation strategies" — how do creatives resolve the tension between "this makes me faster" and "this threatens what I am"?
- Compare writers (48% of creatives) vs. visual artists (21%) — the threat model may differ

**Why it matters**:
- Creative work is the canary in the coal mine for knowledge work displacement broadly
- The emotional dynamics here preview what will happen in other professions as AI capability improves
- Could connect to "Values in the Wild" research — what values are in tension when people use AI for creative work?

**Feasibility**: High. N=125 is small enough for careful qualitative work but large enough for patterns.

---

## Recommended Priority

**Start with Project 1 (Taxonomy of Displacement Anxiety).** It's the most direct bridge to the Clio proposal, it's feasible with public data, and it produces a concrete artifact (the taxonomy) that has standalone value for the field. It also demonstrates exactly the kind of work the Societal Impacts team does — using conversational data to surface patterns about how AI is affecting people.

Project 4 (Stated/Revealed Gap) is the most intellectually interesting but hardest to execute without the behavioral data. Could frame as a methods paper arguing for observational approaches.

---

## Bridge to the Clio Proposal

Every one of these projects ends with the same punchline: *self-report data from 1,250 people gives us a sketch, but observational data from millions of conversations would give us the full picture.* That's the pitch — do the feasible work now with public data, use it to argue for the Clio-based surveillance project.

---

*Status: Brainstorm draft — needs Eli's input on which directions are most interesting.*
