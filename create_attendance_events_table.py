#!/usr/bin/env python3
"""
Create AttendanceEvent table migration
This script adds the AttendanceEvent table for audit trail functionality
"""

from app import create_app, db
from app.models import AttendanceEvent
import sys

def create_attendance_events_table():
    """Create the AttendanceEvent table"""
    print("Creating AttendanceEvent table...")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if table already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'attendance_event' in existing_tables:
                print("✓ AttendanceEvent table already exists")
                return True
            
            # Create the AttendanceEvent table
            print("Creating AttendanceEvent table...")
            AttendanceEvent.__table__.create(db.engine)
            print("✓ AttendanceEvent table created successfully")
            
            # Verify table was created
            inspector = inspect(db.engine)
            updated_tables = inspector.get_table_names()
            
            if 'attendance_event' in updated_tables:
                print("✓ Table creation verified")
                
                # Show table structure
                columns = inspector.get_columns('attendance_event')
                print("\nTable structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
                
                return True
            else:
                print("❌ Table creation failed - table not found after creation")
                return False
                
        except Exception as e:
            print(f"❌ Error creating AttendanceEvent table: {str(e)}")
            return False

if __name__ == '__main__':
    success = create_attendance_events_table()
    if success:
        print("\n🎉 AttendanceEvent table migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)