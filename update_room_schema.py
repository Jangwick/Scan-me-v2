#!/usr/bin/env python3
"""
Database migration script to make room_name nullable
This script updates the rooms table to make the room_name column optional
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def update_room_schema():
    """Update the rooms table to make room_name nullable"""
    
    db_path = os.path.join(project_root, 'instance', 'scanme.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False
    
    print(f"Updating database schema at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the rooms table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='rooms';
        """)
        
        if not cursor.fetchone():
            print("Rooms table does not exist yet. Schema will be created correctly when the app runs.")
            conn.close()
            return True
        
        # Check current schema
        cursor.execute("PRAGMA table_info(rooms)")
        columns = cursor.fetchall()
        
        print("Current rooms table schema:")
        for col in columns:
            print(f"  {col[1]} - {col[2]} - {'NOT NULL' if col[3] else 'NULL'}")
        
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # First, backup existing data
        cursor.execute("SELECT * FROM rooms")
        existing_data = cursor.fetchall()
        
        # Get the original column names
        cursor.execute("PRAGMA table_info(rooms)")
        original_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\nFound {len(existing_data)} existing rooms to preserve")
        
        # Create new table with updated schema
        cursor.execute("""
            CREATE TABLE rooms_new (
                id INTEGER PRIMARY KEY,
                room_number VARCHAR(20) UNIQUE NOT NULL,
                room_name VARCHAR(100),
                building VARCHAR(50) NOT NULL,
                floor INTEGER NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 30,
                room_type VARCHAR(30) NOT NULL DEFAULT 'classroom',
                equipment TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Copy data from old table to new table
        if existing_data:
            # Prepare insert statement
            placeholders = ','.join(['?' for _ in original_columns])
            insert_sql = f"INSERT INTO rooms_new ({','.join(original_columns)}) VALUES ({placeholders})"
            
            for row in existing_data:
                cursor.execute(insert_sql, row)
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE rooms")
        cursor.execute("ALTER TABLE rooms_new RENAME TO rooms")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_rooms_room_number ON rooms (room_number)")
        
        conn.commit()
        print("✅ Successfully updated rooms table schema!")
        print("✅ room_name column is now nullable")
        
        # Verify the update
        cursor.execute("PRAGMA table_info(rooms)")
        updated_columns = cursor.fetchall()
        
        print("\nUpdated rooms table schema:")
        for col in updated_columns:
            print(f"  {col[1]} - {col[2]} - {'NOT NULL' if col[3] else 'NULL'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database schema: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    print("Room Schema Update Script")
    print("=" * 40)
    
    success = update_room_schema()
    
    if success:
        print("\n🎉 Database schema update completed successfully!")
        print("The 'Add Room' form should now work properly with optional room names.")
    else:
        print("\n❌ Database schema update failed!")
        print("Please check the error messages above.")