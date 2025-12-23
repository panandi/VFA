from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime

from app.core.database import get_db
from app.services.pdf_report import generate_assessment_pdf
from app.services.excel_report import generate_assessment_excel
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
from app.models.financial_line_item import FinancialLineItem
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentUpdate,
    AssessmentResponse,
    AssessmentListResponse,
    ExtractedDataUpdate,
    QualitativeResponseCreate,
    QualitativeResponseUpdate
)
from app.services.financial_calculator import FinancialCalculator, CompanyType
# Extraction agents - v2 is the new default with OCR support
from app.agents.extraction_agent_optimized import run_extraction_pipeline as run_extraction_v1
from app.agents.extraction_agent_optimized import extraction_progress as extraction_progress_v1
from app.agents.extraction_agent_v2 import run_extraction_pipeline_v2, extraction_progress as extraction_progress_v2
from app.agents.camelot_integration_agent import run_camelot_extraction
from app.agents.hybrid_extraction_agent import run_hybrid_extraction
from app.agents.recommendation_agent import generate_recommendation

# Use Hybrid extraction by default (Tries Camelot first, falls back to LLM)
USE_HYBRID = True  # Best of both: Camelot for text PDFs, LLM for image PDFs
USE_CAMELOT = False
USE_EXTRACTION_V2 = False

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
    if USE_HYBRID:
        # Use Hybrid extraction (Tries Camelot first, falls back to LLM)
        # - Text PDFs → Camelot → Hierarchical data
        # - Image PDFs → LLM → Flat data
        background_tasks.add_task(
            run_hybrid_extraction,
            assessment_id=assessment_id,
            statement_id=statement.id,
            file_path=file_path
        )
    elif USE_CAMELOT:
        # Use Camelot extraction only (No LLM, extracts ALL data)
        background_tasks.add_task(
            run_camelot_extraction,
            assessment_id=assessment_id,
            statement_id=statement.id,
            file_path=file_path
        )
    elif USE_EXTRACTION_V2:
        # Use LLM v2 extraction (with OCR support)
        background_tasks.add_task(
            run_extraction_pipeline_v2,
            assessment_id=assessment_id,
            statement_id=statement.id,
            file_path=file_path
        )
    else:
        # Use LLM v1 extraction
        background_tasks.add_task(
            run_extraction_v1,
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

    # Get real-time progress from extraction agent (check both v1 and v2)
    progress_info = extraction_progress_v2.get(assessment_id, {}) or extraction_progress_v1.get(assessment_id, {})
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
        if USE_EXTRACTION_V2:
            background_tasks.add_task(
                run_extraction_pipeline_v2,
                assessment_id=assessment_id,
                statement_id=statement.id,
                file_path=statement.file_path
            )
        else:
            background_tasks.add_task(
                run_extraction_v1,
                assessment_id=assessment_id,
                statement_id=statement.id,
                file_path=statement.file_path
            )

    return {"message": f"Extraction triggered for {len(pending_statements)} files"}


# Create new financial data (add a new fiscal year)
@router.post("/{assessment_id}/financial-data")
async def create_financial_data(
    assessment_id: int,
    data: ExtractedDataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new financial data for a specific fiscal year (manual entry)."""
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

    if not data.fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal year is required when creating new financial data"
        )

    # Check if fiscal year already exists
    existing = (
        db.query(ExtractedFinancialData)
        .filter(
            ExtractedFinancialData.assessment_id == assessment_id,
            ExtractedFinancialData.fiscal_year == data.fiscal_year
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Financial data for fiscal year {data.fiscal_year} already exists"
        )

    # Create new financial data record
    new_data = ExtractedFinancialData(
        assessment_id=assessment_id,
        fiscal_year=data.fiscal_year,
        is_confirmed=False
    )

    # Set all provided fields
    update_fields = data.model_dump(exclude_unset=True, exclude={'fiscal_year'})
    for field, value in update_fields.items():
        if hasattr(new_data, field):
            setattr(new_data, field, value)

    db.add(new_data)
    db.commit()
    db.refresh(new_data)

    return new_data


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

    # Debug logging
    print(f"\n=== UPDATE FINANCIAL DATA DEBUG ===")
    print(f"Assessment ID: {assessment_id}, Data ID: {data_id}")
    print(f"Fiscal Year: {extracted_data.fiscal_year}")
    print(f"Update data received: {update_data}")

    for field, value in update_data.items():
        old_value = getattr(extracted_data, field, None)
        print(f"  {field}: {old_value} -> {value}")
        setattr(extracted_data, field, value)

    db.commit()
    db.refresh(extracted_data)

    # Log the updated values
    print(f"After update - current_assets: {extracted_data.current_assets}")
    print(f"After update - current_liabilities: {extracted_data.current_liabilities}")
    print(f"After update - cash_and_equivalents: {extracted_data.cash_and_equivalents}")
    print(f"=================================\n")

    return extracted_data


# Delete financial data for a fiscal year
@router.delete("/{assessment_id}/financial-data/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_data(
    assessment_id: int,
    data_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete financial data for a specific fiscal year."""
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

    db.delete(extracted_data)
    db.commit()


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
    company_type: str = "private",  # "public" or "private"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate financial ratios and Z-score.

    Args:
        company_type: "public" or "private" - affects Z-Score calculation formula

    Z-Score Formulas:
        - Public: Z = 1.200*X1 + 1.400*X2 + 3.300*X3 + 0.600*X4a + 1.000*X5
        - Private: Z = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4b + 0.998*X5

    Where:
        - X1 = Working Capital / Total Assets
        - X2 = Retained Earnings / Total Assets
        - X3 = EBIT / Total Assets
        - X4a/X4b = Equity / Total Liabilities
        - X5 = Sales / Total Assets
    """
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

    # Get all confirmed financial data ordered by year
    all_data = (
        db.query(ExtractedFinancialData)
        .filter(
            ExtractedFinancialData.assessment_id == assessment_id,
            ExtractedFinancialData.is_confirmed == True
        )
        .order_by(ExtractedFinancialData.fiscal_year.desc())
        .all()
    )

    if not all_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed financial data available"
        )

    # Get current and previous year data
    current_year_data = all_data[0]
    previous_year_data = all_data[1] if len(all_data) > 1 else None

    # Determine company type enum
    comp_type = CompanyType.PUBLIC if company_type.lower() == "public" else CompanyType.PRIVATE

    # Calculate ratios using new calculator
    calculator = FinancialCalculator(
        current_year_data=current_year_data,
        previous_year_data=previous_year_data,
        company_type=comp_type
    )

    # Get full assessment (ratios + z-score + summary)
    full_assessment = calculator.calculate_full_assessment()
    z_score_result = full_assessment["z_score"]
    ratios = full_assessment["ratios"]
    summary = full_assessment["summary"]

    # Debug logging for calculation
    print(f"\n=== RATIO CALCULATION DEBUG ===")
    print(f"Company Type: {comp_type.value}")
    print(f"Fiscal Year: {current_year_data.fiscal_year}")
    print(f"Data ID: {current_year_data.id}")
    print(f"\n--- LIQUIDITY RATIO INPUTS ---")
    print(f"  current_assets: {current_year_data.current_assets}")
    print(f"  current_liabilities: {current_year_data.current_liabilities}")
    print(f"  cash_and_equivalents: {current_year_data.cash_and_equivalents}")
    print(f"  inventory: {current_year_data.inventory}")
    print(f"\n--- CALCULATED LIQUIDITY RATIOS ---")
    print(f"  current_ratio: {ratios['liquidity']['current_ratio']['value']}")
    print(f"  quick_ratio: {ratios['liquidity']['quick_ratio']['value']}")
    print(f"  cash_ratio: {ratios['liquidity']['cash_ratio']['value']}")
    print(f"\n--- OTHER INPUT DATA ---")
    print(f"  total_assets: {current_year_data.total_assets}")
    print(f"  total_liabilities: {current_year_data.total_liabilities}")
    print(f"  total_equity: {current_year_data.total_equity}")
    print(f"  working_capital: {current_year_data.working_capital}")
    print(f"  retained_earnings: {current_year_data.retained_earnings}")
    print(f"  revenue: {current_year_data.revenue}")
    print(f"  ebit: {current_year_data.ebit}")
    print(f"  operating_income: {current_year_data.operating_income}")
    print(f"  net_income: {current_year_data.net_income}")
    print(f"  interest_expense: {current_year_data.interest_expense}")
    print(f"\n--- Z-SCORE RESULT ---")
    print(f"  z_score: {z_score_result.get('z_score')}")
    print(f"  risk_level: {z_score_result.get('risk_level')}")
    print(f"  components: {z_score_result.get('components')}")
    print(f"  components_available: {z_score_result.get('components_available')}/5")
    print(f"=================================\n")

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
    risk_assessment.company_type = comp_type.value

    # Z-Score and components
    components = z_score_result.get("components", {})
    risk_assessment.z_score = z_score_result.get("z_score")
    risk_assessment.z_score_x1 = components.get("x1")
    risk_assessment.z_score_x2 = components.get("x2")
    risk_assessment.z_score_x3 = components.get("x3")
    risk_assessment.z_score_x4 = components.get("x4")
    risk_assessment.z_score_x5 = components.get("x5")
    risk_assessment.risk_level = summary.get("overall_risk_level")

    # Liquidity ratios
    risk_assessment.working_capital_ratio = ratios["liquidity"]["working_capital_ratio"]["value"]
    risk_assessment.current_ratio = ratios["liquidity"]["current_ratio"]["value"]
    risk_assessment.quick_ratio = ratios["liquidity"]["quick_ratio"]["value"]
    risk_assessment.cash_ratio = ratios["liquidity"]["cash_ratio"]["value"]

    # Profitability ratios
    risk_assessment.gross_margin = ratios["profitability"]["gross_margin"]["value"]
    risk_assessment.operating_margin = ratios["profitability"]["net_margin"]["value"]  # Using net_margin
    risk_assessment.net_margin = ratios["profitability"]["net_margin"]["value"]
    risk_assessment.roa = ratios["profitability"]["roa"]["value"]
    risk_assessment.roe = ratios["profitability"]["roe"]["value"]

    # Leverage ratios
    risk_assessment.debt_to_equity = ratios["leverage"]["debt_to_equity"]["value"]
    risk_assessment.debt_to_assets = ratios["leverage"]["debt_to_assets"]["value"]
    risk_assessment.interest_coverage = ratios["leverage"]["interest_coverage"]["value"]
    risk_assessment.retained_earnings_to_assets = ratios["leverage"]["retained_earnings_to_assets"]["value"]

    # Efficiency ratios
    risk_assessment.asset_turnover = ratios["efficiency"]["sales_to_assets"]["value"]
    risk_assessment.inventory_turnover = ratios["efficiency"]["inventory_turnover"]["value"]
    risk_assessment.receivables_turnover = ratios["efficiency"]["sales_to_receivables"]["value"]
    risk_assessment.sales_to_working_capital = ratios["efficiency"]["sales_to_working_capital"]["value"]
    risk_assessment.creditors_to_sales = ratios["efficiency"]["creditors_to_sales"]["value"]

    # Growth ratios
    risk_assessment.growth_sales = ratios["growth"]["growth_sales"]["value"]
    risk_assessment.growth_net_profit = ratios["growth"]["growth_net_profit"]["value"]
    risk_assessment.growth_gross_profit_margin = ratios["growth"]["growth_gross_profit_margin"]["value"]
    risk_assessment.growth_net_profit_margin = ratios["growth"]["growth_net_profit_margin"]["value"]

    # Store full ratios detail with risk levels as JSON
    # Include Z-Score details for comprehensive reporting
    risk_assessment.ratios_detail = {
        **ratios,
        "z_score": {
            "value": z_score_result.get("z_score"),
            "risk_level": z_score_result.get("risk_level"),
            "company_type": z_score_result.get("company_type"),
            "components": z_score_result.get("components"),
            "weighted_components": z_score_result.get("weighted_components"),
            "component_risks": z_score_result.get("component_risks"),
            "components_available": z_score_result.get("components_available"),
            "is_estimated": z_score_result.get("is_estimated")
        }
    }

    # Metadata
    risk_assessment.fiscal_year_used = current_year_data.fiscal_year
    risk_assessment.previous_fiscal_year_used = previous_year_data.fiscal_year if previous_year_data else None
    risk_assessment.calculated_at = datetime.utcnow()

    # Update assessment status
    assessment.status = AssessmentStatus.STEP3_COMPLETE.value
    assessment.current_step = 4

    db.commit()
    db.refresh(risk_assessment)

    # Return enriched response with summary
    return {
        "risk_assessment": risk_assessment,
        "summary": summary,
        "z_score_detail": z_score_result
    }


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


# Get all line items for an assessment
@router.get("/{assessment_id}/line-items")
async def get_line_items(
    assessment_id: int,
    fiscal_year: int = None,
    statement_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all extracted line items for an assessment.

    Optional filters:
    - fiscal_year: Filter by specific fiscal year
    - statement_type: Filter by statement type (balance_sheet, income_statement, cash_flow)
    """
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

    # Build query
    query = db.query(FinancialLineItem).filter(
        FinancialLineItem.assessment_id == assessment_id
    )

    # Apply filters
    if fiscal_year:
        query = query.filter(FinancialLineItem.fiscal_year == fiscal_year)

    if statement_type:
        query = query.filter(FinancialLineItem.statement_type == statement_type)

    # Order by year, statement type, and level
    line_items = query.order_by(
        FinancialLineItem.fiscal_year.desc(),
        FinancialLineItem.statement_type,
        FinancialLineItem.level,
        FinancialLineItem.line_item_text
    ).all()

    return {
        "assessment_id": assessment_id,
        "total_items": len(line_items),
        "line_items": [item.to_dict() for item in line_items]
    }


# Get hierarchical financial data
@router.get("/{assessment_id}/hierarchical-data")
async def get_hierarchical_data(
    assessment_id: int,
    fiscal_year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get financial data organized in hierarchical tree structure.
    Shows breakdown of totals into sub-categories and line items.

    Example:
    - Total Assets (level 0)
      - Current Assets (level 1)
        - Cash and Equivalents (level 2)
        - Accounts Receivable (level 2)
      - Non-Current Assets (level 1)
    """
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

    # Get all line items
    query = db.query(FinancialLineItem).filter(
        FinancialLineItem.assessment_id == assessment_id
    )

    if fiscal_year:
        query = query.filter(FinancialLineItem.fiscal_year == fiscal_year)

    line_items = query.order_by(
        FinancialLineItem.fiscal_year.desc(),
        FinancialLineItem.statement_type,
        FinancialLineItem.level,
        FinancialLineItem.line_item_text
    ).all()

    # Get all fiscal years
    all_years = sorted(set(item.fiscal_year for item in line_items), reverse=True)

    # Build hierarchical structure
    def build_tree(items, parent_canonical=None, current_level=0):
        """Recursively build tree structure"""
        tree = []

        # Get items at current level with matching parent
        current_items = [
            item for item in items
            if item.level == current_level and item.parent_canonical_name == parent_canonical
        ]

        for item in current_items:
            # Group values by year
            values_by_year = {}
            for year_item in items:
                if year_item.canonical_name == item.canonical_name:
                    values_by_year[year_item.fiscal_year] = year_item.value

            # Build node
            node = {
                "line_item": item.line_item_text,
                "canonical_name": item.canonical_name,
                "category": item.category,
                "level": item.level,
                "values": values_by_year,
                "statement_type": item.statement_type,
                "confidence": item.confidence,
                "children": []
            }

            # Recursively get children
            if item.canonical_name:
                children = build_tree(items, item.canonical_name, current_level + 1)
                node["children"] = children

            tree.append(node)

        return tree

    # Organize by statement type
    hierarchical_data = {
        "assessment_id": assessment_id,
        "fiscal_years": all_years,
        "statements": {
            "balance_sheet": build_tree(
                [item for item in line_items if item.statement_type == "balance_sheet"]
            ),
            "income_statement": build_tree(
                [item for item in line_items if item.statement_type == "income_statement"]
            ),
            "cash_flow": build_tree(
                [item for item in line_items if item.statement_type == "cash_flow"]
            )
        }
    }

    return hierarchical_data


# Get breakdown for specific line item
@router.get("/{assessment_id}/line-items/breakdown/{canonical_name}")
async def get_line_item_breakdown(
    assessment_id: int,
    canonical_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the breakdown (children) of a specific line item.

    Example:
    - canonical_name = "total_assets"
    - Returns: current_assets, non_current_assets, and their children
    """
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

    # Get the parent item
    parent_items = (
        db.query(FinancialLineItem)
        .filter(
            FinancialLineItem.assessment_id == assessment_id,
            FinancialLineItem.canonical_name == canonical_name
        )
        .order_by(FinancialLineItem.fiscal_year.desc())
        .all()
    )

    if not parent_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Line item '{canonical_name}' not found"
        )

    # Get parent values by year
    parent_values = {item.fiscal_year: item.value for item in parent_items}
    parent_info = parent_items[0]  # Use most recent for metadata

    # Get all children (direct and nested)
    def get_all_children(parent_canonical, level_offset=0):
        """Recursively get all children"""
        children = []

        # Get direct children
        direct_children = (
            db.query(FinancialLineItem)
            .filter(
                FinancialLineItem.assessment_id == assessment_id,
                FinancialLineItem.parent_canonical_name == parent_canonical
            )
            .order_by(
                FinancialLineItem.fiscal_year.desc(),
                FinancialLineItem.level,
                FinancialLineItem.line_item_text
            )
            .all()
        )

        # Group by canonical name to consolidate years
        items_by_canonical = {}
        for item in direct_children:
            if item.canonical_name not in items_by_canonical:
                items_by_canonical[item.canonical_name] = {
                    "line_item": item.line_item_text,
                    "canonical_name": item.canonical_name,
                    "category": item.category,
                    "level": item.level - parent_info.level - 1 + level_offset,  # Relative level
                    "values": {},
                    "statement_type": item.statement_type,
                    "confidence": item.confidence,
                    "children": []
                }
            items_by_canonical[item.canonical_name]["values"][item.fiscal_year] = item.value

        # Get nested children
        for canonical, item_data in items_by_canonical.items():
            nested_children = get_all_children(canonical, level_offset)
            item_data["children"] = nested_children
            children.append(item_data)

        return children

    children = get_all_children(canonical_name)

    return {
        "assessment_id": assessment_id,
        "parent": {
            "line_item": parent_info.line_item_text,
            "canonical_name": parent_info.canonical_name,
            "category": parent_info.category,
            "level": parent_info.level,
            "values": parent_values,
            "statement_type": parent_info.statement_type
        },
        "breakdown": children,
        "total_children": len(children)
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


# Download Excel report
@router.get("/{assessment_id}/download-excel")
async def download_assessment_excel(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the assessment as an Excel report with recommendation, Z-Score, and financial data."""
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

    # Generate Excel
    excel_buffer = generate_assessment_excel(assessment)

    # Create filename
    vendor_name = assessment.vendor_name.replace(" ", "_") if assessment.vendor_name else "assessment"
    filename = f"VFA_Report_{vendor_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
