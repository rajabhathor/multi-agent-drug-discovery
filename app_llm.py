import json
import os
import time
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
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


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return WEIGHTS
    return {k: v / total for k, v in weights.items()}


def score_target(target: Dict, weights: Dict[str, float], contradiction_penalty: float) -> float:
    base_score = sum(target[k] * w for k, w in weights.items())
    penalty = min(len(target["contradictions"]) * contradiction_penalty, 0.25)
    adjusted = max(base_score - penalty, 0)
    return round(adjusted * 100, 1)


def build_scores(targets: List[Dict], weights: Dict[str, float], contradiction_penalty: float) -> pd.DataFrame:
    rows = []
    for target in targets:
        row = {
            "Target": target["target"],
            "Overall Score": score_target(target, weights, contradiction_penalty),
            "Evidence gaps": len(target["contradictions"]),
        }
        row.update({k.title(): round(target[k] * 100, 1) for k in WEIGHTS})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("Overall Score", ascending=False)


@st.cache_data(ttl="6h", show_spinner=False)
def fetch_europe_pmc(target: str, disease: str, max_results: int) -> List[Dict]:
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
        rows.append(
            {
                "source": "Europe PMC",
                "title": item.get("title") or "Untitled",
                "year": item.get("pubYear") or "n/a",
                "pmcid": pmcid or "n/a",
                "authors": item.get("authorString") or "n/a",
                "evidence_snippet": (item.get("abstractText") or "")[:280] or "No abstract snippet returned.",
                "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else "",
            }
        )
    return rows


def literature_packet(target: str, disease: str, mode: str, max_results: int, cache: Dict) -> Dict:
    cached = cache.get(target, {}).get("results", [])[:max_results]
    if mode == "Demo cache":
        return {"mode": "Demo cache", "records": cached, "warning": ""}
    try:
        return {
            "mode": "Live Europe PMC",
            "records": fetch_europe_pmc(target, disease, max_results),
            "warning": "",
        }
    except URLError:
        return {
            "mode": "Demo cache fallback",
            "records": cached,
            "warning": "Live retrieval unavailable. Showing cached records.",
        }


