"""
Quick Database Migration for Time-In/Time-Out Feature
Adds new columns to the attendance_records table using raw SQL
"""

import sqlite3
import os

def migrate_database():
    """Add new columns to attendance_records table"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'scanme.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database file not found. Creating new database with updated schema...")
        return
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(attendance_records)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {columns}")
        
        # Add missing columns
        migrations = []
        
        if 'time_in' not in columns:
            migrations.append("ALTER TABLE attendance_records ADD COLUMN time_in DATETIME")
        
        if 'time_out' not in columns:
            migrations.append("ALTER TABLE attendance_records ADD COLUMN time_out DATETIME")
        
        if 'is_active' not in columns:
            migrations.append("ALTER TABLE attendance_records ADD COLUMN is_active BOOLEAN DEFAULT 1")
            
        if 'time_in_scanned_by' not in columns:
            migrations.append("ALTER TABLE attendance_records ADD COLUMN time_in_scanned_by INTEGER")
            
        if 'time_out_scanned_by' not in columns:
            migrations.append("ALTER TABLE attendance_records ADD COLUMN time_out_scanned_by INTEGER")
        
        # Execute migrations
        if migrations:
            print(f"Running {len(migrations)} migrations...")
            for migration in migrations:
                print(f"  Executing: {migration}")
                cursor.execute(migration)
            
            # Update existing data
            print("Updating existing records...")
            
            # Copy scan_time to time_in where time_in is NULL
            cursor.execute("""
                UPDATE attendance_records 
                SET time_in = scan_time 
                WHERE time_in IS NULL
            """)
            
            # Copy scanned_by to time_in_scanned_by where time_in_scanned_by is NULL
            cursor.execute("""
                UPDATE attendance_records 
                SET time_in_scanned_by = scanned_by 
                WHERE time_in_scanned_by IS NULL
            """)
            
            # Set existing records as inactive (completed visits)
            cursor.execute("""
                UPDATE attendance_records 
                SET is_active = 0 
                WHERE is_active IS NULL
            """)
            
            conn.commit()
            print("✅ Migration completed successfully!")
            
            # Verify the migration
            cursor.execute("PRAGMA table_info(attendance_records)")
            new_columns = [row[1] for row in cursor.fetchall()]
            print(f"Updated columns: {new_columns}")
            
        else:
            print("✅ No migration needed - all columns already exist!")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()