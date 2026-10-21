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

    # How much evidence sits behind the rates above.
    #
    # Every rate is COALESCEd to 0 when there is nothing to average, so a 0
    # means either "scored nothing" or "nothing has been entered yet" - and the
    # rules cannot tell those apart without these counts. A pupil whose teacher
    # has not entered marks yet must not read as a pupil who scored zero.
    #
    # Defaulted so an older caller constructing StudentFeatures by hand still
    # works; the extractor always sets them.
    attendance_days_recorded: int = 0
    result_count: int = 0
    assessment_activity_total: int = 0
    has_previous_term: bool = False

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