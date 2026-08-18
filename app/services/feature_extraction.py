from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.student_features import StudentFeatures
from typing import Optional
import pandas as pd

async def extract_student_features(
    db: AsyncSession,
    school_id: str,
    session: str,
    term: str,
    class_id: Optional[str] = None
) -> list[StudentFeatures]:
    """
    Extract features for all students in a school for a given session/term.
    Queries MSparq's existing PostgreSQL tables directly.
    """

    class_filter = "AND s.class_id = :class_id" if class_id else ""

    query = text(f"""
        SELECT
            s.id as student_id,
            s.school_id,
            s.first_name || ' ' || s.last_name as student_name,
            c.name as class_name,
            s.class_id,

            -- Attendance Rate
            COALESCE(attendance_summary.attendance_rate, 0) as attendance_rate,

            -- Average CA Score
            COALESCE(result_summary.average_ca_score, 0) as average_ca_score,

            -- Average Exam Score
            COALESCE(result_summary.average_exam_score, 0) as average_exam_score,

            -- Average Final Score
            COALESCE(result_summary.average_final_score, 0) as average_final_score,

            -- Assessment Activity Rate
            COALESCE(activity_summary.assessment_activity_rate, 0) as assignment_completion_rate,

            -- Subject Failure Count (final_score < 40)
            COALESCE(result_summary.subject_failure_count, 0) as subject_failure_count

        FROM students s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN LATERAL (
            SELECT
                ROUND(
                    100.0 * COUNT(DISTINCT CASE WHEN a.status = 'PRESENT' THEN a.id END) /
                    NULLIF(COUNT(DISTINCT a.id), 0)
                , 2) as attendance_rate
            FROM attendance a
            WHERE a.student_id = s.id
                AND a.school_id = :school_id
                AND a.session = :session
                AND a.term = :term
        ) attendance_summary ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                AVG(r.assignment_score + r.test_score) as average_ca_score,
                AVG(r.exam_score) as average_exam_score,
                AVG(r.final_score) as average_final_score,
                COUNT(DISTINCT CASE WHEN r.final_score < 40 THEN r.subject_id END) as subject_failure_count
            FROM results r
            WHERE r.student_id = s.id
                AND r.school_id = :school_id
                AND r.session = :session
                AND r.term = :term
        ) result_summary ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                ROUND(
                    100.0 * (activity_counts.completed_lms_assignments + activity_counts.completed_assessments + activity_counts.result_activity_count) /
                    NULLIF(activity_counts.total_lms_assignments + activity_counts.total_assessments + activity_counts.result_activity_count, 0)
                , 2) as assessment_activity_rate
            FROM (
                SELECT
                    (
                        SELECT COUNT(DISTINCT asgn.id)
                        FROM assignments asgn
                        WHERE asgn.class_id = s.class_id
                            AND asgn.school_id = :school_id
                            AND asgn.term = :term
                            AND asgn.session = :session
                    ) as total_lms_assignments,
                    (
                        SELECT COUNT(DISTINCT sub.assignment_id)
                        FROM submissions sub
                        JOIN assignments asgn ON asgn.id = sub.assignment_id
                        WHERE asgn.class_id = s.class_id
                            AND asgn.school_id = :school_id
                            AND asgn.term = :term
                            AND asgn.session = :session
                            AND sub.student_id = s.id
                            AND sub.status IN ('SUBMITTED', 'RESUBMITTED', 'GRADED')
                    ) as completed_lms_assignments,
                    (
                        SELECT COUNT(DISTINCT asm.id)
                        FROM assessments asm
                        WHERE asm.class_id = s.class_id
                            AND asm.school_id = :school_id
                            AND asm.term = :term
                            AND asm.session = :session
                            AND asm.category <> 'EXAM'
                            AND (
                                asm.class_group_id IS NULL
                                OR asm.class_group_id = s.class_group_id
                                OR EXISTS (
                                    SELECT 1
                                    FROM assessment_scores existing_score
                                    WHERE existing_score.assessment_id = asm.id
                                        AND existing_score.student_id = s.id
                                )
                            )
                    ) as total_assessments,
                    (
                        SELECT COUNT(DISTINCT score.assessment_id)
                        FROM assessment_scores score
                        JOIN assessments asm ON asm.id = score.assessment_id
                        WHERE asm.class_id = s.class_id
                            AND asm.school_id = :school_id
                            AND asm.term = :term
                            AND asm.session = :session
                            AND asm.category <> 'EXAM'
                            AND score.student_id = s.id
                    ) as completed_assessments,
                    (
                        SELECT COUNT(DISTINCT r.subject_id)
                        FROM results r
                        WHERE r.student_id = s.id
                            AND r.school_id = :school_id
                            AND r.session = :session
                            AND r.term = :term
                            AND r.class_id = s.class_id
                            AND (r.assignment_score + r.test_score) > 0
                    ) as result_activity_count
            ) activity_counts
        ) activity_summary ON TRUE
        WHERE s.school_id = :school_id
            AND s.archived_at IS NULL
            {class_filter}
        ORDER BY c.name, s.last_name
    """)
    params = {
        "school_id": school_id,
        "session": session,
        "term": term,
    }
    if class_id:
        params["class_id"] = class_id

    result = await db.execute(query, params)
    rows = result.fetchall()

    if not rows:
        return []

    # Calculate trends by comparing to previous term
    prev_term_map = await get_previous_term_scores(db, school_id, session, term)

    features = []
    for row in rows:
        student_id = row.student_id
        prev_score = prev_term_map.get(student_id, {}).get("avg_score")
        prev_attendance = prev_term_map.get(student_id, {}).get("attendance_rate")

        score_trend = 0.0
        if prev_score is not None:
            score_trend = float(row.average_final_score) - float(prev_score)

        attendance_trend = 0.0
        if prev_attendance is not None:
            attendance_trend = float(row.attendance_rate) - float(prev_attendance)

        features.append(StudentFeatures(
            student_id=str(row.student_id),
            school_id=str(row.school_id),
            student_name=str(row.student_name),
            class_name=str(row.class_name),
            session=session,
            term=term,
            attendance_rate=float(row.attendance_rate),
            average_ca_score=float(row.average_ca_score),
            average_exam_score=float(row.average_exam_score),
            average_final_score=float(row.average_final_score),
            assignment_completion_rate=float(row.assignment_completion_rate),
            subject_failure_count=int(row.subject_failure_count),
            score_trend=score_trend,
            attendance_trend=attendance_trend,
        ))

    return features


