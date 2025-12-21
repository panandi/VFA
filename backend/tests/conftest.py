"""
Pytest configuration and fixtures.
"""

import os
import sys
import json
from pathlib import Path

import pytest

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_pdf_path():
    """
    Fixture to provide a sample PDF path.

    Set PDF_TEST_FILE environment variable or place a PDF in uploads/.
    """
    # Check environment variable
    if os.environ.get('PDF_TEST_FILE'):
        return os.environ['PDF_TEST_FILE']

    # Check uploads directory
    uploads_dir = Path(__file__).parent.parent / "uploads"
    if uploads_dir.exists():
        pdfs = list(uploads_dir.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])

    pytest.skip("No sample PDF available. Set PDF_TEST_FILE or place PDF in uploads/")


@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client for testing without API calls."""
    mock_response = {
        "fiscal_years": [
            {
                "year": 2023,
                "data": {
                    "Total Assets": {"value": 1000000, "source_row": "Total Assets 1,000,000", "page": 1},
                    "Total Liabilities": {"value": 400000, "source_row": "Total Liabilities 400,000", "page": 1},
                    "Equity": {"value": 600000, "source_row": "Total Equity 600,000", "page": 1},
                }
            }
        ],
        "scale": "lakhs",
        "currency": "INR"
    }

    # Mock the AsyncOpenAI client
    mock_client = mocker.patch('app.agents.extraction_agent_v2.AsyncOpenAI')
    mock_client.return_value.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_response)

    return mock_client
