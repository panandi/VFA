"""Comprehensive extraction diagnostics"""
import sys
import os

print("=" * 70)
print("EXTRACTION DIAGNOSTICS")
print("=" * 70)

# Test 1: Check required modules
print("\n1. Checking Required Modules...")
required_modules = ['pypdf', 'openai', 'httpx', 'PIL', 'pytesseract']
missing = []

for module in required_modules:
    try:
        __import__(module if module != 'PIL' else 'PIL')
        print(f"  [OK] {module}")
    except ImportError:
        print(f"  [MISSING] {module}")
        missing.append(module)

if missing:
    print(f"\nMISSING MODULES: {', '.join(missing)}")
    print("Some extraction features may not work.")
else:
    print("\nAll required modules are installed!")

# Test 2: Check OpenAI configuration
print("\n2. Checking OpenAI Configuration...")
try:
    from app.core.config import settings
    has_key = bool(settings.OPENAI_API_KEY)
    print(f"  API Key: {'Configured' if has_key else 'NOT CONFIGURED'}")
    print(f"  Model: {settings.OPENAI_MODEL}")

    if not has_key:
        print("\n  WARNING: OPENAI_API_KEY is not set!")
        print("  Set it in backend/.env file")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 3: Check uploads directory
print("\n3. Checking Upload Directory...")
upload_dir = "uploads"
if os.path.exists(upload_dir):
    files = os.listdir(upload_dir)
    print(f"  [OK] Directory exists with {len(files)} files")
    if files:
        print("  Recent uploads:")
        for f in files[:5]:
            size = os.path.getsize(os.path.join(upload_dir, f))
            print(f"    - {f} ({size:,} bytes)")
else:
    print(f"  [INFO] Upload directory doesn't exist yet")

# Test 4: Check extraction agents
print("\n4. Checking Extraction Agents...")
agents = [
    'app.agents.extraction_agent_v2',
    'app.agents.extraction_agent_optimized',
    'app.agents.pdf_processor',
]

for agent in agents:
    try:
        __import__(agent)
        print(f"  [OK] {agent}")
    except Exception as e:
        print(f"  [ERROR] {agent}: {str(e)[:50]}")

# Test 5: Test PDF processing capability
print("\n5. Testing PDF Processing...")
try:
    import pypdf
    print(f"  [OK] pypdf version: {pypdf.__version__}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 6: Check database
print("\n6. Checking Database...")
try:
    from app.core.database import SessionLocal
    from app.models.assessment import VendorAssessment, FinancialStatement

    db = SessionLocal()
    assessment_count = db.query(VendorAssessment).count()
    statement_count = db.query(FinancialStatement).count()

    print(f"  [OK] Database accessible")
    print(f"  Assessments: {assessment_count}")
    print(f"  Financial Statements: {statement_count}")

    # Check for statements with errors
    error_statements = db.query(FinancialStatement).filter(
        FinancialStatement.error_message.isnot(None)
    ).all()

    if error_statements:
        print(f"\n  Found {len(error_statements)} statements with errors:")
        for stmt in error_statements[:3]:
            print(f"    - ID {stmt.id}: {stmt.error_message[:60]}")

    db.close()
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)

# Summary
print("\nNEXT STEPS:")
if missing:
    print(f"1. Install missing modules: {', '.join(missing)}")
if not has_key:
    print("2. Configure OPENAI_API_KEY in backend/.env")
print("3. Try uploading a PDF and check server logs for errors")
print("4. If still failing, share the exact error message")
