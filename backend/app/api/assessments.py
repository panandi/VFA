from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime

from app.core.database import get_db
from app.services.pdf_report import generate_assessment_pdf
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.assessment import (
    VendorAssessment,
    FinancialStatement,
    ExtractedFinancialData,
    QualitativeResponse,
    RiskAssessment,
    Recommendation,
    AssessmentStatus
)
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentListResponse,
    ExtractedDataUpdate,
    QualitativeResponseCreate,
    QualitativeResponseUpdate
)
from app.services.financial_calculator import FinancialCalculator
# OPTIMIZED: Using new extraction agent with 3-5x speed improvement and 10x cost reduction
from app.agents.extraction_agent_optimized import run_extraction_pipeline, extraction_progress
from app.agents.recommendation_agent import generate_recommendation

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new vendor assessment."""
    assessment = VendorAssessment(
        vendor_name=assessment_data.vendor_name,
        vendor_registration_number=assessment_data.vendor_registration_number,
        created_by=current_user.id,
        status=AssessmentStatus.DRAFT.value,
        current_step=1
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Initialize default qualitative questions
    default_questions = [
        ("Q1", "Past working relationship with the Singtel Group?"),
        ("Q2", "Any platforms or systems supported by vendor?"),
        ("Q3", "Any legal disputes?"),
        ("Q4", "Any material corporate governance issues? (Examples: Fraud, conflict of interest, etc.)"),
        ("Q5", "Any qualified audit opinions?"),
        ("Q6", "Any going concern or insolvency risk identified?"),
        ("Q7", "Experience with major projects?"),
        ("Q8", "Any withholding tax? (usually applicable for foreign companies)"),
        ("Q9", "Any support from parent or holding or related company?"),
        ("Q10", "Please elaborate on related party transactions/loans, guarantee and any contingent liabilities."),
        ("Q11", "Any customer/territory/product dominance from segmentation of operations?"),
    ]

    for q_id, q_text in default_questions:
        question = QualitativeResponse(
            assessment_id=assessment.id,
            question_id=q_id,
            question_text=q_text
        )
        db.add(question)

    db.commit()
    db.refresh(assessment)

    return assessment


@router.get("", response_model=List[AssessmentListResponse])
async def list_assessments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all assessments for the current user."""
    assessments = (
        db.query(VendorAssessment)
        .filter(VendorAssessment.created_by == current_user.id)
        .order_by(VendorAssessment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return assessments


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific assessment by ID."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    return assessment


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: int,
    assessment_data: AssessmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an assessment."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    update_data = assessment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assessment, field, value)

    db.commit()
    db.refresh(assessment)

    return assessment


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an assessment."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    db.delete(assessment)
    db.commit()


# File Upload
@router.post("/{assessment_id}/upload")
async def upload_financial_statement(
    assessment_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a financial statement PDF."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(assessment_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create database record
    statement = FinancialStatement(
        assessment_id=assessment_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        processing_status="pending"
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)

    # Trigger extraction in background
    background_tasks.add_task(
        run_extraction_pipeline,
        assessment_id=assessment_id,
        statement_id=statement.id,
        file_path=file_path
    )

    return {
        "message": "File uploaded successfully",
        "statement_id": statement.id,
        "filename": file.filename
    }


# Check extraction status
@router.get("/{assessment_id}/extraction-status")
async def get_extraction_status(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of PDF extraction for an assessment."""
    import time

    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    statements = (
        db.query(FinancialStatement)
        .filter(FinancialStatement.assessment_id == assessment_id)
        .all()
    )

    total = len(statements)
    processed = sum(1 for s in statements if s.is_processed)
    has_errors = any(s.processing_status == "error" for s in statements)

    # Check if any data was extracted
    extracted_count = (
        db.query(ExtractedFinancialData)
        .filter(ExtractedFinancialData.assessment_id == assessment_id)
        .count()
    )

    # Get real-time progress from extraction agent
    progress_info = extraction_progress.get(assessment_id, {})
    current_page = progress_info.get('current_page', 0)
    total_pages = progress_info.get('total_pages', 0)
    statement_type = progress_info.get('statement_type', '')
    stage = progress_info.get('stage', '')

    # Calculate time remaining
    time_remaining_seconds = None
    if progress_info and current_page > 0 and total_pages > 0:
        start_time = progress_info.get('start_time', time.time())
        elapsed = time.time() - start_time
        progress_ratio = current_page / total_pages
        if progress_ratio > 0:
            estimated_total_time = elapsed / progress_ratio
            time_remaining_seconds = max(0, int(estimated_total_time - elapsed))

    return {
        "total_files": total,
        "processed_files": processed,
        "is_complete": processed == total and total > 0,
        "has_errors": has_errors,
        "extracted_years": extracted_count,
        "status": "complete" if (processed == total and total > 0) else "processing" if total > 0 else "pending",
        "current_page": current_page,
        "total_pages": total_pages,
        "statement_type": statement_type,
        "stage": stage,
        "time_remaining_seconds": time_remaining_seconds
    }


# Extraction endpoint
@router.post("/{assessment_id}/extract")
async def trigger_extraction(
    assessment_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger extraction for all pending files."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    pending_statements = (
        db.query(FinancialStatement)
        .filter(
            FinancialStatement.assessment_id == assessment_id,
            FinancialStatement.is_processed == False
        )
        .all()
    )

    for statement in pending_statements:
        background_tasks.add_task(
            run_extraction_pipeline,
            assessment_id=assessment_id,
            statement_id=statement.id,
            file_path=statement.file_path
        )

    return {"message": f"Extraction triggered for {len(pending_statements)} files"}


# Update extracted financial data
@router.put("/{assessment_id}/financial-data/{data_id}")
async def update_financial_data(
    assessment_id: int,
    data_id: int,
    data: ExtractedDataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update extracted financial data (for manual corrections)."""
    extracted_data = (
        db.query(ExtractedFinancialData)
        .join(VendorAssessment)
        .filter(
            ExtractedFinancialData.id == data_id,
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not extracted_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial data not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(extracted_data, field, value)

    db.commit()
    db.refresh(extracted_data)

    return extracted_data


# Confirm all financial data
@router.post("/{assessment_id}/confirm-data")
async def confirm_financial_data(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm all extracted financial data and move to step 2."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Mark all extracted data as confirmed
    db.query(ExtractedFinancialData).filter(
        ExtractedFinancialData.assessment_id == assessment_id
    ).update({"is_confirmed": True})

    # Update assessment status
    assessment.status = AssessmentStatus.STEP2_COMPLETE.value
    assessment.current_step = 3

    db.commit()

    return {"message": "Financial data confirmed", "current_step": 3}


# Update qualitative responses
@router.put("/{assessment_id}/qualitative/{question_id}")
async def update_qualitative_response(
    assessment_id: int,
    question_id: str,
    response_data: QualitativeResponseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a qualitative questionnaire response."""
    response = (
        db.query(QualitativeResponse)
        .join(VendorAssessment)
        .filter(
            QualitativeResponse.question_id == question_id,
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    update_data = response_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(response, field, value)

    db.commit()
    db.refresh(response)

    return response


# Calculate financial ratios
@router.post("/{assessment_id}/calculate")
async def calculate_ratios(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate financial ratios and Z-score."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Get the most recent confirmed financial data
    latest_data = (
        db.query(ExtractedFinancialData)
        .filter(
            ExtractedFinancialData.assessment_id == assessment_id,
            ExtractedFinancialData.is_confirmed == True
        )
        .order_by(ExtractedFinancialData.fiscal_year.desc())
        .first()
    )

    if not latest_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed financial data available"
        )

    # Calculate ratios
    calculator = FinancialCalculator(latest_data)
    ratios = calculator.calculate_all_ratios()
    z_score_result = calculator.calculate_z_score()

    # Create or update risk assessment
    risk_assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.assessment_id == assessment_id)
        .first()
    )

    if not risk_assessment:
        risk_assessment = RiskAssessment(assessment_id=assessment_id)
        db.add(risk_assessment)

    # Update risk assessment with calculated values
    risk_assessment.z_score = z_score_result["z_score"]
    risk_assessment.z_score_x1 = z_score_result["components"]["x1"]
    risk_assessment.z_score_x2 = z_score_result["components"]["x2"]
    risk_assessment.z_score_x3 = z_score_result["components"]["x3"]
    risk_assessment.z_score_x4 = z_score_result["components"]["x4"]
    risk_assessment.z_score_x5 = z_score_result["components"]["x5"]
    risk_assessment.risk_level = z_score_result["risk_level"]

    # Liquidity ratios
    risk_assessment.current_ratio = ratios["liquidity"]["current_ratio"]
    risk_assessment.quick_ratio = ratios["liquidity"]["quick_ratio"]
    risk_assessment.cash_ratio = ratios["liquidity"]["cash_ratio"]

    # Profitability ratios
    risk_assessment.gross_margin = ratios["profitability"]["gross_margin"]
    risk_assessment.operating_margin = ratios["profitability"]["operating_margin"]
    risk_assessment.net_margin = ratios["profitability"]["net_margin"]
    risk_assessment.roa = ratios["profitability"]["roa"]
    risk_assessment.roe = ratios["profitability"]["roe"]

    # Leverage ratios
    risk_assessment.debt_to_equity = ratios["leverage"]["debt_to_equity"]
    risk_assessment.debt_to_assets = ratios["leverage"]["debt_to_assets"]
    risk_assessment.interest_coverage = ratios["leverage"]["interest_coverage"]

    # Efficiency ratios
    risk_assessment.asset_turnover = ratios["efficiency"]["asset_turnover"]
    risk_assessment.inventory_turnover = ratios["efficiency"]["inventory_turnover"]
    risk_assessment.receivables_turnover = ratios["efficiency"]["receivables_turnover"]

    risk_assessment.fiscal_year_used = latest_data.fiscal_year
    risk_assessment.calculated_at = datetime.utcnow()

    # Update assessment status
    assessment.status = AssessmentStatus.STEP3_COMPLETE.value
    assessment.current_step = 4

    db.commit()
    db.refresh(risk_assessment)

    return risk_assessment


# Generate AI recommendation
@router.post("/{assessment_id}/recommend")
async def create_recommendation(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI recommendation based on all assessment data."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    if not assessment.risk_assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk assessment must be calculated first"
        )

    # Generate recommendation using AI agent
    recommendation_data = await generate_recommendation(
        assessment=assessment,
        risk_assessment=assessment.risk_assessment,
        qualitative_responses=assessment.qualitative_responses
    )

    # Create or update recommendation
    recommendation = (
        db.query(Recommendation)
        .filter(Recommendation.assessment_id == assessment_id)
        .first()
    )

    if not recommendation:
        recommendation = Recommendation(assessment_id=assessment_id)
        db.add(recommendation)

    recommendation.recommendation_type = recommendation_data["recommendation_type"]
    recommendation.recommendation_text = recommendation_data["recommendation_text"]
    recommendation.supporting_factors = recommendation_data["supporting_factors"]
    recommendation.summary = recommendation_data["summary"]
    recommendation.model_used = settings.OPENAI_MODEL
    recommendation.generated_at = datetime.utcnow()

    # Update assessment status
    assessment.status = AssessmentStatus.COMPLETED.value

    db.commit()
    db.refresh(recommendation)

    return recommendation


# Sign off assessment
@router.post("/{assessment_id}/sign-off")
async def sign_off_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sign off on the assessment and finalize."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    if not assessment.recommendation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommendation must be generated first"
        )

    # Update recommendation sign-off
    assessment.recommendation.is_signed_off = True
    assessment.recommendation.signed_off_by = current_user.id
    assessment.recommendation.signed_off_at = datetime.utcnow()

    # Update assessment status
    assessment.status = AssessmentStatus.SIGNED_OFF.value
    assessment.completed_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Assessment signed off successfully",
        "assessment_id": assessment_id,
        "signed_off_at": assessment.recommendation.signed_off_at
    }


# Download PDF report
@router.get("/{assessment_id}/download-pdf")
async def download_assessment_pdf(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the assessment as a PDF report."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.created_by == current_user.id
        )
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    # Generate PDF
    pdf_buffer = generate_assessment_pdf(assessment)

    # Create filename
    vendor_name = assessment.vendor_name.replace(" ", "_") if assessment.vendor_name else "assessment"
    filename = f"VFA_Report_{vendor_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
