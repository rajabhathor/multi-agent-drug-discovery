# Monday Demo Script - DISCOVER AI

## 0:00–1:00 — Opening

"Today I am demonstrating a governed multi-agent pattern for early drug-discovery research. The goal is not autonomous science. The goal is to coordinate specialized agents across genetics, biology, literature, compounds, clinical evidence, and safety, then produce a traceable hypothesis package for scientist review."

## 1:00–2:00 — Define the use case

“Our scenario asks the platform to identify and rank promising therapeutic targets for idiopathic pulmonary fibrosis. It must explain the supporting evidence, surface contradictions, assess tractability and safety, and recommend validation experiments.”

Call out the boundary: "The output is a research hypothesis, not a medical, experimental, or portfolio decision."

## 2:00–4:00 — Run the workflow

Click **Run multi-agent investigation**.

Narrate the agents:
- Intake normalizes the scientific question.
- Supervisor creates the plan and controls state, policy, and budgets.
- Specialist agents collect genetics, literature, pathway, compound, and safety evidence.
- Critic challenges overconfidence and requests missing evidence.
- Synthesis produces a ranked, cited result.

Before moving on, point to controls in the sidebar:
- `Audience mode` changes narrative for Executive, Scientist, or Governance stakeholders.
- `Scoring policy` lets us switch weighting priorities.
- `Contradiction penalty` stress-tests ranking robustness when evidence gaps increase.

## 4:00–7:00 — Explain the result

Open **Ranked hypotheses** and expand the highest-ranked target.

Say:
"The ranking is not an opaque LLM opinion. It is a configurable evidence policy combining genetics, mechanism, omics, tractability, clinical evidence, safety, and differentiation."

Show:
- Supporting evidence
- Contradictions
- Intervention landscape
- Validation experiments
- Provenance links

## 7:00-8:30 - Agent orchestration

Open **Agent orchestration**.

"The UI shows both agent contracts and an accountable execution trace: what was investigated, which specialist acted, and what decision followed. We do not expose private chain-of-thought."

## 8:30-9:30 - Stress testing

Open **Stress testing**.

"Now I can switch policy presets in real time to show how strategy changes ranking. If top targets remain stable across policies, confidence increases. If ranking shifts, that flags where scientist review should focus."

## 9:30-10:00 - Knowledge graph

Open **Knowledge Graph**.

"The graph semantically connects disease, genes, proteins, pathways, compounds, assays, publications, and trials. In production, each node and edge would use canonical identifiers and source-level provenance."

## 10:00-11:00 - Governance and evaluation

Open **Governance**.

"Every agent has identity, least-privilege tools, approved sources, loop budgets, citation requirements, and explicit prohibited actions. Every release is tested against retrieval, routing, groundedness, contradiction handling, safety, latency, and scientific usefulness metrics."

## 11:00-12:00 - Close

"The value of multi-agent AI is not adding more agents. It is separating responsibilities where specialization, context isolation, tool permissions, and evaluation boundaries materially improve quality and control."

Close with:
"Every scientific claim has provenance, every agent action has identity, and every recommendation has an accountable human owner."
