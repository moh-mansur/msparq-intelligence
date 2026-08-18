from owlready2 import *
from app.models.student_features import StudentFeatures, RiskPrediction
import os

# Create the MSparq Secondary School Retention Ontology (MSparq-SRO)
# Adapted from AUN-SRO (Mansur, 2026) for Nigerian secondary schools

def create_msparq_ontology():
    """Create and return the MSparq-SRO ontology."""
    
    onto = get_ontology("http://msparq.com/ontology/msparq-sro#")
    
    with onto:
        
        # ── CORE CLASSES ──────────────────────────────────────────
        
        class Student(Thing):
            pass
        
        class Class(Thing):
            pass
        
        class Subject(Thing):
            pass
        
        class Teacher(Thing):
            pass
        
        class Assessment(Thing):
            pass
        
        class Attendance(Thing):
            pass
        
        class Assignment(Thing):
            pass
        
        class Performance(Thing):
            pass
        
        class Risk(Thing):
            pass
        
        class Intervention(Thing):
            pass
        
        class Recommendation(Thing):
            pass
        
        # ── RISK SUBCLASSES ───────────────────────────────────────
        
        class HighRisk(Risk):
            pass
        
        class MediumRisk(Risk):
            pass
        
        class LowRisk(Risk):
            pass
        
        class NoRisk(Risk):
            pass
        
        # ── INTERVENTION SUBCLASSES ───────────────────────────────
        
        class ParentMeeting(Intervention):
            pass
        
        class AcademicTutoring(Intervention):
            pass
        
        class AttendanceMonitoring(Intervention):
            pass
        
        class SubjectSupport(Intervention):
            pass
        
        class CounsellingSession(Intervention):
            pass
        
        # ── OBJECT PROPERTIES ─────────────────────────────────────
        
        class enrolledIn(Student >> Class):
            pass
        
        class taughtBy(Class >> Teacher):
            pass
        
        class hasAttendance(Student >> Attendance):
            pass
        
        class hasAssessment(Student >> Assessment):
            pass
        
        class hasAssignment(Student >> Assignment):
            pass
        
        class hasPerformance(Student >> Performance):
            pass
        
        class hasRisk(Student >> Risk):
            pass
        
        class requiresIntervention(Student >> Intervention):
            pass
        
        class hasRecommendation(Student >> Recommendation):
            pass
        
        class generatedFrom(Recommendation >> Risk):
            pass
        
        # ── DATA PROPERTIES ───────────────────────────────────────
        
        class studentId(Student >> str):
            pass
        
        class studentName(Student >> str):
            pass
        
        class className(Student >> str):
            pass
        
        class attendanceRate(Student >> float):
            pass
        
        class averageFinalScore(Student >> float):
            pass
        
        class averageCAScore(Student >> float):
            pass
        
        class averageExamScore(Student >> float):
            pass
        
        class assignmentCompletionRate(Student >> float):
            pass
        
        class subjectFailureCount(Student >> int):
            pass
        
        class scoreTrend(Student >> float):
            pass
        
        class attendanceTrend(Student >> float):
            pass
        
        class riskLevel(Student >> str):
            pass
        
        class riskScore(Student >> float):
            pass
    
    return onto


