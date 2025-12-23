"""
Database migration script to update schema to match current models.
Run this script with the backend server STOPPED.
"""
import os
import shutil
import sqlite3
from datetime import datetime

def migrate_database():
    db_path = 'vfa.db'
    backup_path = f'vfa.db.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"\n✓ No existing database found at {db_path}")
        print("  Creating fresh database...")
    else:
        print(f"\n! Found existing database: {db_path}")

        # Try to backup
        try:
            # First, backup existing users data
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT id, email, hashed_password, full_name, initials, is_active, is_superuser FROM users")
            users = cursor.fetchall()

            conn.close()

            print(f"  - Backed up {len(users)} users")

            # Backup the file
            shutil.copy2(db_path, backup_path)
            print(f"  - Created backup: {backup_path}")

            # Remove old database
            os.remove(db_path)
            print(f"  - Removed old database")

        except Exception as e:
            print(f"\n✗ Error during backup: {e}")
            print("\nPlease ensure:")
            print("  1. The backend server is STOPPED")
            print("  2. No other process is accessing vfa.db")
            return False

    # Create new database with correct schema
    print("\n→ Creating new database with updated schema...")

    try:
        from app.core.database import engine, Base
        from app.models import (
            User, VendorAssessment, FinancialStatement,
            ExtractedFinancialData, QualitativeResponse,
            RiskAssessment, Recommendation
        )

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("  ✓ Database tables created")

        # Verify schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(risk_assessments)")
        columns = [col[1] for col in cursor.fetchall()]

        required_columns = ['company_type', 'working_capital_ratio', 'ratios_detail']
        missing = [col for col in required_columns if col not in columns]

        if missing:
            print(f"\n✗ Schema verification failed - missing columns: {missing}")
            conn.close()
            return False

        print(f"  ✓ Schema verified ({len(columns)} columns in risk_assessments)")

        # Restore users if we had any
        if 'users' in locals() and users:
            print(f"\n→ Restoring {len(users)} users...")
            for user in users:
                cursor.execute(
                    "INSERT INTO users (id, email, hashed_password, full_name, initials, is_active, is_superuser) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    user
                )
            conn.commit()
            print(f"  ✓ Restored {len(users)} users")

        conn.close()

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now start the backend server.")
        return True

    except Exception as e:
        print(f"\n✗ Error creating database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)
