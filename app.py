# app.py
import json
import streamlit as st
from db import init_db, list_opportunities, create_opportunity, get_opportunity, update_opportunity
from llm import run_day0_analysis
from utils import compute_bucket
from utils import estimate_openai_cost

st.set_page_config(page_title="JD Copilot", layout="wide")

DEFAULT_RUBRIC = """1) Autonomy
2) Scope/Impact
3) Learning/Growth
4) Manager/Team quality signals
5) Role clarity vs ambiguity
6) Domain fit
7) Execution intensity (pace, cross-functional load)
8) Comp/level alignment signals
"""

DEFAULT_PROFILE = """Paste your resume summary here as structured bullets:
- Roles + key achievements (with metrics)
- Tools/skills
- Domains
- 3 signature stories (STAR bullets)
"""

DQ_CODES = [
    "COMP_BELOW_THRESHOLD",
    "LOCATION_MISMATCH",
    "DOMAIN_NOT_INTERESTED",
    "SENIORITY_MISMATCH",
    "SCOPE_MISMATCH",
    "TECH_STACK_MISMATCH",
    "CULTURE_RED_FLAG",
    "BUSINESS_FUNDAMENTALS_CONCERN",
    "TIMING_CONSTRAINT",
]

def render_analysis(a: dict):
    st.subheader("Role Summary")
    st.write(a.get("role_summary", ""))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Responsibilities")
        st.write(a.get("extracted_responsibilities", []))
    with c2:
        st.subheader("Requirements")
        st.write(a.get("extracted_requirements", []))

    st.subheader("Scorecard (1–5)")
    for item in a.get("scorecard", []):
        with st.expander(f"{item['quality']} — {item['score']}/5", expanded=False):
            st.write(item.get("rationale", ""))
            ev = item.get("evidence", [])
            if ev:
                st.markdown("**Evidence**")
                for e in ev:
                    st.markdown(f"- “{e.get('quote','').strip()}” — {e.get('note','')}")
            unk = item.get("unknowns", [])
            if unk:
                st.markdown("**Unknowns**")
                st.write(unk)

    st.subheader("Strengths & Gaps")
    sg = a.get("strengths_and_gaps", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Strengths**")
        st.write(sg.get("strengths", []))
    with c2:
        st.markdown("**Gaps**")
        st.write(sg.get("gaps", []))
    with c3:
        st.markdown("**Bridging language**")
        st.write(sg.get("bridging_language", []))

    st.subheader("Storyline (Cover Letter Beats)")
    story = a.get("storyline", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Why Company**")
        st.write(story.get("why_company", []))
        st.markdown("**Why Role**")
        st.write(story.get("why_role", []))
    with c2:
        st.markdown("**Why Me**")
        st.write(story.get("why_me", []))
        st.markdown("**Closing**")
        st.write(story.get("closing", []))

    st.subheader("Interview Prep")
    ip = a.get("interview_prep", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Likely questions**")
        st.write(ip.get("likely_questions", []))
    with c2:
        st.markdown("**Questions to ask**")
        st.write(ip.get("questions_to_ask", []))

    st.subheader("Downside Case")
    dc = a.get("downside_case", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top risks**")
        st.write(dc.get("top_risks", []))
    with c2:
        st.markdown("**What to verify**")
        st.write(dc.get("what_to_verify", []))

def main():
    init_db()

    st.title("JD Copilot — Opportunity Tracker + Day Buckets")

    with st.sidebar:
        st.header("Your inputs")
        rubric = st.text_area("Rubric (core qualities)", value=DEFAULT_RUBRIC, height=180)
        profile = st.text_area("Profile (resume summary/story bank)", value=DEFAULT_PROFILE, height=220)

        st.divider()
        st.header("Add Opportunity")
        company = st.text_input("Company")
        role_title = st.text_input("Role title")
        jd_link = st.text_input("JD link (optional)")
        jd_text = st.text_area("JD text", height=180)

        if st.button("Create", type="primary", use_container_width=True):
            if not company.strip() or not role_title.strip():
                st.error("Company and role title are required.")
            else:
                oid = create_opportunity(company, role_title, jd_link, jd_text)
                st.success(f"Created opportunity #{oid}")
                st.rerun()

        st.divider()
        st.header("Opportunities")
        opps = list_opportunities()
        labels = [f"#{o['id']} — {o['company']} / {o['role_title']} ({o['stage']})" for o in opps]
        selected_idx = st.selectbox("Select", range(len(opps)) if opps else [], format_func=lambda i: labels[i] if opps else "")
        selected_id = opps[selected_idx]["id"] if opps else None

    if not selected_id:
        st.info("Create or select an opportunity to begin.")
        return

    opp = get_opportunity(selected_id)
    if not opp:
        st.error("Opportunity not found.")
        return

    st.subheader(f"#{opp['id']} — {opp['company']} / {opp['role_title']}")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        company_edit = st.text_input("Company", value=opp["company"])
        role_edit = st.text_input("Role Title", value=opp["role_title"])
        link_edit = st.text_input("JD Link", value=opp.get("jd_link") or "")
    with c2:
        stage = st.selectbox("Stage", ["NEW","ANALYZED","DECISION_PENDING","QUALIFIED_PREP","APPLIED","INTERVIEWING","CLOSED","DQ"], index=["NEW","ANALYZED","DECISION_PENDING","QUALIFIED_PREP","APPLIED","INTERVIEWING","CLOSED","DQ"].index(opp["stage"]))
        decision = st.selectbox("Decision", ["PENDING","QUALIFIED","UNQUALIFIED"], index=["PENDING","QUALIFIED","UNQUALIFIED"].index(opp["decision"]))
    with c3:
        st.caption("SLA / Next action")
        st.write("Bucket due:", opp.get("bucket_due") or "—")
        st.write("Next action:", opp.get("next_action") or "—")
        st.write("Next due:", opp.get("next_action_due") or "—")

    jd_text_edit = st.text_area("JD Text", value=opp.get("jd_text") or "", height=220)

    if st.button("Save fields"):
        update_opportunity(opp["id"], {
            "company": company_edit,
            "role_title": role_edit,
            "jd_link": link_edit,
            "jd_text": jd_text_edit,
            "stage": stage,
            "decision": decision
        })
        opp = get_opportunity(selected_id)
        st.success("Saved.")
        st.rerun()

    st.divider()

    # Compute SLA updates
    if opp.get("day0_at"):
        bucket = compute_bucket(opp["stage"], opp["day0_at"], opp["decision"])
        if bucket["stage"] != opp["stage"] or bucket["bucket_due"] != opp.get("bucket_due") or bucket["next_action"] != (opp.get("next_action") or ""):
            update_opportunity(opp["id"], {
                "stage": bucket["stage"],
                "bucket_due": bucket["bucket_due"],
                "next_action": bucket["next_action"],
                "next_action_due": bucket["next_action_due"],
            })
            opp = get_opportunity(selected_id)

    # Decision / DQ handling
    st.subheader("Qualification")
    dq_codes = st.multiselect("DQ reason codes (if UNQUALIFIED)", DQ_CODES, default=[])
    dq_note = st.text_input("DQ note (optional)", value="")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Mark QUALIFIED", use_container_width=True):
            update_opportunity(opp["id"], {"decision": "QUALIFIED"})
            st.rerun()
    with c2:
        if st.button("Mark UNQUALIFIED (DQ)", use_container_width=True):
            payload = [{"code": c, "note": dq_note} for c in dq_codes]
            update_opportunity(opp["id"], {"decision": "UNQUALIFIED", "dq_reasons_json": json.dumps(payload)})
            st.rerun()
    with c3:
        if st.button("Reset to PENDING", use_container_width=True):
            update_opportunity(opp["id"], {"decision": "PENDING", "dq_reasons_json": None})
            st.rerun()

    st.divider()

    st.subheader("Day 0 Analysis")
    run_btn = st.button("Run Day 0 analysis", type="primary")
    if run_btn:
        if not (opp.get("jd_text") or "").strip():
            st.error("Paste the JD text first.")
        else:
            with st.spinner("Analyzing JD..."):
                try:
                    result = run_day0_analysis(
                        jd_text=opp["jd_text"],
                        company=opp["company"],
                        role_title=opp["role_title"],
                        user_rubric=rubric,
                        user_profile=profile,
                    )
                    analysis = result["analysis"]
                    model = result["model"]
                    
                    prompt_tokens = result["prompt_tokens"]
                    completion_tokens = result["completion_tokens"]
                    total_tokens = result["total_tokens"]
                    
                    estimated_cost = estimate_openai_cost(
                        prompt_tokens,
                        completion_tokens,
                        model
                    )
                    
                    update_opportunity(opp["id"], {
                        "analysis_json": json.dumps(analysis),
                        "analysis_model": model,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost_usd": estimated_cost,
                        "stage": "ANALYZED"
                    })

                    st.success("Analysis saved.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    if opp.get("analysis_json"):
        analysis = json.loads(opp["analysis_json"])
        render_analysis(analysis)

        st.download_button(
            "Download analysis JSON",
            data=json.dumps(analysis, indent=2),
            file_name=f"analysis_{opp['id']}.json",
            mime="application/json",
        )

if __name__ == "__main__":

    main()
