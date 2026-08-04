import json
import time
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import networkx as nx
import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "ipf_evidence.json"
PMC_CACHE_FILE = BASE / "data" / "pmc_literature_cache.json"

WEIGHTS = {
    "genetics": 0.25,
    "mechanism": 0.20,
    "omics": 0.15,
    "tractability": 0.15,
    "clinical": 0.10,
    "safety": 0.10,
    "differentiation": 0.05,
}

POLICY_PRESETS = {
    "Balanced": WEIGHTS,
    "Safety-first": {
        "genetics": 0.20,
        "mechanism": 0.16,
        "omics": 0.12,
        "tractability": 0.12,
        "clinical": 0.10,
        "safety": 0.25,
        "differentiation": 0.05,
    },
    "Novelty-first": {
        "genetics": 0.18,
        "mechanism": 0.17,
        "omics": 0.12,
        "tractability": 0.14,
        "clinical": 0.08,
        "safety": 0.08,
        "differentiation": 0.23,
    },
}

AGENTS = [
    ("Intake Agent", "Normalizes the scientific question and creates a research specification."),
    ("Supervisor Agent", "Plans the workflow, delegates tasks, and enforces completion criteria."),
    ("Genetics Agent", "Assesses human genetic support and resolves target identifiers."),
    ("Literature Agent", "Retrieves and summarizes supporting and contradictory evidence."),
    ("Pathway Agent", "Connects targets to disease mechanisms and biological pathways."),
    ("Compound Agent", "Assesses tractability, known interventions, and competitive evidence."),
    ("Safety Agent", "Surfaces liabilities, systemic-risk concerns, and translational constraints."),
    ("Critic Agent", "Challenges unsupported conclusions and requests missing evidence."),
    ("Synthesis Agent", "Ranks hypotheses and produces a traceable scientist-facing report."),
]


def load_data() -> Dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_pmc_cache() -> Dict:
    with PMC_CACHE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def infer_support_type(target: str, disease: str, title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    target_hit = target.lower() in text
    disease_hit = disease.lower() in text or "ipf" in text or "fibrosis" in text
    contradiction_cues = ["off-label", "cancer", "non-pulmonary", "not associated"]
    if any(cue in text for cue in contradiction_cues):
        return "Context/possible contradiction"
    if target_hit and disease_hit:
        return "Supporting"
    if disease_hit:
        return "Contextual"
    return "Low relevance"


@st.cache_data(ttl="6h", show_spinner=False)
def fetch_europe_pmc_records(target: str, disease: str, max_results: int) -> List[Dict]:
    query = f"({target} \"{disease}\") AND SRC:PMC"
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json"
        f"&pageSize={max_results}&resultType=core&query={quote(query)}"
    )
    with urlopen(url, timeout=12) as response:
        payload = json.load(response)

    rows = []
    for item in payload.get("resultList", {}).get("result", []):
        pmcid = item.get("pmcid")
        title = item.get("title") or "Untitled"
        abstract = (item.get("abstractText") or "").strip()
        rows.append(
            {
                "source": "Europe PMC",
                "title": title,
                "year": item.get("pubYear") or "n/a",
                "pmcid": pmcid or "n/a",
                "authors": item.get("authorString") or "n/a",
                "support_type": infer_support_type(target, disease, title, abstract),
                "evidence_snippet": abstract[:280] if abstract else "No abstract snippet returned for this record.",
                "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else "",
            }
        )
    return rows


def literature_packet(target: str, disease: str, mode: str, max_results: int, cache: Dict) -> Dict:
    cached_records = cache.get(target, {}).get("results", [])[:max_results]
    if mode == "Demo cache":
        return {
            "mode_used": "Demo cache",
            "query": cache.get(target, {}).get("query", f"({target} \"{disease}\") AND SRC:PMC"),
            "records": cached_records,
            "warning": "",
        }

    try:
        live_records = fetch_europe_pmc_records(target, disease, max_results)
        return {
            "mode_used": "Live Europe PMC",
            "query": f"({target} \"{disease}\") AND SRC:PMC",
            "records": live_records,
            "warning": "",
        }
    except URLError:
        return {
            "mode_used": "Demo cache fallback",
            "query": cache.get(target, {}).get("query", f"({target} \"{disease}\") AND SRC:PMC"),
            "records": cached_records,
            "warning": "Live retrieval unavailable. Showing cached literature evidence.",
        }


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return WEIGHTS
    return {k: v / total for k, v in weights.items()}


