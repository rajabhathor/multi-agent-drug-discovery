# Multi-Agent AI Drug Discovery Demo

A stable, offline-friendly Streamlit pilot demonstrating governed multi-agent target discovery, policy-aware ranking, and scientist-facing hypothesis prioritization.

## What it demonstrates

- Supervisor and specialist-agent architecture
- Retrieval-Augmented Reasoning pattern
- Semantic evidence graph
- Transparent target scoring with configurable policy weights
- Ranking stress testing across policy presets
- Contradiction and evidence-gap handling
- Literature Agent retrieval from PubMed Central records (demo cache or live Europe PMC)
- Runtime governance and human approval
- Agent, retrieval, scientific, and operational evaluation

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Demo mode

The app uses curated, illustrative public-data summaries for IPF. It avoids live API dependencies so the Monday demonstration remains stable. All scores are illustrative and are not scientific or medical recommendations.

## Key controls for live demo

- `Audience mode` toggles between Executive, Scientist, and Governance narratives.
- `Scoring policy` switches between Balanced, Safety-first, and Novelty-first weight presets.
- `Literature source` switches between stable demo cache and live Europe PMC retrieval.
- `Literature records per target` sets the retrieval depth shown per hypothesis.
- `Contradiction penalty` stress-tests how unresolved evidence gaps impact ranking confidence.
- `Require human approval` keeps the recommendation boundary explicit.

## Suggested 12-minute flow

1. Frame the problem and decision boundary.
2. Run the multi-agent investigation.
3. Show the `Mission snapshot` and audience-specific explanation.
4. Show ranked hypotheses for the top target, including contradictions and validation experiments.
5. Open `Agent orchestration` to walk the contract table and execution trace.
6. Open `Stress testing` and switch policy presets to show ranking sensitivity.
7. Show the semantic `Evidence graph`.
8. Finish with `Governance` and the human-review gate.

## Architecture message

> The system uses bounded agency: agents investigate, compare, and recommend, while deterministic policies control access, evidence requirements, iteration budgets, and human approval.
