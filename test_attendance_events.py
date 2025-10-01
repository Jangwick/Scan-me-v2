#!/usr/bin/env python3
"""
Test AttendanceEvent functionality
This script tests that time-in and time-out events are created separately
"""

from app import create_app, db
from app.models import AttendanceEvent, AttendanceRecord, Student, Room
from app.services.attendance_state_service import AttendanceStateService
import sys

def test_attendance_events():
    """Test that attendance events are created properly"""
    print("Testing AttendanceEvent functionality...")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get a test student and room
            student = Student.query.first()
            room = Room.query.first()
            
            if not student or not room:
                print("❌ No student or room found for testing")
                return False
            
            print(f"Using student: {student.get_full_name()} ({student.student_no})")
            print(f"Using room: {room.room_name}")
            
            # Count existing events
            initial_event_count = AttendanceEvent.query.count()
            initial_record_count = AttendanceRecord.query.count()
            
            print(f"Initial event count: {initial_event_count}")
            print(f"Initial record count: {initial_record_count}")
            
            # Test time-in (simulate QR scan)
            print("\n--- Testing Time-In ---")
            result = AttendanceStateService.process_attendance_scan(
                student_id=student.id,
                room_id=room.id,
                session_id=None,  # No specific session
                scanned_by=1,  # Assuming admin user ID is 1
                ip_address="127.0.0.1",
                user_agent="Test"
            )
            
            if result['success']:
                print(f"✓ Time-in successful: {result['message']}")
            else:
                print(f"❌ Time-in failed: {result['message']}")
                return False
            
            # Check events after time-in
            events_after_time_in = AttendanceEvent.query.count()
            print(f"Events after time-in: {events_after_time_in}")
            
            # Get the latest time-in event
            time_in_event = AttendanceEvent.query.filter_by(
                student_id=student.id,
                room_id=room.id,
                event_type='time_in'
            ).order_by(AttendanceEvent.event_time.desc()).first()
            
            if time_in_event:
                print(f"✓ Time-in event created: {time_in_event.event_time}")
            else:
                print("❌ No time-in event found")
                return False
            
            # Test time-out (simulate another QR scan)
            print("\n--- Testing Time-Out ---")
            print("Waiting 6 seconds to avoid rate limiting...")
            import time
            time.sleep(6)
            
            result = AttendanceStateService.process_attendance_scan(
                student_id=student.id,
                room_id=room.id,
                session_id=None,  # No specific session
                scanned_by=1,  # Assuming admin user ID is 1
                ip_address="127.0.0.1",
                user_agent="Test"
            )
            
            if result['success']:
                print(f"✓ Time-out successful: {result['message']}")
            else:
                print(f"❌ Time-out failed: {result['message']}")
                return False
            
            # Check events after time-out
            final_event_count = AttendanceEvent.query.count()
            print(f"Final event count: {final_event_count}")
            
            # Get the latest time-out event
            time_out_event = AttendanceEvent.query.filter_by(
                student_id=student.id,
                room_id=room.id,
                event_type='time_out'
            ).order_by(AttendanceEvent.event_time.desc()).first()
            
            if time_out_event:
                print(f"✓ Time-out event created: {time_out_event.event_time}")
            else:
                print("❌ No time-out event found")
                return False
            
            # Show all events for this student/room
            print("\n--- All Events for this test ---")
            all_events = AttendanceEvent.query.filter_by(
                student_id=student.id,
                room_id=room.id
            ).order_by(AttendanceEvent.event_time.desc()).limit(5).all()
            
            for event in all_events:
                print(f"  {event.event_type}: {event.event_time} (ID: {event.id})")
            
            # Verify we created exactly 2 new events
            expected_new_events = final_event_count - initial_event_count
            if expected_new_events == 2:
                print(f"✓ Correct number of events created: {expected_new_events}")
                return True
            else:
                print(f"❌ Expected 2 new events, but got {expected_new_events}")
                return False
                
        except Exception as e:
            print(f"❌ Error during test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_attendance_events()
    if success:
        print("\n🎉 AttendanceEvent test completed successfully!")
        print("Separate time-in and time-out events are working!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)