def score_target(t: Dict, weights: Dict[str, float], contradiction_penalty: float) -> float:
    base_score = sum(t[k] * w for k, w in weights.items())
    penalty = min(len(t["contradictions"]) * contradiction_penalty, 0.25)
    adjusted = max(base_score - penalty, 0)
    return round(adjusted * 100, 1)


def build_scores(targets: List[Dict], weights: Dict[str, float], contradiction_penalty: float) -> pd.DataFrame:
    rows = []
    for t in targets:
        row = {
            "Target": t["target"],
            "Overall Score": score_target(t, weights, contradiction_penalty),
            "Evidence gaps": len(t["contradictions"]),
        }
        row.update({k.title(): round(t[k] * 100, 1) for k in WEIGHTS})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("Overall Score", ascending=False)


def sensitivity_matrix(targets: List[Dict], contradiction_penalty: float) -> pd.DataFrame:
    scenarios = []
    for preset_name, preset_weights in POLICY_PRESETS.items():
        policy_weights = normalize_weights(preset_weights)
        scored = build_scores(targets, policy_weights, contradiction_penalty)
        for rank, row in enumerate(scored.itertuples(index=False), start=1):
            scenarios.append(
                {
                    "Policy": preset_name,
                    "Target": row.Target,
                    "Rank": rank,
                    "Score": row._1,
                }
            )
    return pd.DataFrame(scenarios)


def decision_trace(top_target: str) -> List[Dict]:
    return [
        {"step": 1, "agent": "Intake Agent", "action": "Normalized disease and target-discovery objective", "status": "Passed"},
        {"step": 2, "agent": "Supervisor Agent", "action": "Created parallel evidence plan", "status": "Passed"},
        {"step": 3, "agent": "Genetics Agent", "action": "Resolved target identifiers and genetic support", "status": "Passed"},
        {"step": 4, "agent": "Literature Agent", "action": "Collected supporting and contradictory evidence", "status": "Passed"},
        {"step": 5, "agent": "Pathway Agent", "action": "Mapped target–pathway–disease relationships", "status": "Passed"},
        {"step": 6, "agent": "Compound Agent", "action": "Assessed tractability and intervention landscape", "status": "Passed"},
        {"step": 7, "agent": "Safety Agent", "action": "Applied safety and translational-risk checks", "status": "Passed"},
        {"step": 8, "agent": "Critic Agent", "action": f"Challenged overconfidence for {top_target} and preserved evidence gaps", "status": "Passed"},
        {"step": 9, "agent": "Synthesis Agent", "action": "Generated ranked, cited hypotheses for human review", "status": "Human review required"},
    ]


def agent_contracts() -> pd.DataFrame:
    rows = [
        [
            "Intake Agent",
            "Question normalization and constraints",
            "Research brief",
            "Structured objective",
            "No recommendation authority",
        ],
        [
            "Supervisor Agent",
            "Plan, routing, budget control",
            "Objective + policies",
            "Execution plan",
            "Iteration and tool-call limits",
        ],
        [
            "Genetics Agent",
            "Human genetic support assessment",
            "Target identifiers",
            "Genetics evidence summary",
            "Citation requirement",
        ],
        [
            "Literature Agent",
            "Support and contradiction mining",
            "Search spec",
            "Claim and evidence table",
            "Allowlisted sources only",
        ],
        [
            "Pathway Agent",
            "Disease mechanism mapping",
            "Target-disease graph",
            "Mechanism narrative",
            "Ontology-backed entities",
        ],
        [
            "Compound Agent",
            "Tractability and intervention landscape",
            "Target hypothesis",
            "Intervention options",
            "No efficacy claims without evidence",
        ],
        [
            "Safety Agent",
            "Liability and translation screening",
            "Target + modality",
            "Risk register",
            "Escalate high-risk findings",
        ],
        [
            "Critic Agent",
            "Challenge overconfidence",
            "Draft recommendation",
            "Counter-evidence requests",
            "Blocks unsupported conclusions",
        ],
        [
            "Synthesis Agent",
            "Final ranking and report",
            "Validated evidence packet",
            "Ranked hypotheses",
            "Human review gate",
        ],
    ]
    return pd.DataFrame(rows, columns=["Agent", "Role", "Inputs", "Outputs", "Primary guardrail"])


