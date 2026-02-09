"""
Vendor Financial Assessment API
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, assessments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    yield

    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for Vendor Financial Assessment system with AI-powered document extraction and risk analysis.",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(assessments.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/test")
async def postman_test_collection():
    """Get all API endpoints with headers and body examples for Postman testing."""
    base_url = "http://localhost:8000"

    return {
        "info": {
            "name": "VFA API Test Collection",
            "description": "Complete API endpoints with headers and body examples for Postman testing",
            "base_url": base_url
        },
        "authentication": [
            {
                "name": "Register User",
                "method": "POST",
                "url": f"{base_url}/api/auth/register",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": {
                    "email": "test@example.com",
                    "password": "yourpassword123",
                    "full_name": "John Doe"
                },
                "description": "Register a new user and receive access token"
            },
            {
                "name": "Login",
                "method": "POST",
                "url": f"{base_url}/api/auth/login",
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                "body": {
                    "username": "test@example.com",
                    "password": "yourpassword123"
                },
                "description": "Login with email (as username) and password. Returns access token."
            },
            {
                "name": "Get Current User",
                "method": "GET",
                "url": f"{base_url}/api/auth/me",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Get current authenticated user info"
            },
            {
                "name": "Logout",
                "method": "POST",
                "url": f"{base_url}/api/auth/logout",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Logout user (client-side token removal)"
            }
        ],
        "assessments_crud": [
            {
                "name": "Create Assessment",
                "method": "POST",
                "url": f"{base_url}/api/assessments",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Create a new vendor assessment. No input required."
            },
            {
                "name": "List Assessments",
                "method": "GET",
                "url": f"{base_url}/api/assessments?skip=0&limit=50",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "List all assessments for current user (paginated)"
            },
            {
                "name": "Get Assessment",
                "method": "GET",
                "url": f"{base_url}/api/assessments/{{assessment_id}}",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Get a specific assessment by ID. Replace {assessment_id} with actual ID."
            },
            {
                "name": "Update Assessment",
                "method": "PATCH",
                "url": f"{base_url}/api/assessments/{{assessment_id}}",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": {
                    "vendor_name": "Updated Vendor Name",
                    "vendor_registration_number": "REG-54321"
                },
                "description": "Update an assessment. All fields are optional."
            },
            {
                "name": "Delete Assessment",
                "method": "DELETE",
                "url": f"{base_url}/api/assessments/{{assessment_id}}",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Delete an assessment by ID"
            }
        ],
        "file_upload_and_processing": [
            {
                "name": "Upload Financial Statement",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/upload",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": {
                    "type": "form-data",
                    "fields": {
                        "file": "(PDF file) - Select a PDF file in Postman"
                    }
                },
                "description": "Upload a financial statement PDF. Use form-data with key 'file'."
            },
            {
                "name": "Check Extraction Status",
                "method": "GET",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/extraction-status",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Check the status of PDF extraction for an assessment"
            },
            {
                "name": "Trigger Extraction",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/extract",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Manually trigger extraction for all pending files"
            }
        ],
        "financial_data": [
            {
                "name": "Get Financial Data",
                "method": "GET",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/financial-data",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Get all extracted financial data for an assessment"
            },
            {
                "name": "Update Financial Data",
                "method": "PUT",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/financial-data/{{data_id}}",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": {
                    "fiscal_year": 2024,
                    "total_assets": 1000000.00,
                    "current_assets": 400000.00,
                    "non_current_assets": 600000.00,
                    "total_liabilities": 500000.00,
                    "current_liabilities": 200000.00,
                    "non_current_liabilities": 300000.00,
                    "total_equity": 500000.00,
                    "retained_earnings": 150000.00,
                    "working_capital": 200000.00,
                    "cash_and_equivalents": 100000.00,
                    "inventory": 80000.00,
                    "accounts_receivable": 120000.00,
                    "accounts_payable": 90000.00,
                    "revenue": 2000000.00,
                    "cost_of_sales": 1200000.00,
                    "gross_profit": 800000.00,
                    "operating_expenses": 400000.00,
                    "operating_income": 400000.00,
                    "ebit": 400000.00,
                    "ebitda": 500000.00,
                    "interest_expense": 50000.00,
                    "net_income": 280000.00,
                    "operating_cash_flow": 350000.00,
                    "investing_cash_flow": -100000.00,
                    "financing_cash_flow": -50000.00,
                    "net_cash_flow": 200000.00,
                    "is_confirmed": False
                },
                "description": "Update extracted financial data for manual corrections. All numeric fields are optional."
            },
            {
                "name": "Confirm Financial Data",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/confirm-data",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Confirm all extracted financial data and move to step 2"
            }
        ],
        "qualitative_responses": [
            {
                "name": "Update Qualitative Response",
                "method": "PUT",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/qualitative/{{question_id}}",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": {
                    "response": "yes",
                    "notes": "Additional notes about the response"
                },
                "description": "Update a qualitative questionnaire response. Question IDs are Q1-Q5."
            }
        ],
        "calculations_and_recommendations": [
            {
                "name": "Calculate Financial Ratios",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/calculate",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Calculate financial ratios and Z-score based on confirmed financial data"
            },
            {
                "name": "Generate AI Recommendation",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/recommend",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Generate AI-powered recommendation based on all assessment data"
            }
        ],
        "sign_off_and_export": [
            {
                "name": "Sign Off Assessment",
                "method": "POST",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/sign-off",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Sign off on the assessment and finalize"
            },
            {
                "name": "Download PDF Report",
                "method": "GET",
                "url": f"{base_url}/api/assessments/{{assessment_id}}/download-pdf",
                "headers": {
                    "Authorization": "Bearer <your_access_token>"
                },
                "body": None,
                "description": "Download the assessment as a PDF report"
            }
        ],
        "notes": {
            "authentication": "Replace <your_access_token> with the token received from /api/auth/login or /api/auth/register",
            "path_parameters": "Replace {assessment_id}, {data_id}, {question_id} with actual values",
            "question_ids": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "workflow": [
                "1. Register or Login to get access token",
                "2. Create an assessment (no input required)",
                "3. Upload financial statement PDF",
                "4. Wait for extraction or check extraction status",
                "5. Get extracted financial data to review",
                "6. Update/correct financial data if needed",
                "7. Confirm financial data",
                "8. Update qualitative responses (Q1-Q5)",
                "9. Calculate financial ratios",
                "10. Generate AI recommendation",
                "11. Sign off assessment",
                "12. Download PDF report"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
