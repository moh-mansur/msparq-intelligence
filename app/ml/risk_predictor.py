import numpy as np
from app.models.student_features import StudentFeatures, RiskPrediction

class RiskPredictor:
    """
    Rule-based + ML hybrid risk predictor for secondary school students.
    Adapted from AUN-SRO thesis (Mansur, 2026) for secondary school context.
    
    Phase 1: Rule-based SWRL-style reasoning (no training data needed)
    Phase 2: Random Forest overlay when enough data exists (post-launch)
    """

    # Configurable thresholds (can be overridden per school later)
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

    def predict(self, features: StudentFeatures) -> RiskPrediction:
        """
        Generate risk prediction for a single student.
        Uses SWRL-style rules adapted from AUN-SRO ontology.
        """
        risk_factors = []
        recommendations = []
        risk_points = 0.0

        t = self.thresholds

        # ── RULE 1: Attendance Risk ──────────────────────────────
        if features.attendance_rate < t["attendance_high_risk"]:
            risk_factors.append(
                f"Critical attendance: {features.attendance_rate:.1f}% "
                f"(below {t['attendance_high_risk']}% threshold)"
            )
            recommendations.append("Immediate parent meeting required")
            recommendations.append("Investigate reasons for absence")
            risk_points += 3.0

        elif features.attendance_rate < t["attendance_medium_risk"]:
            risk_factors.append(
                f"Low attendance: {features.attendance_rate:.1f}% "
                f"(below {t['attendance_medium_risk']}% threshold)"
            )
            recommendations.append("Monitor attendance closely this term")
            recommendations.append("Send parent notification about attendance")
            risk_points += 2.0

        elif features.attendance_rate < t["attendance_low_risk"]:
            risk_factors.append(
                f"Attendance needs improvement: {features.attendance_rate:.1f}%"
            )
            risk_points += 1.0

        # ── RULE 2: Academic Performance Risk ────────────────────
        if features.average_final_score < t["score_high_risk"]:
            risk_factors.append(
                f"Critical academic performance: {features.average_final_score:.1f}% average"
            )
            recommendations.append("Immediate academic intervention required")
            recommendations.append("Schedule extra lessons in weak subjects")
            risk_points += 3.0

        elif features.average_final_score < t["score_medium_risk"]:
            risk_factors.append(
                f"Below average performance: {features.average_final_score:.1f}% average"
            )
            recommendations.append("Assign academic support or tutoring")
            risk_points += 2.0

        elif features.average_final_score < t["score_low_risk"]:
            risk_factors.append(
                f"Performance below expected: {features.average_final_score:.1f}% average"
            )
            risk_points += 1.0

        # ── RULE 3: Assignment Completion Risk ───────────────────
        if features.assignment_completion_rate < t["completion_high_risk"]:
            risk_factors.append(
                f"Very low assignment completion: "
                f"{features.assignment_completion_rate:.1f}%"
            )
            recommendations.append("Investigate why student is not submitting work")
            recommendations.append("Parent notification about missing assignments")
            risk_points += 2.0

        elif features.assignment_completion_rate < t["completion_medium_risk"]:
            risk_factors.append(
                f"Low assignment completion: "
                f"{features.assignment_completion_rate:.1f}%"
            )
            recommendations.append("Monitor assignment submission closely")
            risk_points += 1.0

        # ── RULE 4: Subject Failure Count ────────────────────────
        if features.subject_failure_count >= t["failure_count_high"]:
            risk_factors.append(
                f"Failing {features.subject_failure_count} subjects "
                f"(score below 40%)"
            )
            recommendations.append(
                f"Academic review needed — failing {features.subject_failure_count} subjects"
            )
            recommendations.append("Consider subject-specific tutoring")
            risk_points += 2.0

        elif features.subject_failure_count >= t["failure_count_medium"]:
            risk_factors.append(
                f"At risk of failing {features.subject_failure_count} subjects"
            )
            recommendations.append("Extra support needed in failing subjects")
            risk_points += 1.0

        # ── RULE 5: Score Decline Trend ──────────────────────────
        if features.score_trend < t["score_decline_threshold"]:
            risk_factors.append(
                f"Significant score decline from previous term: "
                f"{features.score_trend:+.1f}%"
            )
            recommendations.append(
                "Performance declining — review learning support"
            )
            risk_points += 2.0

        elif features.score_trend < 0:
            risk_factors.append(
                f"Slight score decline from previous term: "
                f"{features.score_trend:+.1f}%"
            )
            risk_points += 0.5

        # ── RULE 6: Attendance Decline Trend ─────────────────────
        if features.attendance_trend < t["attendance_decline_threshold"]:
            risk_factors.append(
                f"Attendance declining significantly: "
                f"{features.attendance_trend:+.1f}% from last term"
            )
            recommendations.append(
                "Attendance deteriorating — urgent parent contact"
            )
            risk_points += 1.5

        # ── RULE 7: Combined Risk (Attendance + Performance) ─────
        if (features.attendance_rate < t["attendance_medium_risk"] and
                features.average_final_score < t["score_medium_risk"]):
            if "Schedule parent-teacher conference" not in recommendations:
                recommendations.append(
                    "Combined attendance and academic risk — "
                    "schedule parent-teacher conference"
                )
            risk_points += 1.0

        # ── DETERMINE RISK LEVEL ─────────────────────────────────
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

        # Normalize risk score to 0.0-1.0
        risk_score = min(1.0, risk_points / 10.0)

        # Remove duplicate recommendations
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
        """Predict risk for a list of students."""
        return [
            self.predict(f) for f in features_list
            if f is not None
        ]