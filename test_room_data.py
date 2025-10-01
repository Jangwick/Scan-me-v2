#!/usr/bin/env python3
"""
Test script to check room data and floor types
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Room, AttendanceSession
import traceback

def test_room_data():
    """Test room data to identify floor type issues"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing room data...")
            
            # Get all rooms
            rooms = Room.query.all()
            print(f"Found {len(rooms)} rooms")
            
            for room in rooms:
                print(f"\nRoom {room.id}: {room.room_number}")
                print(f"  Building: {room.building}")
                print(f"  Floor: {room.floor} (type: {type(room.floor)})")
                
                try:
                    # Test the method that might be causing issues
                    location = room.get_location()
                    print(f"  Location: {location}")
                except Exception as e:
                    print(f"  ERROR getting location: {e}")
                    traceback.print_exc()
                    
            # Also test sessions that reference rooms
            print("\n--- Testing sessions with rooms ---")
            sessions = AttendanceSession.query.filter(AttendanceSession.room_id.isnot(None)).all()
            print(f"Found {len(sessions)} sessions with rooms")
            
            for session in sessions:
                print(f"\nSession {session.id}: {session.subject}")
                if session.room:
                    print(f"  Room: {session.room.room_number}")
                    print(f"  Floor: {session.room.floor} (type: {type(session.room.floor)})")
                    try:
                        location = session.room.get_location()
                        print(f"  Location: {location}")
                    except Exception as e:
                        print(f"  ERROR: {e}")
                        traceback.print_exc()
                        
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_room_data()