#!/usr/bin/env python3
"""
Database migration script to add session scheduling tables
"""

import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models.session_schedule_model import SessionSchedule

def create_scheduling_tables():
    """Create the session scheduling tables"""
    
    print("🔧 Creating Session Scheduling Tables")
    print("=" * 50)
    
    try:
        app = create_app()
        
        with app.app_context():
            # Create all tables
            db.create_all()
            
            print("✅ Session scheduling tables created successfully!")
            print("\n📋 Available tables:")
            
            # List all tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            
            for table_name in sorted(table_names):
                print(f"  - {table_name}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_scheduling_tables()
    
    if success:
        print("\n🎉 Database migration completed successfully!")
        print("\nNew Features Available:")
        print("1. 📅 Session Scheduling")
        print("2. 🔄 Recurring Sessions") 
        print("3. 📊 Room Availability Checking")
        print("4. ⏰ Attendance Time Windows")
    else:
        print("\n❌ Database migration failed!")