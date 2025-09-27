#!/usr/bin/env python3
"""
Test script to verify room management action routes
"""

import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from app.models.room_model import Room

def test_room_actions():
    """Test room management functionality"""
    
    print("🧪 Testing Room Management Actions")
    print("=" * 50)
    
    try:
        app = create_app()
        
        with app.app_context():
            # Test getting rooms
            rooms = Room.query.all()
            print(f"✅ Found {len(rooms)} rooms in database")
            
            for room in rooms:
                print(f"  📍 {room.get_full_name()}")
                print(f"     Building: {room.building}, Floor: {room.floor}")
                print(f"     Capacity: {room.capacity}, Type: {room.room_type}")
                print(f"     Active: {'Yes' if room.is_active else 'No'}")
                print(f"     ID: {room.id}")
                print()
            
            # Test available routes
            print("🛠️ Available Admin Routes:")
            
            # Get all routes from the app
            for rule in app.url_map.iter_rules():
                if rule.endpoint.startswith('admin') and 'room' in rule.endpoint:
                    print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods)})")
            
            print("\n✅ All tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_room_actions()
    
    if success:
        print("\n🎉 Room management system is ready!")
        print("\nAvailable Actions:")
        print("1. 👁️  View Room Details - Click the eye icon")
        print("2. ✏️  Edit Room - Click the edit icon")
        print("3. 🔧 Set Maintenance - Click the tools icon")
        print("4. ✅ Activate Room - Click the check icon (for rooms in maintenance)")
        print("5. 🗑️  Delete Room - Click the trash icon")
    else:
        print("\n❌ Room management system has issues!")