def apply_swrl_rules(
    onto,
    features: StudentFeatures,
    thresholds: dict
) -> tuple[list[str], list[str], float]:
    """
    Apply SWRL-style reasoning rules to determine risk factors
    and interventions for a student.
    
    Adapted from AUN-SRO SWRL rules for secondary school context.
    Returns: (risk_factors, recommendations, risk_points)
    """
    
    risk_factors = []
    recommendations = []
    interventions = set()
    risk_points = 0.0
    
    t = thresholds
    
    # ── RULE 1: Critical Attendance ───────────────────────────────
    # Student(?s) ∧ hasAttendanceRate(?s, ?r) ∧ lessThan(?r, 70)
    # → hasRisk(?s, HighRisk) ∧ requiresIntervention(?s, ParentMeeting)
    if features.attendance_rate < t["attendance_high_risk"]:
        risk_factors.append(
            f"Critical attendance rate: {features.attendance_rate:.1f}% "
            f"— below {t['attendance_high_risk']}% minimum threshold"
        )
        interventions.add("ParentMeeting")
        interventions.add("AttendanceMonitoring")
        risk_points += 3.0
    
    # ── RULE 2: Low Attendance ────────────────────────────────────
    # Student(?s) ∧ hasAttendanceRate(?s, ?r) ∧ lessThan(?r, 80)
    # → hasRisk(?s, MediumRisk) ∧ requiresIntervention(?s, AttendanceMonitoring)
    elif features.attendance_rate < t["attendance_medium_risk"]:
        risk_factors.append(
            f"Low attendance rate: {features.attendance_rate:.1f}% "
            f"— below {t['attendance_medium_risk']}% threshold"
        )
        interventions.add("AttendanceMonitoring")
        risk_points += 2.0
    
    elif features.attendance_rate < t["attendance_low_risk"]:
        risk_factors.append(
            f"Attendance below expected: {features.attendance_rate:.1f}%"
        )
        risk_points += 1.0
    
    # ── RULE 3: Critical Academic Performance ─────────────────────
    # Student(?s) ∧ hasAverageFinalScore(?s, ?sc) ∧ lessThan(?sc, 40)
    # → hasRisk(?s, HighRisk) ∧ requiresIntervention(?s, AcademicTutoring)
    if features.average_final_score < t["score_high_risk"]:
        risk_factors.append(
            f"Critical academic performance: "
            f"{features.average_final_score:.1f}% average final score"
        )
        interventions.add("AcademicTutoring")
        interventions.add("SubjectSupport")
        risk_points += 3.0
    
    elif features.average_final_score < t["score_medium_risk"]:
        risk_factors.append(
            f"Below average academic performance: "
            f"{features.average_final_score:.1f}% average"
        )
        interventions.add("AcademicTutoring")
        risk_points += 2.0
    
    elif features.average_final_score < t["score_low_risk"]:
        risk_factors.append(
            f"Performance below expected level: "
            f"{features.average_final_score:.1f}% average"
        )
        risk_points += 1.0
    
    # ── RULE 4: Assessment Activity ─────────────────────────────
    # Student(?s) ∧ hasAssessmentActivityRate(?s, ?cr) ∧ lessThan(?cr, 60)
    # → hasRisk(?s, MediumRisk) ∧ requiresIntervention(?s, ParentMeeting)
    if features.assignment_completion_rate < t["completion_high_risk"]:
        risk_factors.append(
            f"Very low assessment activity: "
            f"{features.assignment_completion_rate:.1f}% of expected assessments completed"
        )
        interventions.add("ParentMeeting")
        risk_points += 2.0
    
    elif features.assignment_completion_rate < t["completion_medium_risk"]:
        risk_factors.append(
            f"Low assessment activity rate: "
            f"{features.assignment_completion_rate:.1f}%"
        )
        risk_points += 1.0
    
    # ── RULE 5: Multiple Subject Failures ─────────────────────────
    # Student(?s) ∧ hasSubjectFailureCount(?s, ?fc) ∧ greaterThan(?fc, 2)
    # → hasRisk(?s, HighRisk) ∧ requiresIntervention(?s, SubjectSupport)
    if features.subject_failure_count >= t["failure_count_high"]:
        risk_factors.append(
            f"Failing {features.subject_failure_count} subjects "
            f"with scores below 40%"
        )
        interventions.add("SubjectSupport")
        interventions.add("AcademicTutoring")
        risk_points += 2.0
    
    elif features.subject_failure_count >= t["failure_count_medium"]:
        risk_factors.append(
            f"At risk of failing {features.subject_failure_count} subjects"
        )
        interventions.add("SubjectSupport")
        risk_points += 1.0
    
    # ── RULE 6: Score Decline Trend ───────────────────────────────
    # Student(?s) ∧ hasScoreTrend(?s, ?st) ∧ lessThan(?st, -10)
    # → hasRisk(?s, MediumRisk) ∧ requiresIntervention(?s, AcademicTutoring)
    if features.score_trend < t["score_decline_threshold"]:
        risk_factors.append(
            f"Significant academic decline from previous term: "
            f"{features.score_trend:+.1f}% change"
        )
        interventions.add("AcademicTutoring")
        risk_points += 2.0
    
    elif features.score_trend < 0:
        risk_factors.append(
            f"Slight academic decline from previous term: "
            f"{features.score_trend:+.1f}% change"
        )
        risk_points += 0.5
    
    # ── RULE 7: Attendance Decline Trend ──────────────────────────
    # Student(?s) ∧ hasAttendanceTrend(?s, ?at) ∧ lessThan(?at, -10)
    # → hasRisk(?s, MediumRisk) ∧ requiresIntervention(?s, AttendanceMonitoring)
    if features.attendance_trend < t["attendance_decline_threshold"]:
        risk_factors.append(
            f"Attendance significantly declining: "
            f"{features.attendance_trend:+.1f}% from last term"
        )
        interventions.add("AttendanceMonitoring")
        interventions.add("ParentMeeting")
        risk_points += 1.5
    
    # ── RULE 8: Combined Attendance + Performance Risk ────────────
    # Student(?s) ∧ hasAttendanceRate(?s, ?r) ∧ lessThan(?r, 80)
    # ∧ hasAverageFinalScore(?s, ?sc) ∧ lessThan(?sc, 50)
    # → hasRisk(?s, HighRisk) ∧ requiresIntervention(?s, ParentMeeting)
    # ∧ requiresIntervention(?s, CounsellingSession)
    if (features.attendance_rate < t["attendance_medium_risk"] and
            features.average_final_score < t["score_medium_risk"]):
        risk_factors.append(
            "Combined attendance and academic risk detected"
        )
        interventions.add("ParentMeeting")
        interventions.add("CounsellingSession")
        risk_points += 1.0
    
    # ── MAP INTERVENTIONS TO RECOMMENDATIONS ──────────────────────
    intervention_map = {
        "ParentMeeting": "Schedule urgent parent-teacher meeting",
        "AcademicTutoring": "Enrol student in academic tutoring programme",
        "AttendanceMonitoring": "Place student on attendance monitoring plan",
        "SubjectSupport": "Provide subject-specific academic support",
        "CounsellingSession": "Refer student for counselling session",
    }
    
    recommendations = [
        intervention_map[i]
        for i in intervention_map
        if i in interventions
    ]
    
    return risk_factors, recommendations, risk_points


# Initialize ontology once at module level
_ontology = None

def get_ontology_instance():
    global _ontology
    if _ontology is None:
        _ontology = create_msparq_ontology()
    return _ontology