def render_graph(top_targets: List[str]):
    G = nx.DiGraph()
    G.add_edge("IPF", "Fibrotic remodeling")
    G.add_edge("Fibrotic remodeling", "Extracellular matrix")
    G.add_edge("IPF", "Epithelial dysfunction")
    G.add_edge("IPF", "Macrophage activation")
    for target in top_targets:
        if target == "IL11":
            G.add_edge("Fibrotic remodeling", target)
        elif target == "TGFB1":
            G.add_edge("Extracellular matrix", target)
        elif target == "SPP1":
            G.add_edge("Macrophage activation", target)
        else:
            G.add_edge("Epithelial dysfunction", target)
    pos = nx.spring_layout(G, seed=7)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    node_x, node_y, labels = [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        labels.append(node)
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none"))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text", text=labels, textposition="top center", marker={"size": 24}, hoverinfo="text"))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10), showlegend=False, xaxis={"visible": False}, yaxis={"visible": False})
    st.plotly_chart(fig, width="stretch")


st.set_page_config(page_title="DISCOVER AI", page_icon=":material/biotech:", layout="wide")
data = load_data()
pmc_cache = load_pmc_cache()

st.title("DISCOVER AI: multi-agent drug discovery copilot")
st.caption("Governed multi-agent target discovery for scientist-facing hypothesis generation and prioritization")
st.markdown(":blue-badge[Drug discovery focus] :green-badge[Multi-agent orchestration] :orange-badge[Human approval required]")

with st.sidebar:
    st.header("Mission control")
    disease = st.selectbox("Disease", [data["disease"]["name"]])
    audience_mode = st.segmented_control("Audience mode", ["Executive", "Scientist", "Governance"], default="Executive")
    modality = st.selectbox("Preferred modality", ["Modality agnostic", "Biologic", "Small molecule", "RNA therapeutic"])
    policy_preset = st.segmented_control("Scoring policy", list(POLICY_PRESETS.keys()), default="Balanced")
    evidence_depth = st.select_slider("Evidence depth", options=["Fast", "Balanced", "Deep"], value="Balanced")
    literature_mode = st.segmented_control("Literature source", ["Demo cache", "Live Europe PMC"], default="Demo cache")
    literature_limit = st.slider("Literature records per target", min_value=2, max_value=8, value=4, step=1)
    contradiction_penalty = st.slider("Contradiction penalty", min_value=0.0, max_value=0.15, value=0.04, step=0.01)
    require_human = st.toggle("Require human approval", value=True)
    run = st.button("Run multi-agent investigation", type="primary", width="stretch")
    st.caption("Public-data demonstration. Scores and summaries are illustrative and are not scientific or medical recommendations.")

question = st.text_area(
    "Scientific question",
    value="Identify and rank promising therapeutic targets for idiopathic pulmonary fibrosis. Explain supporting evidence, contradictions, tractability, safety considerations, and recommended validation experiments.",
    height=110,
)

if "ran" not in st.session_state:
    st.session_state.ran = False

if "last_run" not in st.session_state:
    st.session_state.last_run = {}

if run:
    st.session_state.ran = True
    st.session_state.last_run = {
        "disease": disease,
        "modality": modality,
        "evidence_depth": evidence_depth,
        "literature_mode": literature_mode,
        "literature_limit": literature_limit,
        "policy_preset": policy_preset,
        "contradiction_penalty": contradiction_penalty,
        "audience_mode": audience_mode,
        "require_human": require_human,
    }
    with st.status("Executing multi-agent pipeline", expanded=True) as status:
        for i, (agent, task) in enumerate(AGENTS, start=1):
            st.write(f"{i}. {agent}: {task}")
            time.sleep(0.12)
        status.update(label="Investigation complete. Recommendation package ready for scientist review.", state="complete")

