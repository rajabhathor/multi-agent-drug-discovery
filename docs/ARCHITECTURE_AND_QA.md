# Architecture and Likely Q&A

## Agent contract

Each agent should define:
- Purpose and scope
- Input/output schema
- Allowed and prohibited tools
- Identity and permissions
- Evidence and citation policy
- Time, cost, and iteration budgets
- Failure and escalation behavior
- Evaluation metrics

## Why multi-agent?

Use multiple agents only when specialization has a concrete benefit:
- Separate scientific domains
- Different tools or data entitlements
- Context isolation
- Independent evaluation
- Parallel investigation
- Critic/reviewer separation

## Why not one large prompt?

A single prompt makes planning, tool control, context, provenance, and evaluation difficult to isolate. A graph-based workflow allows deterministic gates, resumable state, parallel work, targeted retries, and per-agent controls.

## RAG versus Retrieval-Augmented Reasoning

Basic RAG retrieves documents and generates an answer. Retrieval-Augmented Reasoning decomposes the question, resolves entities, combines vector, lexical, structured, and graph retrieval, evaluates contradictions, and iteratively fills evidence gaps before synthesis.

## Production roadmap

1. Curated public evidence pilot
2. Scientist-created golden dataset and evaluation rubric
3. Internal data integration with entitlement enforcement
4. Shadow-mode use alongside existing research workflows
5. Controlled pilot with documented decision boundaries
6. Continuous evaluation, drift monitoring, and policy updates

## Likely questions

**What are the scoring weights doing?**
The weights define policy priorities across evidence dimensions such as genetics, mechanism, omics, tractability, clinical evidence, safety, and differentiation. They are not model randomness; they are explicit decision-policy settings.

**Why provide multiple policy presets?**
Different organizations and therapeutic programs have different risk appetites. Balanced, Safety-first, and Novelty-first presets allow transparent strategy shifts without changing the underlying evidence.

**How do you prevent weight manipulation from hiding risk?**
We preserve contradiction counts, apply contradiction penalties, and expose sensitivity views across presets. A target that only wins under one extreme policy is flagged for deeper scientist review.

**What does ranking stability mean?**
If top targets remain highly ranked across policy presets, confidence in prioritization increases. If rankings move significantly, this signals policy-sensitive uncertainty and review focus areas.

**How do you prevent hallucination?**
Require evidence for scientific claims, use allowlisted tools, validate citations, preserve uncertainty, run contradiction checks, and block unsupported final conclusions.

**How do you secure internal research?**
Use identity-aware retrieval, least-privilege tool scopes, tenant and project isolation, encrypted state, confidential-computing options where required, audit logs, and no model training on enterprise prompts or outputs without approval.

**How do you evaluate scientific usefulness?**
Create disease-specific golden questions and known evidence sets, then have scientists score correctness, completeness, novelty, contradiction handling, actionability, and calibration.

**How do AWS and GCP fit?**
Keep orchestration and agent contracts portable. Map model access, identity, storage, search, graph, observability, and policy enforcement to approved services on either cloud.

**Would you allow agents to initiate experiments?**
No. The system can propose experiments and prepare structured protocols, but execution requires scientist approval and integration through governed systems of record.
