"""
Database model for a single extracted numeric result claim, e.g.
"LSTM achieved 90% accuracy on the emotion dataset" -> model=LSTM,
dataset=<paper's dataset>, metric=Accuracy, value=90.0.

This is what powers the cross-paper leaderboard — a structured fact
extracted from unstructured text, not a generated summary.
"""
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.core.database import Base


class ResultClaim(Base):
    __tablename__ = "result_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)

    paper_id = Column(String, ForeignKey("papers.id"), nullable=False, index=True)

    model_name = Column(String, nullable=True, index=True)    # e.g. "LSTM" — nullable if not identifiable in-sentence
    dataset_name = Column(String, nullable=True, index=True)  # e.g. "SQuAD"
    metric_name = Column(String, nullable=False, index=True)  # e.g. "Accuracy"

    value_text = Column(String, nullable=False)   # raw matched text, e.g. "90%" or "0.90"
    value = Column(Float, nullable=True)           # parsed numeric value, normalized to a 0-100 scale where possible

    sentence = Column(Text, nullable=False)  # the sentence this claim was extracted from, for verification/citation
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