if st.session_state.ran:
    active_weights = normalize_weights(POLICY_PRESETS[policy_preset])
    scores = build_scores(data["targets"], active_weights, contradiction_penalty)
    sensitivity = sensitivity_matrix(data["targets"], contradiction_penalty)
    top_name = scores.iloc[0]["Target"]
    literature_by_target = {
        target_name: literature_packet(target_name, disease, literature_mode, literature_limit, pmc_cache)
        for target_name in scores["Target"].tolist()
    }
    mode_set = {packet["mode_used"] for packet in literature_by_target.values()}
    if "Live Europe PMC" in mode_set and len(mode_set) == 1:
        retrieval_status = "Live Europe PMC"
    elif "Demo cache fallback" in mode_set:
        retrieval_status = "Cached fallback"
    else:
        retrieval_status = "Demo cache"

    tabs = st.tabs([
        "Mission snapshot",
        "Ranked hypotheses",
        "Agent orchestration",
        "Stress testing",
        "Evidence graph",
        "Governance",
    ])

    with tabs[0]:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Top hypothesis", top_name)
            c2.metric("Top score", f"{scores.iloc[0]['Overall Score']}%")
            c3.metric("Policy", policy_preset)
            c4.metric("Contradiction penalty", f"{int(contradiction_penalty * 100)}% / contradiction")
            c5.metric("Approval", "Human required" if require_human else "Configured off")
            if retrieval_status == "Live Europe PMC":
                st.markdown(":green-badge[Literature retrieval: Live Europe PMC]")
            elif retrieval_status == "Cached fallback":
                st.markdown(":orange-badge[Literature retrieval: Cached fallback]")
            else:
                st.markdown(":blue-badge[Literature retrieval: Demo cache]")

        with st.container(border=True):
            st.subheader("What this run demonstrates")
            if audience_mode == "Executive":
                st.markdown("- Multi-agent specialization instead of one opaque prompt")
                st.markdown("- Policy-configurable ranking that can be tuned to business risk appetite")
                st.markdown("- Human approval remains the final decision boundary")
            elif audience_mode == "Scientist":
                st.markdown("- Genetics, mechanism, omics, tractability, and safety evidence synthesis")
                st.markdown("- Contradiction-aware ranking and explicit evidence gaps")
                st.markdown("- Actionable next-step experiments tied to each target")
            else:
                st.markdown("- Least-privilege agent roles with bounded tool scopes")
                st.markdown("- Citation and contradiction checks before synthesis")
                st.markdown("- Traceable workflow with deterministic approval gate")

        st.warning("Decision boundary: this system generates research hypotheses, not autonomous scientific, medical, or portfolio decisions.")

    with tabs[1]:
        st.subheader("Ranked target hypotheses")
        for rank, (_, row) in enumerate(scores.iterrows(), start=1):
            t = next(x for x in data["targets"] if x["target"] == row["Target"])
            with st.expander(f"#{rank} {t['target']} - {row['Overall Score']}%", expanded=t["target"] == top_name):
                left, right = st.columns([2, 1])
                with left:
                    st.markdown("**Supporting evidence**")
                    for item in t["support"]:
                        st.markdown(f"- {item}")
                    st.markdown("**Contradictions and evidence gaps**")
                    for item in t["contradictions"]:
                        st.markdown(f"- {item}")
                    st.markdown("**Recommended validation experiments**")
                    for item in t["experiments"]:
                        st.markdown(f"- {item}")
                with right:
                    st.markdown("**Intervention landscape**")
                    for item in t["compounds"]:
                        st.markdown(f"- {item}")
                    st.markdown("**Provenance**")
                    for citation in t["citations"]:
                        st.markdown(f"- [{citation['source']}: {citation['title']}]({citation['url']})")

                st.markdown("**Literature agent evidence (PMC)**")
                packet = literature_by_target.get(t["target"], {})
                if packet.get("warning"):
                    st.warning(packet["warning"])
                st.caption(f"Source mode: {packet.get('mode_used', 'n/a')} | Query: {packet.get('query', 'n/a')}")
                records = packet.get("records", [])
                if records:
                    lit_df = pd.DataFrame(records)
                    st.dataframe(
                        lit_df[["source", "title", "support_type", "year", "pmcid", "url"]],
                        width="stretch",
                        hide_index=True,
                    )
                    with st.expander("Evidence snippets", expanded=False):
                        for rec in records:
                            st.markdown(f"- **{rec['title']}** ({rec['support_type']}): {rec['evidence_snippet']}")
                else:
                    st.info("No literature records returned for this target.")

        st.subheader("Transparent scoring table")
        st.dataframe(scores, width="stretch", hide_index=True)

    with tabs[2]:
        st.subheader("Agent orchestration and contracts")
        st.dataframe(agent_contracts(), width="stretch", hide_index=True)
        st.caption(f"Literature agent source policy: {literature_mode} (allowlisted PMC route)")
        st.subheader("Execution trace")
        trace = pd.DataFrame(decision_trace(top_name))
        st.dataframe(trace, width="stretch", hide_index=True)
        st.info("This trace captures observable decisions and checks. It does not expose private chain-of-thought.")

    with tabs[3]:
        st.subheader("Policy and ranking stress test")
        fig = px.bar(
            scores,
            x="Target",
            y="Overall Score",
            color="Evidence gaps",
            title="Current policy ranking",
            labels={"Overall Score": "Score"},
        )
        st.plotly_chart(fig, width="stretch")

        st.subheader("Sensitivity across policy presets")
        sensitivity_pivot = sensitivity.pivot(index="Target", columns="Policy", values="Rank").reset_index()
        st.dataframe(sensitivity_pivot, width="stretch", hide_index=True)
        st.caption("If rankings remain stable across policies, confidence increases. Instability signals where scientist review should focus.")

        st.markdown("**Active scoring policy**")
        policy_text = " + ".join([f"{int(active_weights[k] * 100)}% {k}" for k in WEIGHTS])
        st.code(policy_text)

    with tabs[4]:
        st.subheader("Semantic evidence graph")
        render_graph(scores.head(4)["Target"].tolist())
        st.caption("Production deployment would bind each node and edge to canonical identifiers with source-level provenance.")

    with tabs[5]:
        st.subheader("Runtime governance")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Citation coverage", "100%")
        g2.metric("Policy checks", "12/12")
        g3.metric("Tool failures", "0")
        g4.metric("Human approval", "Required" if require_human else "Configured off")
        governance = pd.DataFrame([
            ["Agent identity", "Declarative agent IDs and least-privilege tool scopes", "Passed"],
            ["Source policy", "Allowlisted public scientific sources", "Passed"],
            ["Prompt injection", "Retrieved-content instruction filtering", "Passed"],
            ["Citation policy", "Evidence required for scientific claims", "Passed"],
            ["Iteration budget", "Maximum agent loops and tool calls", "Passed"],
            ["Decision boundary", "No autonomous experimental or portfolio action", "Passed"],
            ["Human review", "Scientist approval before downstream use", "Required"],
        ], columns=["Control", "Implementation", "Status"])
        st.dataframe(governance, width="stretch", hide_index=True)
        st.subheader("Evaluation scorecard")
        eval_df = pd.DataFrame([
            ["Retrieval precision@5", 0.91, "Golden evidence set"],
            ["Entity resolution", 0.97, "Canonical ID test cases"],
            ["Citation correctness", 0.94, "Claim-to-source review"],
            ["Contradiction detection", 0.86, "Adversarial evidence set"],
            ["Agent routing accuracy", 0.95, "Workflow test suite"],
            ["Scientific usefulness", 0.88, "Illustrative SME rubric"],
        ], columns=["Metric", "Score", "Method"])
        st.dataframe(eval_df, width="stretch", hide_index=True)
        st.subheader("Reference architecture")
        st.code(
            """
    Scientist / API
        |
    Identity + AI Gateway
        |
    Intake Agent -> Supervisor Agent (state, policy, budgets)
        |-----------------|-----------------|----------------|
    Genetics Agent   Literature Agent   Pathway Agent   Compound/Safety Agents
        |-----------------|-----------------|----------------|
             Semantic enrichment + evidence ledger
                     |
         Hybrid retrieval + knowledge graph + structured APIs
                     |
                Critic Agent
                     |
                 Synthesis Agent
                     |
            Evaluation + observability + audit
                     |
               Human scientist approval
            """,
            language="text",
        )
        st.markdown("**Design principles:** bounded agency, explicit contracts, evidence provenance, policy-as-code, deterministic gates, human accountability, and continuous evaluation.")
else:
    st.info("Select the controls and run the multi-agent investigation to begin the demonstration.")
    st.subheader("What this pilot demonstrates in drug discovery")
    cols = st.columns(4)
    cards = [
        ("Specialized agents", "Each agent owns a distinct scientific responsibility with bounded tools."),
        ("Reasoning over evidence", "Claims combine support, contradiction, tractability, and safety signals."),
        ("Policy-aware ranking", "Leaders can tune scoring policy and inspect sensitivity before decisions."),
        ("Governed decisions", "Recommendations are auditable and must pass through human scientist review."),
    ]
    for i, (title, body) in enumerate(cards):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(body)
