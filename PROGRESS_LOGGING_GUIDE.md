# PDF Extraction Progress Logging Guide

## Overview

The optimized extraction agent now provides detailed, real-time progress logging so you can monitor exactly what's happening during PDF processing.

---

## Complete Progress Log Example

Here's what you'll see in the backend console when processing a 112-page PDF:

```
================================================================================
STARTING EXTRACTION PIPELINE
Assessment ID: 2 | Statement ID: 3
File: uploads/2/financial-statement.pdf
================================================================================

STAGE 1/3: PDF Text Extraction & Analysis

=== OPTIMIZED EXTRACTION: uploads/2/financial-statement.pdf ===
Starting parallel extraction for all 3 statement types...

┌─────────────────────────────────────────────────────────────────────────────┐
│ BALANCE SHEET EXTRACTION                                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Scanning 112 pages for balance_sheet...
  [  4%] Processing page 5/112 for balance_sheet...
  ✓ Page 8 relevant (score: 45)
  [  9%] Processing page 10/112 for balance_sheet...
  [ 13%] Processing page 15/112 for balance_sheet...
  ✓ Page 16 relevant (score: 38)
  [ 18%] Processing page 20/112 for balance_sheet...
  [ 22%] Processing page 25/112 for balance_sheet...
  ✓ Page 27 relevant (score: 42)
  [ 27%] Processing page 30/112 for balance_sheet...
  [ 31%] Processing page 35/112 for balance_sheet...
  [ 36%] Processing page 40/112 for balance_sheet...
  ✓ Page 43 relevant (score: 35)
  [ 40%] Processing page 45/112 for balance_sheet...
  [ 45%] Processing page 50/112 for balance_sheet...
  [ 49%] Processing page 55/112 for balance_sheet...
  [ 54%] Processing page 60/112 for balance_sheet...
  [ 58%] Processing page 65/112 for balance_sheet...
  [ 63%] Processing page 70/112 for balance_sheet...
  [ 67%] Processing page 75/112 for balance_sheet...
  [ 71%] Processing page 80/112 for balance_sheet...
  [ 76%] Processing page 85/112 for balance_sheet...
  [ 80%] Processing page 90/112 for balance_sheet...
  [ 85%] Processing page 95/112 for balance_sheet...
  [ 89%] Processing page 100/112 for balance_sheet...
  [ 94%] Processing page 105/112 for balance_sheet...
  [ 98%] Processing page 110/112 for balance_sheet...
  [100%] Processing page 112/112 for balance_sheet...
  [100%] Completed scanning 112 pages, found 8 relevant pages

  Ranking pages by relevance score...
  ✓ Selected top 8 pages for balance_sheet
  Selected pages: [8, 16, 27, 43, 56, 67, 78, 89] (scores: [45, 42, 38, 35, 32, 30, 28, 25])

  Extracting text from selected pages...
  [1/8] Extracted 1,245 chars from page 8
  [2/8] Extracted 1,189 chars from page 16
  [3/8] Extracted 1,321 chars from page 27
  [4/8] Extracted 1,156 chars from page 43
  [5/8] Extracted 1,278 chars from page 56
  [6/8] Extracted 1,203 chars from page 67
  [7/8] Extracted 1,267 chars from page 78
  [8/8] Extracted 1,198 chars from page 89
  ✓ Ready for LLM: 9,857 total characters from 8 pages

Calling OpenAI API for Balance Sheet extraction (9,857 chars, model: gpt-4o-mini)...
  Received response from OpenAI for Balance Sheet
  Balance Sheet successfully extracted 3 fiscal year(s): [2023, 2022, 2021]

┌─────────────────────────────────────────────────────────────────────────────┐
│ INCOME STATEMENT EXTRACTION                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Scanning 112 pages for income_statement...
  [  4%] Processing page 5/112 for income_statement...
  ✓ Page 6 relevant (score: 52)
  [  9%] Processing page 10/112 for income_statement...
  ✓ Page 12 relevant (score: 48)
  [ 13%] Processing page 15/112 for income_statement...
  ...
  [100%] Processing page 112/112 for income_statement...
  [100%] Completed scanning 112 pages, found 7 relevant pages

  Ranking pages by relevance score...
  ✓ Selected top 7 pages for income_statement
  Selected pages: [6, 12, 29, 45, 61, 77, 93] (scores: [52, 48, 44, 40, 38, 35, 32])

  Extracting text from selected pages...
  [1/7] Extracted 1,156 chars from page 6
  [2/7] Extracted 1,234 chars from page 12
  [3/7] Extracted 1,189 chars from page 29
  [4/7] Extracted 1,267 chars from page 45
  [5/7] Extracted 1,198 chars from page 61
  [6/7] Extracted 1,245 chars from page 77
  [7/7] Extracted 1,203 chars from page 93
  ✓ Ready for LLM: 8,492 total characters from 7 pages

Calling OpenAI API for Income Statement extraction (8,492 chars, model: gpt-4o-mini)...
  Received response from OpenAI for Income Statement
  Income Statement successfully extracted 3 fiscal year(s): [2023, 2022, 2021]

┌─────────────────────────────────────────────────────────────────────────────┐
│ CASH FLOW EXTRACTION                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

Scanning 112 pages for cash_flow...
  [  4%] Processing page 5/112 for cash_flow...
  [  9%] Processing page 10/112 for cash_flow...
  ✓ Page 11 relevant (score: 38)
  ...
  [100%] Processing page 112/112 for cash_flow...
  [100%] Completed scanning 112 pages, found 5 relevant pages

  Ranking pages by relevance score...
  ✓ Selected top 5 pages for cash_flow
  Selected pages: [11, 30, 49, 68, 87] (scores: [38, 35, 32, 28, 25])

  Extracting text from selected pages...
  [1/5] Extracted 1,089 chars from page 11
  [2/5] Extracted 1,156 chars from page 30
  [3/5] Extracted 1,134 chars from page 49
  [4/5] Extracted 1,198 chars from page 68
  [5/5] Extracted 1,167 chars from page 87
  ✓ Ready for LLM: 5,744 total characters from 5 pages

Calling OpenAI API for Cash Flow extraction (5,744 chars, model: gpt-4o-mini)...
  Received response from OpenAI for Cash Flow
  Cash Flow successfully extracted 3 fiscal year(s): [2023, 2022, 2021]

Parallel extraction completed for all statement types

Merging extraction results from all statement types...
Year 2023: 24/26 fields, confidence: 0.89
Year 2022: 22/26 fields, confidence: 0.84
Year 2021: 20/26 fields, confidence: 0.78

✓ STAGE 1 COMPLETE: Extracted 3 fiscal year(s), avg confidence: 0.84

STAGE 2/3: Saving Results to Database
Stored results for assessment 2
✓ STAGE 2 COMPLETE: Results saved

STAGE 3/3: Cleanup & Finalization
================================================================================
✓ EXTRACTION PIPELINE COMPLETE
================================================================================
```

