#!/usr/bin/env python3
"""
Clean up test data and reset for fresh testing
"""

from app import create_app, db
from app.models import AttendanceEvent, AttendanceRecord, Student, Room
import sys

def cleanup_test_data():
    """Clean up test data for fresh testing"""
    print("Cleaning up test data...")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get John Smith for cleanup
            john = Student.query.filter_by(first_name='John', last_name='Smith').first()
            computer_lab = Room.query.filter_by(room_name='Computer Lab').first()
            
            if john and computer_lab:
                print(f"Cleaning up data for: {john.get_full_name()} in {computer_lab.room_name}")
                
                # Delete all events for this student/room
                events_deleted = AttendanceEvent.query.filter_by(
                    student_id=john.id,
                    room_id=computer_lab.id
                ).delete()
                
                # Delete all records for this student/room
                records_deleted = AttendanceRecord.query.filter_by(
                    student_id=john.id,
                    room_id=computer_lab.id
                ).delete()
                
                db.session.commit()
                
                print(f"✓ Deleted {events_deleted} events")
                print(f"✓ Deleted {records_deleted} records")
                
                # Verify cleanup
                remaining_events = AttendanceEvent.query.filter_by(
                    student_id=john.id,
                    room_id=computer_lab.id
                ).count()
                
                remaining_records = AttendanceRecord.query.filter_by(
                    student_id=john.id,
                    room_id=computer_lab.id
                ).count()
                
                print(f"✓ Remaining events: {remaining_events}")
                print(f"✓ Remaining records: {remaining_records}")
                
                return True
            else:
                print("❌ Could not find John Smith or Computer Lab")
                return False
                
        except Exception as e:
            print(f"❌ Error during cleanup: {str(e)}")
            return False

if __name__ == '__main__':
    success = cleanup_test_data()
    if success:
        print("\n🧹 Cleanup completed successfully!")
    else:
        print("\n❌ Cleanup failed!")
        sys.exit(1)