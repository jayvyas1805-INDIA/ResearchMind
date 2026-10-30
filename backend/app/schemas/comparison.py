"""Pydantic schemas for paper comparison."""
from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    paper_id_1: str
    paper_id_2: str


class PaperBriefOut(BaseModel):
    id: str
    title: str
    methodology: str
    dataset: str
    models: str
    metrics: str
    results: str
    limitations: str


class ComparisonOut(BaseModel):
    paper1: PaperBriefOut
    paper2: PaperBriefOut
    similarities: str
    differences: str
    methodology_comparison: str
    dataset_comparison: str
    model_comparison: str
    result_comparison: str
    generation_mode: str = "llm"
