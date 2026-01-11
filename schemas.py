# schemas.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Evidence(BaseModel):
    quote: str = Field(..., description="Direct quote from JD or source")
    note: str = Field(..., description="Interpretation")

class ScoreItem(BaseModel):
    quality: str
    score: int = Field(..., ge=1, le=5)
    rationale: str
    evidence: List[Evidence] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)

class StrengthGap(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    bridging_language: List[str] = Field(default_factory=list)

class Storyline(BaseModel):
    why_company: List[str] = Field(default_factory=list)
    why_role: List[str] = Field(default_factory=list)
    why_me: List[str] = Field(default_factory=list)
    closing: List[str] = Field(default_factory=list)

class InterviewPrep(BaseModel):
    likely_questions: List[str] = Field(default_factory=list)
    questions_to_ask: List[str] = Field(default_factory=list)

class DownsideCase(BaseModel):
    top_risks: List[str] = Field(default_factory=list)
    what_to_verify: List[str] = Field(default_factory=list)

class JDAnalysis(BaseModel):
    role_summary: str
    extracted_requirements: List[str]
    extracted_responsibilities: List[str]
    scorecard: List[ScoreItem]
    strengths_and_gaps: StrengthGap
    storyline: Storyline
    interview_prep: InterviewPrep
    downside_case: DownsideCase