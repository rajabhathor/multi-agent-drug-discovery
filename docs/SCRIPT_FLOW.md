# Multi-Agentic AI Script Flow Documentation

This document explains the end-to-end execution flow of the Streamlit app in [app.py](app.py), including how data is loaded, how multi-agent steps are represented, how target scores are computed, and how each UI tab is rendered.

## 1) High-level purpose

The script builds an interactive, offline-friendly demonstration of a governed multi-agent drug-discovery workflow. It is designed to show:

- Agent specialization and orchestration
- Transparent scoring policy controls
- Contradiction-aware ranking
- Sensitivity testing across policy presets
- Governance and human-approval boundaries

## 2) Startup and configuration flow

### 2.1 Imports and constants

At startup, the script imports data, graphing, plotting, and UI libraries, then defines:

- Base path and data file path
- Default evidence weights
- Policy presets (Balanced, Safety-first, Novelty-first)
- The ordered list of agents and responsibilities

Relevant sections:

- [Weights and presets](app.py#L14)
- [Agent list](app.py#L46)

### 2.2 App metadata and initial load

The app config is set via Streamlit page config, then source data is loaded from [data/ipf_evidence.json](data/ipf_evidence.json).

Relevant sections:

- [Page config and data load](app.py#L224)

## 3) Data model used by the app

The JSON payload in [data/ipf_evidence.json](data/ipf_evidence.json) provides:

- Disease metadata
- A list of candidate targets
- Per-target evidence dimensions:
  - genetics
  - mechanism
  - omics
  - tractability
  - clinical
  - safety
  - differentiation
- Supporting evidence statements
- Contradictions/evidence gaps
- Intervention landscape entries
- Suggested validation experiments
- Citation links

The app never calls external APIs at runtime in this demo; it works from this curated local dataset.

## 4) Core scoring and policy logic

### 4.1 Weight normalization

Function: [normalize_weights](app.py#L64)

Purpose:

- Ensures policy weights sum to 1.0 before scoring
- Prevents malformed presets from distorting final values
- Falls back to default weights if total weight is invalid

### 4.2 Target scoring

Function: [score_target](app.py#L71)

Computation:

$$
\text{base\_score} = \sum_i (e_i \cdot w_i)
$$

Where:

- \(e_i\) is target evidence for dimension \(i\)
- \(w_i\) is policy weight for dimension \(i\)

Contradiction adjustment:

$$
\text{penalty} = \min(\text{num\_contradictions} \cdot \text{contradiction\_penalty}, 0.25)
$$

Final score:

$$
\text{final\_score} = 100 \times \max(\text{base\_score} - \text{penalty}, 0)
$$

This does two things for the demo:

- Keeps ranking policy-transparent
- Shows explicit risk from unresolved contradictory evidence

### 4.3 Score table construction

Function: [build_scores](app.py#L78)

Purpose:

- Builds a DataFrame containing:
  - Target
  - Overall Score
  - Evidence gaps count
  - Dimension-level percentages
- Sorts descending by overall score for ranking display

### 4.4 Sensitivity matrix

Function: [sensitivity_matrix](app.py#L91)

Purpose:

- Re-runs ranking under each policy preset
- Produces policy-vs-rank table used in Stress testing tab
- Makes policy dependence visible for client discussions

## 5) Multi-agent representation

### 5.1 Agent roster

The list in [AGENTS](app.py#L46) defines the staged workflow shown during execution.

Execution order:

1. Intake Agent
2. Supervisor Agent
3. Genetics Agent
4. Literature Agent
5. Pathway Agent
6. Compound Agent
7. Safety Agent
8. Critic Agent
9. Synthesis Agent

### 5.2 Decision trace

Function: [decision_trace](app.py#L108)

Purpose:

- Generates a bounded, inspectable action log
- Uses top target in critic message for contextual traceability
- Ends with Human review required status for synthesis stage

### 5.3 Agent contract table

Function: [agent_contracts](app.py#L122)

Purpose:

- Documents role, inputs, outputs, and primary guardrail per agent
- Supports governance and operating-model narrative

## 6) Graph visualization flow

Function: [render_graph](app.py#L191)

Flow:

1. Build directed graph scaffold around IPF mechanism nodes
2. Attach top-ranked targets to mechanism branches
3. Compute spring-layout positions
4. Build Plotly traces for edges and nodes
5. Render in Streamlit chart area

This is a semantic illustration for demo storytelling, not a complete production knowledge graph implementation.

## 7) UI and interaction flow

## 7.1 Sidebar controls

Sidebar in [mission control block](app.py#L234) gathers:

- Disease
- Audience mode
- Preferred modality
- Scoring policy preset
- Evidence depth
- Contradiction penalty slider
- Human approval toggle
- Run button

These controls define the run context and scoring behavior.

### 7.2 Scientific question input

The text area captures the natural-language problem statement in [question input](app.py#L246).

### 7.3 Session state lifecycle

Session state keys initialized in [state init](app.py#L252):

- ran: whether a run has occurred
- last_run: captures selected control values for the latest run

When Run is clicked in [run block](app.py#L258):

1. State is marked as ran
2. Current control values are persisted
3. Status panel streams through each agent stage
4. Pipeline status is finalized as complete

## 8) Post-run rendering flow (tab-by-tab)

After run, active weights and scores are computed in [post-run block](app.py#L275), then six tabs are rendered.

### 8.1 Mission snapshot tab

Section: [Mission snapshot](app.py#L290)

Shows:

- Top hypothesis
- Top score
- Current policy
- Contradiction penalty setting
- Approval boundary status

Audience mode changes narrative bullets for:

- Executive
- Scientist
- Governance

### 8.2 Ranked hypotheses tab

Section: [Ranked hypotheses](app.py#L315)

For each ranked target:

- Supporting evidence
- Contradictions/evidence gaps
- Recommended validation experiments
- Intervention landscape
- Citation provenance

Also includes a transparent scoring table.

### 8.3 Agent orchestration tab

Section: [Agent orchestration](app.py#L344)

Shows:

- Agent contracts table
- Execution trace table
- Note about observable trace vs private reasoning

### 8.4 Stress testing tab

Section: [Stress testing](app.py#L352)

Shows:

- Current policy bar chart
- Sensitivity pivot table across presets
- Active scoring policy string

This tab is the primary explanation aid for policy-driven prioritization.

### 8.5 Evidence graph tab

Section: [Evidence graph](app.py#L372)

Renders semantic graph for top-ranked targets.

### 8.6 Governance tab

Section: [Governance tab](app.py#L377)

Shows:

- Runtime governance KPIs
- Governance control table
- Evaluation scorecard
- Reference architecture diagram text
- Design-principles summary

## 9) Pre-run fallback flow

If no run has occurred, the app uses the fallback block in [default state](app.py#L425):

- Prompts user to execute the investigation
- Shows four capability cards:
  - Specialized agents
  - Reasoning over evidence
  - Policy-aware ranking
  - Governed decisions

## 10) Demo talking points mapped to code

Use this mapping during demos:

1. Policy is explicit, not hidden
   - [Weights and presets](app.py#L14)
   - [Active policy selection](app.py#L239)

2. Contradictions reduce confidence
   - [Contradiction penalty control](app.py#L241)
   - [Penalty application](app.py#L71)

3. Multi-agent process is inspectable
   - [Agent contracts](app.py#L122)
   - [Decision trace](app.py#L108)

4. Strategy sensitivity is measurable
   - [Sensitivity computation](app.py#L91)
   - [Sensitivity display](app.py#L364)

5. Human remains accountable
   - [Run-time approval toggle](app.py#L242)
   - [Governance controls](app.py#L382)

## 11) Extension points

Practical next enhancements:

1. Replace static JSON with governed retrieval adapters while preserving same scoring interfaces
2. Add uncertainty intervals per evidence dimension
3. Version policy presets and log run-time policy IDs
4. Add per-agent latency and token/cost observability rows
5. Export run package (rankings, citations, trace, policy settings) as shareable artifact

## 12) Operational notes

- The script is designed for deterministic demo behavior using local curated data.
- Scores are illustrative; this is a hypothesis prioritization aid, not a decision automation system.
- Scientific, medical, and portfolio decisions remain outside the autonomous boundary.