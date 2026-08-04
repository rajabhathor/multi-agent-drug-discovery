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

## LLM-assisted app variant

Use the new LLM app entrypoint when you want to demo real model-backed synthesis on top of deterministic scoring:

```bash
streamlit run app_llm.py
```

Recommended environment variables:

- `OPENAI_API_KEY` or `LLM_API_KEY`: API key for OpenAI-compatible chat completion endpoint
- `LLM_MODEL` (optional): defaults to `gpt-4o-mini`
- `LLM_BASE_URL` (optional): defaults to `https://api.openai.com/v1`

Windows PowerShell example:

```powershell
$env:OPENAI_API_KEY="<your-key>"
$env:LLM_MODEL="gpt-4o-mini"
c:/Mutli-Agent_ai_demo/.venv/Scripts/python.exe -m streamlit run c:/Mutli-Agent_ai_demo/app_llm.py
```

If no API key is configured, the app still runs and shows deterministic ranking plus literature retrieval, but LLM synthesis calls are disabled.

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
