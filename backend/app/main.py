"""
Vendor Financial Assessment API
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, assessments
# Import all models to ensure tables are created
from app.models import User, VendorAssessment, FinancialStatement, ExtractedFinancialData, QualitativeResponse, RiskAssessment, Recommendation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)


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
    expose_headers=["*"],
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
    """Health check endpoint - lists all available endpoints."""

    # Collect all routes
    all_routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = list(route.methods - {"HEAD", "OPTIONS"}) if route.methods else []
            if methods:  # Only include routes with methods
                all_routes.append({
                    "path": route.path,
                    "methods": methods,
                    "name": route.name or "unnamed"
                })

    # Group by category
    categories = {
        "Root": [],
        "Authentication": [],
        "Assessments": [],
        "Financial Data": [],
        "Reports": [],
        "Other": []
    }

    for route in all_routes:
        path = route["path"]
        if path in ["/", "/health"]:
            categories["Root"].append(route)
        elif "/auth" in path:
            categories["Authentication"].append(route)
        elif any(x in path for x in ["/extract", "/hierarchical", "/ai-organized", "/line-items", "/confirm", "/calculate"]):
            categories["Financial Data"].append(route)
        elif any(x in path for x in ["/download", "/report"]):
            categories["Reports"].append(route)
        elif "/assessments" in path:
            categories["Assessments"].append(route)
        else:
            categories["Other"].append(route)

    # Build formatted output
    formatted_endpoints = {}
    total = 0

    for category, routes in categories.items():
        if routes:
            # Sort routes within category
            routes.sort(key=lambda x: (x["path"], x["methods"][0] if x["methods"] else ""))

            formatted_routes = []
            for i, route in enumerate(routes, 1):
                total += 1
                formatted_routes.append({
                    "no": i,
                    "method": ", ".join(sorted(route["methods"])),
                    "path": route["path"],
                    "name": route["name"]
                })

            formatted_endpoints[category] = formatted_routes

    return {
        "status": "✅ healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "total_endpoints": total,
        "endpoints_by_category": formatted_endpoints
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