async def get_previous_term_scores(
    db: AsyncSession,
    school_id: str,
    session: str,
    term: str
) -> dict:
    """Get previous term's scores for trend calculation."""

    term_order = {
        "First Term": 1,
        "Second Term": 2,
        "Third Term": 3
    }

    current_term_num = term_order.get(term, 1)

    if current_term_num == 1:
        prev_term = "Third Term"
        year = int(session.split("/")[0])
        prev_session = f"{year - 1}/{year}"
    elif current_term_num == 2:
        prev_term = "First Term"
        prev_session = session
    else:
        prev_term = "Second Term"
        prev_session = session

    query = text("""
        SELECT
            r.student_id,
            AVG(r.final_score) as avg_score,
            COALESCE(
                ROUND(
                    100.0 * COUNT(DISTINCT CASE WHEN a.status = 'PRESENT' THEN a.id END) /
                    NULLIF(COUNT(DISTINCT a.id), 0)
                , 2),
                0
            ) as attendance_rate
        FROM results r
        LEFT JOIN attendance a ON a.student_id = r.student_id
            AND a.school_id = :school_id
            AND a.session = :prev_session
            AND a.term = :prev_term
        WHERE r.school_id = :school_id
            AND r.session = :prev_session
            AND r.term = :prev_term
        GROUP BY r.student_id
    """)

    result = await db.execute(query, {
        "school_id": school_id,
        "prev_session": prev_session,
        "prev_term": prev_term
    })

    rows = result.fetchall()
    return {
        str(row.student_id): {
            "avg_score": float(row.avg_score) if row.avg_score else None,
            "attendance_rate": float(row.attendance_rate) if row.attendance_rate else None
        }
        for row in rows
    }