---

## Progress Indicators Explained

### 1. **Page Scanning Progress**

```
[  4%] Processing page 5/112 for balance_sheet...
[  9%] Processing page 10/112 for balance_sheet...
```

- **Percentage**: Shows progress through all pages
- **Current/Total**: Shows which page is being processed (e.g., page 5 out of 112)
- **Statement Type**: Shows which financial statement is being analyzed

**Frequency:**
- Every 5 pages for large PDFs (>20 pages)
- Every page for small PDFs (≤20 pages)

### 2. **Relevant Page Detection**

```
✓ Page 8 relevant (score: 45)
✓ Page 16 relevant (score: 42)
```

- **Checkmark**: Indicates a relevant page was found
- **Page Number**: Which page contains financial data
- **Score**: Relevance score (higher = more relevant)

**Scoring:**
- Title keywords (e.g., "Balance Sheet"): +10 points
- Data keywords (e.g., "Total Assets"): +1 point each
- Numeric density (>15 numbers): +5 points

### 3. **Page Selection Summary**

```
✓ Selected top 8 pages for balance_sheet
Selected pages: [8, 16, 27, 43, 56, 67, 78, 89] (scores: [45, 42, 38, ...])
```

- **Page Numbers**: Shows exactly which pages will be sent to AI
- **Scores**: Relevance scores in descending order

### 4. **Text Extraction Progress**

```
[1/8] Extracted 1,245 chars from page 8
[2/8] Extracted 1,189 chars from page 16
```

- **Progress Counter**: Shows which selected page is being processed
- **Character Count**: Amount of text extracted from each page

### 5. **LLM API Call Status**

```
Calling OpenAI API for Balance Sheet extraction (9,857 chars, model: gpt-4o-mini)...
  Received response from OpenAI for Balance Sheet
  Balance Sheet successfully extracted 3 fiscal year(s): [2023, 2022, 2021]
```

- **Character Count**: Total text sent to AI
- **Model**: Which AI model is being used
- **Years Found**: Number of fiscal years extracted

### 6. **Confidence Scores**

```
Year 2023: 24/26 fields, confidence: 0.89
Year 2022: 22/26 fields, confidence: 0.84
```

- **Fields Ratio**: How many fields were successfully extracted
- **Confidence Score**: 0.0-1.0 (higher = better quality)

### 7. **Pipeline Stages**

