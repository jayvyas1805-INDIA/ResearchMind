"""Pydantic schema for the structured paper summary."""
from pydantic import BaseModel


class SummaryOut(BaseModel):
    research_problem: str
    objective: str
    methodology: str
    models_algorithms: str
    dataset: str
    evaluation_metrics: str
    key_results: str
    limitations: str
    future_work: str
