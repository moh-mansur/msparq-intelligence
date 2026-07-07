import numpy as np
from app.models.student_features import StudentFeatures, RiskPrediction
from app.ontology.msparq_sro import get_ontology_instance, apply_swrl_rules

class RiskPredictor:
    """
    Hybrid ontology + rule-based risk predictor for secondary school students.
    Uses MSparq-SRO ontology with SWRL-style reasoning.
    Adapted from AUN-SRO thesis (Mansur, 2026) for secondary school context.
    """

    DEFAULT_THRESHOLDS = {
        "attendance_high_risk": 70.0,
        "attendance_medium_risk": 80.0,
        "attendance_low_risk": 90.0,
        "score_high_risk": 40.0,
        "score_medium_risk": 50.0,
        "score_low_risk": 60.0,
        "completion_high_risk": 50.0,
        "completion_medium_risk": 65.0,
        "failure_count_high": 3,
        "failure_count_medium": 2,
        "score_decline_threshold": -10.0,
        "attendance_decline_threshold": -10.0,
    }

    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self.onto = get_ontology_instance()

    def predict(self, features: StudentFeatures) -> RiskPrediction:
        """
        Generate risk prediction using MSparq-SRO ontology reasoning.
        """
        # Apply SWRL-style ontology rules
        risk_factors, recommendations, risk_points = apply_swrl_rules(
            self.onto, features, self.thresholds
        )

        # Determine risk level from points
        if risk_points >= 5.0:
            risk_level = "HIGH"
            confidence = min(0.95, 0.70 + (risk_points - 5.0) * 0.05)
        elif risk_points >= 2.5:
            risk_level = "MEDIUM"
            confidence = min(0.85, 0.60 + (risk_points - 2.5) * 0.05)
        elif risk_points >= 1.0:
            risk_level = "LOW"
            confidence = 0.60 + risk_points * 0.05
        else:
            risk_level = "NONE"
            confidence = 0.90
            risk_factors = []
            recommendations = []

        risk_score = min(1.0, risk_points / 10.0)
        recommendations = list(dict.fromkeys(recommendations))

        return RiskPrediction(
            student_id=features.student_id,
            student_name=features.student_name,
            class_name=features.class_name,
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            confidence=round(confidence, 3),
            risk_factors=risk_factors,
            recommendations=recommendations,
            features=features,
        )

    def predict_batch(
        self, features_list: list[StudentFeatures]
    ) -> list[RiskPrediction]:
        return [self.predict(f) for f in features_list if f is not None]