```
STAGE 1/3: PDF Text Extraction & Analysis
✓ STAGE 1 COMPLETE

STAGE 2/3: Saving Results to Database
✓ STAGE 2 COMPLETE

STAGE 3/3: Cleanup & Finalization
```

- Shows overall progress through the extraction pipeline
- Each stage is marked complete with ✓

---

## Error Indicators

### Page Read Error

```
✗ Error reading page 45: [error details]
```

- **✗ Symbol**: Indicates an error occurred
- **Details**: Shows what went wrong

### LLM Extraction Error

```
Balance Sheet extraction error: [error details]
```

- Shows if AI extraction failed for a specific statement type
- Pipeline continues with other statement types

### Pipeline Error

```
Pipeline error: [error details]
```

- Critical error that stops the entire extraction
- Full error details provided for debugging

---

## Small PDF Example (20 pages)

For PDFs with ≤20 pages, you see progress for EVERY page:

```
Scanning 15 pages for balance_sheet...
  [  7%] Processing page 1/15 for balance_sheet...
  [ 13%] Processing page 2/15 for balance_sheet...
  ✓ Page 3 relevant (score: 52)
  [ 20%] Processing page 3/15 for balance_sheet...
  [ 27%] Processing page 4/15 for balance_sheet...
  [ 33%] Processing page 5/15 for balance_sheet...
  ...
  [100%] Processing page 15/15 for balance_sheet...
  [100%] Completed scanning 15 pages, found 4 relevant pages
```

---

## Timing Estimates

Based on a 112-page financial statement:

| Phase | Duration | What Happens |
|-------|----------|--------------|
| **Page Scanning** | ~10-15 sec | Reads all pages, scores relevance |
| **Text Extraction** | ~2-3 sec | Extracts text from selected pages |
| **LLM Processing** | ~5-8 sec | AI analyzes text (3 parallel calls) |
| **Data Merging** | ~1 sec | Combines results from all statements |
| **Database Save** | ~1 sec | Stores extracted data |
| **Total** | **~20-30 sec** | Complete end-to-end extraction |

For smaller PDFs (20-30 pages), expect ~8-12 seconds total.

---

## How to Monitor Progress

### 1. Terminal/Console View

When running the backend with `uvicorn app.main:app --reload`, all progress logs appear in real-time in your terminal.

### 2. Log File (Optional)

To save logs to a file:

```bash
uvicorn app.main:app --reload > extraction.log 2>&1
```

Then monitor with:

```bash
tail -f extraction.log
```

### 3. Grep for Specific Info

To see only percentage progress:

```bash
uvicorn app.main:app --reload 2>&1 | grep "\[.*%\]"
```

To see only completed stages:

```bash
uvicorn app.main:app --reload 2>&1 | grep "✓"
```

---

## Troubleshooting

### "Stuck" on a Page

If you see the same page percentage for >10 seconds:

```
[ 45%] Processing page 50/112 for balance_sheet...
```

**Possible causes:**
- Large page with lots of text (takes longer to extract)
- Complex table structures
- Corrupted PDF page

**Resolution:**
- Wait 30 seconds - some pages are legitimately slow
- If truly stuck (>1 minute on same page), restart backend

### No Progress After "Calling OpenAI API"

```
Calling OpenAI API for Balance Sheet extraction (9,857 chars, model: gpt-4o-mini)...
[... waiting ...]
```

**Possible causes:**
- OpenAI API is slow (high load)
- Network latency
- Large text being processed

**Resolution:**
- Normal wait time: 3-10 seconds
- If >30 seconds, may be API rate limit or connectivity issue
- Check OpenAI API status at status.openai.com

### Error Messages

If you see errors, check:

1. **JSON parse errors**: Rare but can happen if AI returns invalid JSON
   - Automatically retries up to 3 times
   - If all retries fail, that statement extraction is skipped

2. **Page read errors**: Some PDF pages may be corrupted
   - These are logged but don't stop processing
   - Other pages continue to be processed

3. **Pipeline errors**: Critical failures
   - Check error message for details
   - Common: File not found, permissions, out of memory

---

## Best Practices

1. **Monitor first extraction** - Watch the logs for your first PDF to understand timing
2. **Expected duration** - Budget 20-30 seconds for typical financial statements
3. **Check confidence scores** - Aim for >0.75 confidence for good quality
4. **Review low scores** - If confidence <0.60, manually review extracted data

---

## Summary

The new progress logging provides:

- ✓ Real-time page-by-page progress with percentages
- ✓ Relevant page detection with scores
- ✓ Text extraction progress
- ✓ LLM API call status
- ✓ Confidence scores for quality assessment
- ✓ Clear stage indicators
- ✓ Error reporting

You'll never wonder "Is it still working?" again!
