"""
Database Migration Script for Time-In/Time-Out Feature
Adds new columns to attendance_records table to support time-in and time-out functionality
"""

from app import app, db
from app.models.attendance_model import AttendanceRecord
from datetime import datetime

def migrate_database():
    """Run database migration to add time-in/time-out columns"""
    
    with app.app_context():
        try:
            print("Starting database migration for time-in/time-out feature...")
            
            # Check if we need to add new columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('attendance_records')]
            
            migrations_needed = []
            
            # Check for missing columns
            required_columns = [
                ('time_in', 'DATETIME'),
                ('time_out', 'DATETIME'),
                ('is_active', 'BOOLEAN DEFAULT TRUE'),
                ('time_in_scanned_by', 'INTEGER'),
                ('time_out_scanned_by', 'INTEGER')
            ]
            
            for col_name, col_type in required_columns:
                if col_name not in columns:
                    migrations_needed.append((col_name, col_type))
            
            if migrations_needed:
                print(f"Adding {len(migrations_needed)} new columns...")
                
                # Add missing columns
                for col_name, col_type in migrations_needed:
                    try:
                        if col_name == 'time_in':
                            # Copy scan_time to time_in for existing records
                            db.engine.execute(f'ALTER TABLE attendance_records ADD COLUMN {col_name} {col_type}')
                            db.engine.execute(f'UPDATE attendance_records SET time_in = scan_time WHERE time_in IS NULL')
                        elif col_name == 'time_in_scanned_by':
                            # Copy scanned_by to time_in_scanned_by for existing records
                            db.engine.execute(f'ALTER TABLE attendance_records ADD COLUMN {col_name} {col_type}')
                            db.engine.execute(f'UPDATE attendance_records SET time_in_scanned_by = scanned_by WHERE time_in_scanned_by IS NULL')
                        elif col_name == 'is_active':
                            # Set all existing records to inactive (they are historical records)
                            db.engine.execute(f'ALTER TABLE attendance_records ADD COLUMN {col_name} {col_type}')
                            db.engine.execute(f'UPDATE attendance_records SET is_active = FALSE WHERE is_active IS NULL')
                        else:
                            db.engine.execute(f'ALTER TABLE attendance_records ADD COLUMN {col_name} {col_type}')
                        
                        print(f"✅ Added column: {col_name}")
                        
                    except Exception as e:
                        print(f"❌ Failed to add column {col_name}: {str(e)}")
                        
                print("✅ Database migration completed successfully!")
                print("\n📋 Migration Summary:")
                print("- Added time_in column (copied from scan_time)")
                print("- Added time_out column (nullable)")
                print("- Added is_active column (default FALSE for existing records)")
                print("- Added time_in_scanned_by column (copied from scanned_by)")
                print("- Added time_out_scanned_by column (nullable)")
                
            else:
                print("✅ No migration needed - all columns already exist!")
                
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    migrate_database()