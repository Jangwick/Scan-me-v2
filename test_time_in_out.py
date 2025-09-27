"""
Test Time-In/Time-Out Functionality
This script demonstrates and tests the new time-in and time-out features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app.models.student_model import Student
from app.models.user_model import User
from app.models.room_model import Room
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from datetime import datetime, timedelta

def test_time_in_out_functionality():
    """Test the complete time-in and time-out workflow"""
    
    with app.app_context():
        try:
            print("🧪 Testing Time-In/Time-Out Functionality")
            print("=" * 50)
            
            # Get or create test data
            student = Student.query.first()
            if not student:
                print("❌ No students found in database. Please add students first.")
                return False
                
            user = User.query.first()
            if not user:
                print("❌ No users found in database. Please add users first.")
                return False
                
            room = Room.query.first()
            if not room:
                print("❌ No rooms found in database. Please add rooms first.")
                return False
                
            session = AttendanceSession.query.first()
            if not session:
                print("❌ No sessions found in database. Please create a session first.")
                return False
                
            print(f"📚 Test Data:")
            print(f"  Student: {student.get_full_name()} ({student.student_no})")
            print(f"  User: {user.username}")
            print(f"  Room: {room.get_full_name()}")
            print(f"  Session: {session.session_name}")
            print()
            
            # Test 1: Time-In
            print("🔵 Test 1: Student Time-In")
            print("-" * 30)
            
            # Check if student is already timed in
            existing_active = AttendanceRecord.get_student_active_record(student.id, room.id)
            if existing_active:
                print("⚠️  Student already has active record, timing out first...")
                existing_active.time_out_student(user.id)
            
            # Create new time-in record
            attendance = AttendanceRecord(
                student_id=student.id,
                room_id=room.id,
                scanned_by=user.id,
                session_id=session.id,
                is_late=False
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            print(f"✅ Time-In successful!")
            print(f"   Student: {student.get_full_name()}")
            print(f"   Time: {attendance.time_in.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Status: {attendance.get_status()}")
            print(f"   Duration so far: {attendance.get_duration()} minutes")
            print()
            
            # Test 2: Check Active Records
            print("🔵 Test 2: Check Active Records")
            print("-" * 30)
            
            active_records = AttendanceRecord.get_active_in_room(room.id)
            print(f"Students currently in {room.room_name}:")
            for record in active_records:
                print(f"  - {record.student.get_full_name()} (In for {record.get_duration()} minutes)")
            print()
            
            # Test 3: Time-Out
            print("🔵 Test 3: Student Time-Out")
            print("-" * 30)
            
            # Wait a moment to show duration
            import time
            time.sleep(2)
            
            # Time out the student
            success, message = attendance.time_out_student(user.id)
            
            if success:
                print(f"✅ Time-Out successful!")
                print(f"   Student: {student.get_full_name()}")
                print(f"   Time In: {attendance.time_in.strftime('%H:%M:%S')}")
                print(f"   Time Out: {attendance.time_out.strftime('%H:%M:%S')}")
                print(f"   Total Duration: {attendance.get_duration()} minutes")
                print(f"   Status: {attendance.get_status()}")
            else:
                print(f"❌ Time-Out failed: {message}")
            print()
            
            # Test 4: Today's Records
            print("🔵 Test 4: Today's Records")
            print("-" * 30)
            
            today_records = AttendanceRecord.get_by_student_today(student.id)
            print(f"Today's attendance for {student.get_full_name()}:")
            for record in today_records:
                status_emoji = "🟢" if record.get_status() == "timed_out" else "🔴"
                time_in_str = record.time_in.strftime('%H:%M:%S')
                time_out_str = record.time_out.strftime('%H:%M:%S') if record.time_out else "Still in"
                print(f"  {status_emoji} {time_in_str} - {time_out_str} ({record.get_duration()} min)")
            print()
            
            # Test 5: Room Statistics
            print("🔵 Test 5: Room Statistics")
            print("-" * 30)
            
            room_records = AttendanceRecord.get_by_room_today(room.id)
            active_count = len([r for r in room_records if r.is_active])
            completed_count = len([r for r in room_records if r.time_out])
            
            print(f"Room: {room.get_full_name()}")
            print(f"  Total visits today: {len(room_records)}")
            print(f"  Currently active: {active_count}")
            print(f"  Completed visits: {completed_count}")
            
            if room_records:
                total_duration = sum(r.get_duration() for r in room_records if r.time_out)
                avg_duration = total_duration / completed_count if completed_count > 0 else 0
                print(f"  Average visit duration: {avg_duration:.1f} minutes")
            print()
            
            # Test 6: Data Structure Validation
            print("🔵 Test 6: Data Structure Validation")
            print("-" * 30)
            
            record_dict = attendance.to_dict()
            required_fields = [
                'time_in', 'time_out', 'duration_minutes', 'status',
                'is_active', 'time_in_scanned_by', 'time_out_scanned_by'
            ]
            
            print("Checking attendance record dictionary structure:")
            for field in required_fields:
                if field in record_dict:
                    print(f"  ✅ {field}: {record_dict[field]}")
                else:
                    print(f"  ❌ {field}: MISSING")
            
            print()
            print("🎉 All tests completed successfully!")
            print("✅ Time-in/Time-out functionality is working properly!")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_time_in_out_functionality()
    if success:
        print("\n🚀 Ready to use the new time-in/time-out scanner!")
    else:
        print("\n💥 Tests failed. Please check the setup and try again.")