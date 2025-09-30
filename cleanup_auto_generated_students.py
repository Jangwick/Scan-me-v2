#!/usr/bin/env python3
"""
Cleanup Script for Auto-Generated Students
Removes students that were automatically created by the demo/testing logic
"""

from app import create_app
from app.models import Student, AttendanceRecord
from app import db

def cleanup_auto_generated_students():
    """Remove auto-generated students and their attendance records"""
    
    app = create_app()
    
    with app.app_context():
        print("🧹 CLEANUP AUTO-GENERATED STUDENTS")
        print("=" * 50)
        
        # Find auto-generated students
        auto_generated = Student.query.filter(
            (Student.section == 'Auto-Generated') |
            (Student.department == 'General') & 
            (Student.first_name == 'Student')
        ).all()
        
        print(f"Found {len(auto_generated)} auto-generated students:")
        
        for student in auto_generated:
            print(f"  - {student.get_full_name()} ({student.student_no})")
            print(f"    Section: {student.section}")
            print(f"    Department: {student.department}")
            print(f"    Email: {student.email}")
            
            # Check if student has attendance records
            attendance_count = AttendanceRecord.query.filter_by(student_id=student.id).count()
            print(f"    Attendance records: {attendance_count}")
            print()
        
        if not auto_generated:
            print("✅ No auto-generated students found!")
            return
        
        # Ask for confirmation
        confirm = input(f"\n⚠️  Delete all {len(auto_generated)} auto-generated students? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            try:
                deleted_count = 0
                deleted_attendance = 0
                
                for student in auto_generated:
                    # Delete attendance records first (due to foreign key constraints)
                    attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).all()
                    for record in attendance_records:
                        db.session.delete(record)
                        deleted_attendance += 1
                    
                    # Delete the student
                    print(f"🗑️  Deleting: {student.get_full_name()} ({student.student_no})")
                    db.session.delete(student)
                    deleted_count += 1
                
                # Commit all deletions
                db.session.commit()
                
                print(f"\n✅ Successfully deleted:")
                print(f"   - {deleted_count} auto-generated students")
                print(f"   - {deleted_attendance} associated attendance records")
                print(f"\n🎉 Cleanup completed!")
                
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error during cleanup: {str(e)}")
                print("🔄 Database rolled back - no changes made")
        
        else:
            print("\n🚫 Cleanup cancelled - no students deleted")
            
            # Offer to deactivate instead
            deactivate = input("Would you like to deactivate them instead? (yes/no): ").lower().strip()
            
            if deactivate in ['yes', 'y']:
                try:
                    for student in auto_generated:
                        student.is_active = False
                        print(f"🔒 Deactivated: {student.get_full_name()}")
                    
                    db.session.commit()
                    print(f"\n✅ Deactivated {len(auto_generated)} auto-generated students")
                    print("They will no longer appear in active student lists")
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"\n❌ Error during deactivation: {str(e)}")

def restore_auto_generated_students():
    """Restore (reactivate) auto-generated students if needed"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 RESTORE AUTO-GENERATED STUDENTS")
        print("=" * 50)
        
        # Find deactivated auto-generated students
        deactivated = Student.query.filter(
            (Student.is_active == False) &
            ((Student.section == 'Auto-Generated') |
            ((Student.department == 'General') & 
            (Student.first_name == 'Student')))
        ).all()
        
        if not deactivated:
            print("✅ No deactivated auto-generated students found!")
            return
        
        print(f"Found {len(deactivated)} deactivated auto-generated students:")
        for student in deactivated:
            print(f"  - {student.get_full_name()} ({student.student_no})")
        
        confirm = input(f"\nReactivate all {len(deactivated)} students? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            try:
                for student in deactivated:
                    student.is_active = True
                    print(f"🔓 Reactivated: {student.get_full_name()}")
                
                db.session.commit()
                print(f"\n✅ Reactivated {len(deactivated)} students")
                
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error during reactivation: {str(e)}")
        else:
            print("\n🚫 Reactivation cancelled")

if __name__ == "__main__":
    import sys
    
    print("🎯 AUTO-GENERATED STUDENT CLEANUP UTILITY")
    print("=" * 50)
    print("This script helps manage students that were automatically created")
    print("by the previous demo/testing auto-creation logic.")
    print()
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == 'restore':
            restore_auto_generated_students()
        else:
            print("Usage: python cleanup_auto_generated_students.py [restore]")
    else:
        cleanup_auto_generated_students()