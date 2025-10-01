#!/usr/bin/env python3
"""
Test script to examine database schema and data types
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
import traceback

def examine_database_schema():
    """Examine database schema and data types"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Examining database schema and data...")
            
            # Check the database engine
            engine = db.engine
            print(f"Database engine: {engine}")
            
            # Get table information
            from sqlalchemy import inspect
            inspector = inspect(engine)
            
            # Check all tables
            tables = inspector.get_table_names()
            print(f"Found tables: {tables}")
            
            # Focus on key tables that might have integer fields
            for table_name in ['rooms', 'attendance_sessions', 'students']:
                if table_name in tables:
                    print(f"\n--- {table_name.upper()} TABLE ---")
                    columns = inspector.get_columns(table_name)
                    
                    for column in columns:
                        print(f"  {column['name']}: {column['type']} (nullable: {column['nullable']})")
                        
                    # Sample some data
                    result = db.engine.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = result.fetchall()
                    print(f"  Sample data ({len(rows)} rows):")
                    for i, row in enumerate(rows):
                        print(f"    Row {i+1}: {dict(row)}")
                        
                        # Check specific fields that might be problematic
                        if table_name == 'rooms' and 'floor' in dict(row):
                            floor_val = dict(row)['floor']
                            print(f"      Floor value: {floor_val} (type: {type(floor_val)})")
                            
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    examine_database_schema()