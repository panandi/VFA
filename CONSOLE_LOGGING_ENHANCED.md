# Console Logging Enhanced

## What Was Added

I've added comprehensive console logging to show every operation clearly in the terminal. Now you'll see detailed, formatted output for all extraction steps.

## Files Updated

1. **`backend/app/agents/hybrid_extraction_agent.py`**
   - Added formatted logging functions
   - Detailed step-by-step progress
   - Clear success/warning/error messages
   - Timing information

2. **`backend/app/services/camelot_extractor.py`**
   - Enhanced table extraction logging
   - Shows Lattice vs Stream mode results
   - Deduplication progress
   - Classification results

## Example Console Output

### When Camelot Succeeds (Text PDF):

```
================================================================================
  HYBRID EXTRACTION AGENT
================================================================================
Assessment ID: 14
Statement ID: 10
File: uploads/14/sample.pdf
Started at: 2025-12-24 10:30:45

>>> STEP 0: Initializing extraction
--------------------------------------------------------------------------------
  Fetching statement from database...
[SUCCESS] Statement found: sample.pdf
  Updating status to 'processing'...
[SUCCESS] Status updated successfully

>>> STEP 1: Attempting Camelot Extraction (Text-based PDFs)
--------------------------------------------------------------------------------
  Camelot is FREE and FAST for text-based PDFs
  Initializing Camelot extractor...
  Scanning PDF for tables...

======================================================================
  CAMELOT TABLE EXTRACTOR
======================================================================
PDF File: uploads/14/sample.pdf

>>> Step 1: Extracting tables from PDF...
----------------------------------------------------------------------
  Trying LATTICE mode (for tables with borders)...
  Lattice mode: 15 table(s) found

[SUCCESS] Extracted 15 tables from PDF

>>> Step 2: Classifying tables by statement type...
----------------------------------------------------------------------
  - balance_sheet: 5 table(s)
  - income_statement: 6 table(s)
  - cash_flow: 4 table(s)

>>> Step 3: Processing and matching line items...
----------------------------------------------------------------------
  Processing balance_sheet...
    [OK] 45 line items extracted
  Processing income_statement...
    [OK] 38 line items extracted
  Processing cash_flow...
    [OK] 25 line items extracted

======================================================================
  CAMELOT EXTRACTION SUMMARY
======================================================================
Statements extracted: 3
  - balance_sheet: 45 items, Years: [2023, 2022]
  - income_statement: 38 items, Years: [2023, 2022]
  - cash_flow: 25 items, Years: [2023, 2022]
======================================================================

  Camelot scan completed in 8.52s
  Found 3 statement type(s)

[SUCCESS] Camelot successfully extracted financial data!
  PDF Type: TEXT-BASED (digital)
  Extraction Method: Camelot (No LLM required)
  Data Format: HIERARCHICAL (tree structure)
  Cost: $0.00 (FREE)

>>> STEP 2: Processing Camelot Results
--------------------------------------------------------------------------------
  Statement Type: balance_sheet
    - Years detected: [2023, 2022]
    - Line items: 45
  Statement Type: income_statement
    - Years detected: [2023, 2022]
    - Line items: 38
  Statement Type: cash_flow
    - Years detected: [2023, 2022]
    - Line items: 25

  Clearing previous line items (if any)...
  Deleted 0 old line items
  Saving hierarchical line items to database...
    Saved 50 items...
    Saved 100 items...
[SUCCESS] Saved 108 hierarchical line items to database

>>> STEP 3: Creating Flat Data (Backward Compatibility)
--------------------------------------------------------------------------------
  Populating ExtractedFinancialData table...
[SUCCESS] Flat data table populated successfully

>>> STEP 4: Finalizing
--------------------------------------------------------------------------------

================================================================================
  EXTRACTION COMPLETE
================================================================================
[SUCCESS] Hybrid extraction finished using CAMELOT
Total time: 12.34 seconds
Line items extracted: 108
Hierarchical view: AVAILABLE
Flat view: AVAILABLE
```

### When Camelot Fails (Image PDF):

