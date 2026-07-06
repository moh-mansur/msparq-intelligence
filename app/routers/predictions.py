from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.feature_extraction import extract_student_features
from app.ml.risk_predictor import RiskPredictor
from app.models.student_features import SchoolRiskSummary, RiskPrediction
from typing import Optional

router = APIRouter(prefix="/predictions", tags=["predictions"])
predictor = RiskPredictor()

@router.get("/school/{school_id}", response_model=SchoolRiskSummary)
async def get_school_predictions(
    school_id: str,
    session: str = Query(..., description="Academic session e.g. 2026/2027"),
    term: str = Query(..., description="Term e.g. First Term"),
    class_id: Optional[str] = Query(None, description="Filter by class"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get risk predictions for all students in a school.
    Returns HIGH, MEDIUM, LOW risk classifications with
    explanations and recommendations.
    """
    try:
        features_list = await extract_student_features(
            db, school_id, session, term, class_id
        )

        if not features_list:
            return SchoolRiskSummary(
                school_id=school_id,
                session=session,
                term=term,
                total_students=0,
                high_risk_count=0,
                medium_risk_count=0,
                low_risk_count=0,
                predictions=[]
            )

        predictions = predictor.predict_batch(features_list)

        # Filter out NONE risk (no risk factors)
        at_risk = [p for p in predictions if p.risk_level != "NONE"]

        # Sort by risk level: HIGH first, then MEDIUM, then LOW
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        at_risk.sort(key=lambda p: (risk_order.get(p.risk_level, 3), -p.risk_score))

        return SchoolRiskSummary(
            school_id=school_id,
            session=session,
            term=term,
            total_students=len(predictions),
            high_risk_count=sum(1 for p in at_risk if p.risk_level == "HIGH"),
            medium_risk_count=sum(1 for p in at_risk if p.risk_level == "MEDIUM"),
            low_risk_count=sum(1 for p in at_risk if p.risk_level == "LOW"),
            predictions=at_risk
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{student_id}", response_model=RiskPrediction)
async def get_student_prediction(
    student_id: str,
    school_id: str = Query(...),
    session: str = Query(...),
    term: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get risk prediction for a single student."""
    try:
        features_list = await extract_student_features(
            db, school_id, session, term
        )

        student_features = next(
            (f for f in features_list if f.student_id == student_id),
            None
        )

        if not student_features:
            raise HTTPException(
                status_code=404,
                detail="Student not found or no data for this term"
            )

        return predictor.predict(student_features)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))