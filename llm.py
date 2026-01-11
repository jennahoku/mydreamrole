# llm.py
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from schemas import JDAnalysis

load_dotenv()

def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)

def default_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

DAY0_SYSTEM = """You are an assistant that analyzes job descriptions for fit, risks, and interview prep.
You must return valid JSON that matches the provided schema. No markdown. No extra keys.
Be specific, avoid fluff, and include evidence quotes from the JD.
If information is missing, put it in unknowns / what_to_verify rather than guessing.
"""

def run_day0_analysis(
    jd_text: str,
    company: str,
    role_title: str,
    user_rubric: str,
    user_profile: str,
    model: str | None = None
) -> tuple[dict, str]:
    client = get_client()
    model = model or default_model()

    schema_hint = JDAnalysis.model_json_schema()

    user_prompt = f"""
Company: {company}
Role Title: {role_title}

USER RUBRIC (core qualities to score 1-5):
{user_rubric}

USER PROFILE (resume summary, strengths, story bank):
{user_profile}

JOB DESCRIPTION (raw):
{jd_text}

Return JSON ONLY matching this JSON Schema:
{json.dumps(schema_hint)}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DAY0_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content
    data = json.loads(content)

    # Validate to ensure it matches schema
    try:
        JDAnalysis.model_validate(data)
    except ValidationError as e:
        raise RuntimeError(f"Model returned invalid schema: {e}")

    return data, model