```
================================================================================
  HYBRID EXTRACTION AGENT
================================================================================
Assessment ID: 15
Statement ID: 11
File: uploads/15/scanned.pdf
Started at: 2025-12-24 10:35:20

>>> STEP 0: Initializing extraction
--------------------------------------------------------------------------------
  Fetching statement from database...
[SUCCESS] Statement found: scanned.pdf
  Updating status to 'processing'...
[SUCCESS] Status updated successfully

>>> STEP 1: Attempting Camelot Extraction (Text-based PDFs)
--------------------------------------------------------------------------------
  Camelot is FREE and FAST for text-based PDFs
  Initializing Camelot extractor...
  Scanning PDF for tables...

======================================================================
  CAMELOT TABLE EXTRACTOR
======================================================================
PDF File: uploads/15/scanned.pdf

>>> Step 1: Extracting tables from PDF...
----------------------------------------------------------------------
  Trying LATTICE mode (for tables with borders)...
  Lattice mode: 0 table(s) found
  Few tables found, trying STREAM mode (for borderless tables)...
  Stream mode: 0 table(s) found
  Combining and deduplicating results...
  After deduplication: 0 unique table(s)

[NO TABLES FOUND] PDF appears to be image-based or has no tables
  Camelot requires text-based PDFs with extractable tables
======================================================================

  Camelot scan completed in 5.21s
  Found 0 statement type(s)

[WARNING] Camelot found no financial tables
  Reason: PDF appears to be IMAGE-BASED (scanned)
  Camelot limitation: Cannot read scanned/image PDFs

>>> STEP 2: Falling Back to LLM Extraction
--------------------------------------------------------------------------------
  PDF Type: IMAGE-BASED (scanned)
  Extraction Method: LLM with OCR (AI-powered)
  Data Format: FLAT (table format)
  Cost: ~$0.10-0.50 per PDF
  Processing time: 30-60 seconds

  Closing database connection...
  Initiating LLM extraction pipeline...

================================================================================
EXTRACTION PIPELINE V2
Assessment ID: 15 | Statement ID: 11
File: uploads/15/scanned.pdf
================================================================================
[... LLM extraction output ...]

================================================================================
  EXTRACTION COMPLETE
================================================================================
[SUCCESS] Hybrid extraction finished using LLM (fallback)
LLM extraction time: 42.15 seconds
Total time: 47.36 seconds
Hierarchical view: NOT AVAILABLE (image PDF)
Flat view: AVAILABLE
[WARNING] To get hierarchical data, upload a text-based PDF

================================================================================
  HYBRID EXTRACTION AGENT - END
================================================================================
```

### When Error Occurs:

```
[ERROR] Hybrid extraction failed: Database connection timeout
Exception details:
  Traceback (most recent call last):
    File "hybrid_extraction_agent.py", line 120, in run_hybrid_extraction
      db.commit()
    sqlalchemy.exc.OperationalError: database is locked

  Updating statement status to 'error'...
[SUCCESS] Error status saved to database
Database connection closed

================================================================================
  HYBRID EXTRACTION AGENT - END
================================================================================
```

## Logging Features Added

### 1. **Formatted Headers**
```python
def log_header(message: str):
    """Print a formatted header"""
    logger.info("=" * 80)
    logger.info(f"  {message}")
    logger.info("=" * 80)
```

### 2. **Step-by-Step Progress**
```python
def log_step(step_num: str, message: str):
    """Print a formatted step"""
    logger.info("")
    logger.info(f">>> STEP {step_num}: {message}")
    logger.info("-" * 80)
```

### 3. **Status Messages**
- `log_success()` - Green/success messages
- `log_warning()` - Yellow/warning messages
- `log_error()` - Red/error messages
- `log_info()` - Regular info with optional indentation

### 4. **Timing Information**
- Start time logged
- Individual step times (Camelot, LLM)
- Total extraction time

### 5. **Progress Indicators**
- Shows items saved every 50 items
- Table extraction progress
- Database operations status

### 6. **Detailed Metadata**
- Assessment ID
- Statement ID
- File path
- PDF type (text vs image)
- Extraction method used
- Cost information
- Data availability

## Benefits

1. **Easy Debugging**
   - See exactly where extraction fails
   - Understand which method was used
   - Track timing issues

2. **User Transparency**
   - Know if Camelot or LLM was used
   - See cost implications
   - Understand limitations

3. **Progress Tracking**
   - Watch extraction in real-time
   - Know how many items extracted
   - See which statement types found

4. **Error Diagnosis**
   - Full stack traces
   - Clear error messages
   - Database operation status

## How to View Logs

### Option 1: Terminal Output
Watch the backend server terminal to see real-time logs.

### Option 2: Log Files (if configured)
Check log files in `backend/logs/` directory.

### Option 3: Check via API
Access extraction status endpoint:
```
GET /api/assessments/{id}/extraction-status
```

## Log Levels

All logging uses Python's `logging` module with INFO level:

- **INFO**: Normal operation messages
- **WARNING**: Camelot fallback, non-critical issues
- **ERROR**: Extraction failures, exceptions

## Testing the Logging

### Test 1: Upload New PDF
```bash
1. Open application
2. Create new assessment
3. Upload any PDF
4. Watch backend terminal for detailed logs
5. See step-by-step progress
```

### Test 2: Re-extract Existing PDF
```python
cd backend
./venv/Scripts/python -c "
import asyncio
from app.agents.hybrid_extraction_agent import run_hybrid_extraction

asyncio.run(run_hybrid_extraction(
    assessment_id=14,
    statement_id=10,
    file_path='uploads/14/sample.pdf'
))
"
```

Watch the console output for all the enhanced logging!

## Summary

**Status:** ✅ Console logging enhanced

**What to see:**
- Clear headers and step markers
- Success/warning/error indicators
- Timing for each operation
- Detailed extraction metadata
- Progress indicators
- Full error traces

**Result:** You can now easily monitor and debug the extraction process!