def llm_config() -> Dict[str, str]:
    return {
        "api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    }


def call_openai_compatible(messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
    cfg = llm_config()
    if not cfg["api_key"]:
        return {"ok": False, "error": "Missing LLM_API_KEY or OPENAI_API_KEY"}

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            raw = json.load(resp)
        content = raw["choices"][0]["message"]["content"]
        return {"ok": True, "content": content, "model": cfg["model"]}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


def extract_json_block(text: str) -> Dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {"raw": text}
    return {"raw": text}


@st.cache_data(ttl="1h", show_spinner=False)
def llm_synthesis(
    question: str,
    target_json: str,
    records_json: str,
    weights_json: str,
    policy_name: str,
    contradiction_penalty: float,
    temperature: float,
) -> Dict:
    target = json.loads(target_json)
    records = json.loads(records_json)
    weights = json.loads(weights_json)

    system = (
        "You are a cautious biomedical research analyst. "
        "Use only provided evidence. Preserve uncertainty and contradictions. "
        "Return only JSON."
    )
    user = {
        "question": question,
        "policy_name": policy_name,
        "weights": weights,
        "contradiction_penalty": contradiction_penalty,
        "target": target,
        "literature_records": records,
        "required_output_schema": {
            "executive_summary": "string",
            "rationale_bullets": ["string"],
            "contradictions": ["string"],
            "recommended_experiments": ["string"],
            "confidence": "Low|Medium|High",
            "citations_used": ["pmcid-or-url"],
        },
    }

    resp = call_openai_compatible(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=temperature,
        max_tokens=1100,
    )
    if not resp["ok"]:
        return {"ok": False, "error": resp["error"]}

    parsed = extract_json_block(resp["content"])
    return {
        "ok": True,
        "model": resp.get("model", "unknown"),
        "parsed": parsed,
        "raw": resp["content"],
    }


st.set_page_config(page_title="DISCOVER AI (LLM)", page_icon=":material/psychology:", layout="wide")
data = load_json(DATA_FILE)
pmc_cache = load_json(PMC_CACHE_FILE)
cfg = llm_config()

st.title("DISCOVER AI: LLM-assisted multi-agent drug discovery")
st.caption("Deterministic ranking plus optional LLM synthesis for Literature, Critic, and Synthesis-style output.")

with st.sidebar:
    st.header("Mission control")
    disease = st.selectbox("Disease", [data["disease"]["name"]])
    policy_preset = st.segmented_control("Scoring policy", list(POLICY_PRESETS.keys()), default="Balanced")
    literature_mode = st.segmented_control("Literature source", ["Demo cache", "Live Europe PMC"], default="Demo cache")
    literature_limit = st.slider("Literature records per target", min_value=2, max_value=8, value=4)
    contradiction_penalty = st.slider("Contradiction penalty", min_value=0.0, max_value=0.15, value=0.04, step=0.01)
    temperature = st.slider("LLM temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
    run = st.button("Run LLM-assisted investigation", type="primary", width="stretch")

    if cfg["api_key"]:
        st.markdown(":green-badge[LLM configured]")
    else:
        st.markdown(":orange-badge[LLM not configured]")
        st.caption("Set OPENAI_API_KEY (or LLM_API_KEY) and optional LLM_MODEL, LLM_BASE_URL.")

question = st.text_area(
    "Scientific question",
    value="Identify and rank promising therapeutic targets for idiopathic pulmonary fibrosis. Explain supporting evidence, contradictions, tractability, safety considerations, and recommended validation experiments.",
    height=100,
)

if "ran_llm" not in st.session_state:
    st.session_state.ran_llm = False

if "last_llm_result" not in st.session_state:
    st.session_state.last_llm_result = {}

if run:
    st.session_state.ran_llm = True
    with st.status("Executing deterministic + literature retrieval steps", expanded=True) as status:
        for i, step in enumerate([
            "Intake and objective normalization",
            "Policy selection and weighting",
            "Literature retrieval",
            "Contradiction-aware scoring",
            "LLM synthesis readiness",
        ], start=1):
            st.write(f"{i}. {step}")
            time.sleep(0.1)
        status.update(label="Pipeline complete", state="complete")

if st.session_state.ran_llm:
    weights = normalize_weights(POLICY_PRESETS[policy_preset])
    scores = build_scores(data["targets"], weights, contradiction_penalty)
    top_target_name = scores.iloc[0]["Target"]
    top_target = next(target for target in data["targets"] if target["target"] == top_target_name)
    lit_packet = literature_packet(top_target_name, disease, literature_mode, literature_limit, pmc_cache)

    tab1, tab2, tab3 = st.tabs(["Ranked hypotheses", "LLM synthesis", "Governance notes"])

    with tab1:
        st.subheader("Deterministic ranking")
        st.dataframe(scores, width="stretch", hide_index=True)
        st.caption("This rank is deterministic and policy-driven. LLM output does not change score ordering.")

        st.subheader(f"Top target evidence: {top_target_name}")
        st.markdown("**Supporting evidence**")
        for item in top_target["support"]:
            st.markdown(f"- {item}")
        st.markdown("**Contradictions**")
        for item in top_target["contradictions"]:
            st.markdown(f"- {item}")

        if lit_packet["warning"]:
            st.warning(lit_packet["warning"])
        st.caption(f"Literature mode used: {lit_packet['mode']}")
        lit_df = pd.DataFrame(lit_packet["records"])
        if not lit_df.empty:
            st.dataframe(lit_df[["source", "title", "year", "pmcid", "url"]], width="stretch", hide_index=True)

    with tab2:
        st.subheader("LLM agent synthesis")
        st.caption("Produces a scientist-style narrative grounded in retrieved evidence and explicit contradictions.")
        if st.button("Generate LLM synthesis for top target", type="primary"):
            with st.spinner("Calling LLM for synthesis..."):
                result = llm_synthesis(
                    question=question,
                    target_json=json.dumps(top_target),
                    records_json=json.dumps(lit_packet["records"]),
                    weights_json=json.dumps(weights),
                    policy_name=policy_preset,
                    contradiction_penalty=contradiction_penalty,
                    temperature=temperature,
                )
                st.session_state.last_llm_result = result

        result = st.session_state.last_llm_result
        if not result:
            st.info("Run synthesis to generate the LLM-assisted agent report.")
        elif not result.get("ok", False):
            st.error(f"LLM call failed: {result.get('error', 'unknown error')}")
        else:
            parsed = result.get("parsed", {})
            st.success(f"LLM response generated with model: {result.get('model', 'unknown')}")
            st.markdown("**Executive summary**")
            st.write(parsed.get("executive_summary", "No summary field returned."))

            st.markdown("**Rationale bullets**")
            for item in parsed.get("rationale_bullets", []):
                st.markdown(f"- {item}")

            st.markdown("**Contradictions**")
            for item in parsed.get("contradictions", []):
                st.markdown(f"- {item}")

            st.markdown("**Recommended experiments**")
            for item in parsed.get("recommended_experiments", []):
                st.markdown(f"- {item}")

            st.markdown("**Confidence**")
            st.write(parsed.get("confidence", "n/a"))

            st.markdown("**Citations used**")
            for item in parsed.get("citations_used", []):
                st.markdown(f"- {item}")

            with st.expander("Raw LLM output"):
                st.code(result.get("raw", ""), language="json")

    with tab3:
        st.subheader("Governance notes for LLM mode")
        st.markdown("- Deterministic policy scoring remains the rank authority.")
        st.markdown("- LLM output is advisory narrative and does not bypass human review.")
        st.markdown("- Literature source is constrained to demo cache or Europe PMC retrieval.")
        st.markdown("- Contradictions are preserved explicitly in both deterministic and LLM layers.")
else:
    st.info("Run the LLM-assisted investigation to begin.")
    st.markdown("Use this app when you want to demonstrate real model-based synthesis on top of your deterministic policy engine.")