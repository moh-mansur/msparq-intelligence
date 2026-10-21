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

        risk_points = self._apply_attendance_only_bounds(features, risk_points)

        # Determine risk level from points
        if risk_points >= 5.0:
            risk_level = "HIGH"
        elif risk_points >= 2.5:
            risk_level = "MEDIUM"
        elif risk_points >= 1.0:
            risk_level = "LOW"
        else:
            risk_level = "NONE"
            risk_factors = []
            recommendations = []

        risk_score = min(1.0, risk_points / 10.0)
        confidence = self._data_completeness(features)
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

    # Attendance below this can still reach HIGH on its own. Above it, a pupil
    # with no marks entered yet is capped at MEDIUM: poor attendance is worth
    # flagging, but calling a pupil high risk before a single mark exists is a
    # judgement the data cannot support.
    ATTENDANCE_ALONE_HIGH_RISK = 50.0

    # Just under the 5.0 HIGH threshold, so a capped pupil lands at the top of
    # MEDIUM rather than having their score flattened.
    ATTENDANCE_ALONE_CAP = 4.9

    # The HIGH threshold exactly: enough to flag, without inflating the score
    # beyond what one signal can justify.
    ATTENDANCE_ALONE_HIGH_POINTS = 5.0

    def _apply_attendance_only_bounds(
        self, features: StudentFeatures, risk_points: float
    ) -> float:
        """
        Bound a pupil who has attendance but no academic data yet.

        Early in a term nothing has been entered, so attendance is all there
        is. That is enough to say "watch this one" and not enough to say
        "urgent", so the reading is held below HIGH.

        Attendance under 50% is the exception and goes the other way: a pupil
        missing half of school is high risk whatever the mark book says, and
        the attendance rules alone only reach 3.0 points, which is MEDIUM. So
        that case is lifted to HIGH rather than merely left uncapped.

        A pupil with no register either is not bounded upward at all - their
        attendance_rate is 0.0 because nothing was recorded, not because they
        never came.
        """
        has_academic_data = (
            features.result_count > 0 or features.assessment_activity_total > 0
        )

        if has_academic_data:
            return risk_points

        if (
            features.attendance_days_recorded > 0
            and features.attendance_rate < self.ATTENDANCE_ALONE_HIGH_RISK
        ):
            return max(risk_points, self.ATTENDANCE_ALONE_HIGH_POINTS)

        return min(risk_points, self.ATTENDANCE_ALONE_CAP)

    def _data_completeness(self, features: StudentFeatures) -> float:
        """
        How much of the evidence this reading wants is actually present.

        This is what the card calls confidence, and it used to be derived
        purely from the risk score - which carried no information the score did
        not already carry, and was not even ordered sensibly: a pupil at 20%
        risk showed 70% confidence while one at 30% showed 63%, and a pupil
        with no risk factors at all showed 90%, higher than almost everyone.

        It now answers the only question a teacher can act on: how much do we
        actually know about this pupil? A reading built on a full register and
        a full mark book deserves more weight than one built on three days of
        attendance, and now says so.

        The weights follow how much each source tells us. A full register is
        taken as twenty days and a full mark book as five subjects; past those
        the extra data adds little.
        """
        attendance_share = 0.35 * min(1.0, features.attendance_days_recorded / 20.0)
        results_share = 0.35 * min(1.0, features.result_count / 5.0)
        activity_share = 0.20 if features.assessment_activity_total > 0 else 0.0
        trend_share = 0.10 if features.has_previous_term else 0.0
        completeness = (
            attendance_share + results_share + activity_share + trend_share
        )

        # Floored rather than allowed to reach zero: the reading is thin, not
        # absent, and a flat 0% reads as a broken number rather than a weak one.
        return max(0.15, min(1.0, completeness))

    def predict_batch(
        self, features_list: list[StudentFeatures]
    ) -> list[RiskPrediction]:
        return [self.predict(f) for f in features_list if f is not None]