from pydantic import BaseModel
from typing import Optional

class StudentFeatures(BaseModel):
    student_id: str
    school_id: str
    student_name: str
    class_name: str
    session: str
    term: str
    attendance_rate: float
    average_ca_score: float
    average_exam_score: float
    average_final_score: float
    assignment_completion_rate: float
    subject_failure_count: int
    score_trend: float  # positive = improving, negative = declining
    attendance_trend: float  # positive = improving, negative = declining

class RiskPrediction(BaseModel):
    student_id: str
    student_name: str
    class_name: str
    risk_level: str  # HIGH, MEDIUM, LOW
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    risk_factors: list[str]
    recommendations: list[str]
    features: StudentFeatures

class SchoolRiskSummary(BaseModel):
    school_id: str
    session: str
    term: str
    total_students: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    predictions: list[RiskPrediction]