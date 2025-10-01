#!/usr/bin/env python3
"""
Debug recent scans to see what events are currently stored
"""

from app import create_app, db
from app.models import AttendanceEvent, AttendanceRecord, Student, Room
import sys

def debug_recent_events():
    """Debug what's currently in the AttendanceEvent table"""
    print("🔍 DEBUGGING RECENT SCAN EVENTS")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get all attendance events
            all_events = AttendanceEvent.query.order_by(AttendanceEvent.event_time.desc()).limit(20).all()
            
            print(f"📊 Found {len(all_events)} recent events in AttendanceEvent table:")
            
            if not all_events:
                print("❌ No events found in AttendanceEvent table!")
                
                # Check if we have any AttendanceRecords
                records = AttendanceRecord.query.order_by(AttendanceRecord.created_at.desc()).limit(5).all()
                print(f"\n📊 Found {len(records)} recent AttendanceRecords:")
                
                for record in records:
                    print(f"   Record ID {record.id}: {record.student.get_full_name()} in {record.room.room_name}")
                    print(f"      Time In: {record.time_in}")
                    print(f"      Time Out: {record.time_out}")
                    print(f"      Is Active: {record.is_active}")
                    print()
                
                return False
            
            print("\nEvent Details:")
            print("-" * 50)
            
            for i, event in enumerate(all_events, 1):
                student_name = event.student.get_full_name()
                room_name = event.room.room_name
                event_type = event.event_type
                event_time = event.event_time.strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"{i:2d}. {event_type.upper()}: {student_name} in {room_name}")
                print(f"    Time: {event_time}")
                print(f"    ID: {event.id}")
                if event.duration_minutes:
                    print(f"    Duration: {event.duration_minutes} minutes")
                print()
            
            # Check for duplicate events (same student/room/time)
            print("\n🔍 Checking for issues...")
            
            students_events = {}
            for event in all_events:
                key = f"{event.student.get_full_name()}-{event.room.room_name}"
                if key not in students_events:
                    students_events[key] = []
                students_events[key].append(event)
            
            for student_room, events in students_events.items():
                if len(events) > 1:
                    print(f"📋 {student_room}: {len(events)} events")
                    for event in events:
                        print(f"   - {event.event_type} at {event.event_time.strftime('%H:%M:%S')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error debugging events: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    debug_recent_events()