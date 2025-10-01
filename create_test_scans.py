#!/usr/bin/env python3
"""
Create test scans to verify the frontend displays separate time-in and time-out events
"""

from app import create_app, db
from app.models import AttendanceEvent, AttendanceRecord, Student, Room
from app.services.attendance_state_service import AttendanceStateService
import sys
import time

def create_test_scans():
    """Create test scans to verify frontend display"""
    print("🧪 CREATING TEST SCANS FOR FRONTEND VERIFICATION")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get test data
            student = Student.query.first()
            room = Room.query.first()
            
            if not student or not room:
                print("❌ No test data available")
                return False
            
            print(f"Using: {student.get_full_name()} in {room.room_name}")
            
            # Clean up any existing data for this test
            AttendanceEvent.query.filter_by(student_id=student.id, room_id=room.id).delete()
            AttendanceRecord.query.filter_by(student_id=student.id, room_id=room.id).delete()
            db.session.commit()
            
            print("🔄 Creating time-in event...")
            
            # Create time-in
            result1 = AttendanceStateService.process_attendance_scan(
                student_id=student.id,
                room_id=room.id,
                session_id=None,
                scanned_by=1,
                ip_address="127.0.0.1",
                user_agent="Frontend Test"
            )
            
            if result1['success']:
                print(f"   ✅ {result1['message']}")
            else:
                print(f"   ❌ Time-in failed: {result1['message']}")
                return False
            
            print("⏳ Waiting 7 seconds before time-out...")
            time.sleep(7)
            
            print("🔄 Creating time-out event...")
            
            # Create time-out
            result2 = AttendanceStateService.process_attendance_scan(
                student_id=student.id,
                room_id=room.id,
                session_id=None,
                scanned_by=1,
                ip_address="127.0.0.1",
                user_agent="Frontend Test"
            )
            
            if result2['success']:
                print(f"   ✅ {result2['message']}")
            else:
                print(f"   ❌ Time-out failed: {result2['message']}")
                return False
            
            # Verify events were created
            events = AttendanceEvent.query.filter_by(
                student_id=student.id,
                room_id=room.id
            ).order_by(AttendanceEvent.event_time.desc()).all()
            
            print(f"\n📊 Created {len(events)} events:")
            for event in events:
                event_type = event.event_type.replace('_', '-').title()
                event_time = event.event_time.strftime('%H:%M:%S')
                print(f"   {event_type}: {event_time}")
            
            if len(events) == 2:
                print("\n✅ SUCCESS: Test scans created successfully!")
                print("🌐 You can now check the scanner frontend to see separate time-in and time-out entries")
                print("📍 URL: http://127.0.0.1:5000/scanner")
                return True
            else:
                print(f"\n❌ Expected 2 events, got {len(events)}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating test scans: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = create_test_scans()
    if success:
        print("\n🎉 Test scans created! Check the scanner frontend.")
    else:
        print("\n❌ Failed to create test scans!")
        sys.exit(1)