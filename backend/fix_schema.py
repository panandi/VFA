"""
Quick fix to add missing columns to risk_assessments table.
Run this while the server is STOPPED.
"""
import sqlite3
import os

def fix_schema():
    db_path = 'vfa.db'

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False

    print("Adding missing columns to risk_assessments table...")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # List of columns to add
        columns_to_add = [
            ("company_type", "VARCHAR(20) DEFAULT 'private'"),
            ("working_capital_ratio", "FLOAT"),
            ("retained_earnings_to_assets", "FLOAT"),
            ("sales_to_working_capital", "FLOAT"),
            ("creditors_to_sales", "FLOAT"),
            ("growth_sales", "FLOAT"),
            ("growth_net_profit", "FLOAT"),
            ("growth_gross_profit_margin", "FLOAT"),
            ("growth_net_profit_margin", "FLOAT"),
            ("ratios_detail", "JSON"),
            ("previous_fiscal_year_used", "INTEGER"),
        ]

        # Check existing columns
        cursor.execute("PRAGMA table_info(risk_assessments)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        # Add missing columns
        added = 0
        skipped = 0

        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE risk_assessments ADD COLUMN {col_name} {col_type}")
                    print(f"  + Added: {col_name}")
                    added += 1
                except Exception as e:
                    print(f"  x Failed to add {col_name}: {e}")
            else:
                print(f"  - Skipped: {col_name} (already exists)")
                skipped += 1

        conn.commit()
        conn.close()

        print(f"\nCompleted: {added} columns added, {skipped} already existed")

        # Verify
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(risk_assessments)")
        final_columns = cursor.fetchall()
        conn.close()

        print(f"\nFinal schema: {len(final_columns)} columns in risk_assessments table")

        return True

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SCHEMA FIX SCRIPT")
    print("=" * 60)
    print("\nIMPORTANT: Make sure the backend server is STOPPED!")
    print("Press Enter to continue or Ctrl+C to cancel...")
    input()

    success = fix_schema()

    if success:
        print("\n" + "=" * 60)
        print("SUCCESS! You can now restart the backend server.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("FAILED! Check the error messages above.")
        print("=" * 60)

    exit(0 if success else 1)
