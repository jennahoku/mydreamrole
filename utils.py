# utils.py
from datetime import datetime, timedelta
from typing import Dict, Any

def iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)

def dt_to_iso(dt: datetime) -> str:
    return dt.isoformat()

def compute_bucket(stage: str, day0_at: str, decision: str) -> Dict[str, Any]:
    """
    Returns: bucket_due, next_action, next_action_due, suggested_stage
    """
    day0 = iso_to_dt(day0_at)
    now = datetime.utcnow()

    # Defaults
    next_action = ""
    next_due = None
    suggested_stage = stage

    if stage in ("NEW", "ANALYZED", "DECISION_PENDING") and decision == "PENDING":
        # Decision window Day 1-7
        suggested_stage = "DECISION_PENDING"
        next_action = "Decide: QUALIFIED or UNQUALIFIED (log DQ reasons if unqualified)"
        next_due = day0 + timedelta(days=7)

    elif decision == "QUALIFIED":
        # Prep window Day 8-12
        if stage not in ("APPLIED", "INTERVIEWING", "CLOSED"):
            suggested_stage = "QUALIFIED_PREP"
            next_action = "Run tailoring workflow: resume deltas + cover letter storyline + outreach note"
            next_due = day0 + timedelta(days=12)

    elif decision == "UNQUALIFIED":
        suggested_stage = "DQ"
        next_action = "No action (DQ logged)"
        next_due = None

    # If already applied and waiting
    if stage == "APPLIED":
        next_action = "Follow up or reach out to hiring manager if no response"
        next_due = max(now, day0 + timedelta(days=14))  # simple rule

    if stage == "INTERVIEWING":
        next_action = "Generate interview prep pack + post-interview follow-up drafts"
        next_due = now + timedelta(days=2)

    return {
        "bucket_due": dt_to_iso(next_due) if next_due else None,
        "next_action": next_action,
        "next_action_due": dt_to_iso(next_due) if next_due else None,
        "stage": suggested_stage
    }

def estimate_openai_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str
) -> float:
    """
    Rough cost estimate in USD based on published pricing.
    Currently assumes gpt-4.1-mini standard pricing.
    """

    # Prices per 1M tokens (USD)
    PRICES = {
        "gpt-4.1-mini": {
            "input": 0.80,
            "output": 3.20,
        }
    }

    pricing = PRICES.get(model, PRICES["gpt-4.1-mini"])

    cost = (
        (prompt_tokens / 1_000_000) * pricing["input"]
        + (completion_tokens / 1_000_000) * pricing["output"]
    )

    return round(cost, 6)
