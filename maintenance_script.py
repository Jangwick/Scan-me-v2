"""
Attendance System Maintenance Script
Handles cleanup and monitoring for time-in/time-out edge cases

Run with: python maintenance_script.py [--cleanup] [--monitor] [--report]
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import json

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.attendance_model import AttendanceRecord, AttendanceSession
from app.models.student_model import Student
from app.models.room_model import Room
from app.services.attendance_state_service import AttendanceStateService
from app.services.time_management_service import TimeManagementService

class AttendanceMaintenanceManager:
    """Manager for attendance system maintenance operations"""
    
    def __init__(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.app_context.pop()
    
    def cleanup_orphaned_records(self, max_age_hours=24, dry_run=False):
        """Clean up orphaned active records"""
        print(f"🧹 Cleaning up orphaned records (max age: {max_age_hours}h)")
        print("=" * 50)
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        # Get orphaned records
        threshold_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        orphaned_records = AttendanceRecord.query.filter(
            AttendanceRecord.is_active == True,
            AttendanceRecord.time_in <= threshold_time
        ).all()
        
        print(f"Found {len(orphaned_records)} orphaned records")
        
        if not orphaned_records:
            print("✅ No orphaned records found")
            return {'cleaned_count': 0, 'success': True}
        
        # Display details
        for record in orphaned_records:
            student_name = record.student.get_full_name() if record.student else 'Unknown'
            room_name = record.room.get_full_name() if record.room else 'Unknown'
            duration_hours = (datetime.utcnow() - record.time_in).total_seconds() / 3600
            
            print(f"  - {student_name} in {room_name} (active for {duration_hours:.1f}h)")
        
        if dry_run:
            return {'cleaned_count': len(orphaned_records), 'success': True, 'dry_run': True}
        
        # Clean up records
        cleanup_result = AttendanceStateService.cleanup_orphaned_records(max_age_hours)
        
        if cleanup_result['success']:
            print(f"✅ Successfully cleaned up {cleanup_result['cleaned_count']} records")
        else:
            print(f"❌ Error during cleanup: {cleanup_result.get('error', 'Unknown error')}")
        
        return cleanup_result
    
    def fix_multiple_active_records(self, dry_run=False):
        """Fix students with multiple active records in the same room"""
        print("🔧 Fixing multiple active records")
        print("=" * 40)
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        # Find students with multiple active records per room
        from sqlalchemy import func
        
        multiple_active = db.session.query(
            AttendanceRecord.student_id,
            AttendanceRecord.room_id,
            func.count().label('record_count')
        ).filter(
            AttendanceRecord.is_active == True
        ).group_by(
            AttendanceRecord.student_id,
            AttendanceRecord.room_id
        ).having(func.count() > 1).all()
        
        print(f"Found {len(multiple_active)} student-room pairs with multiple active records")
        
        fixed_count = 0
        
        for student_id, room_id, count in multiple_active:
            student = Student.query.get(student_id)
            room = Room.query.get(room_id)
            
            student_name = student.get_full_name() if student else f'Student ID {student_id}'
            room_name = room.get_full_name() if room else f'Room ID {room_id}'
            
            print(f"  - {student_name} in {room_name}: {count} active records")
            
            if not dry_run:
                # Get all active records for this student-room pair
                records = AttendanceRecord.query.filter_by(
                    student_id=student_id,
                    room_id=room_id,
                    is_active=True
                ).order_by(AttendanceRecord.time_in.desc()).all()
                
                # Keep the most recent, close others
                if len(records) > 1:
                    for record in records[1:]:  # Skip the first (most recent)
                        record.time_out = datetime.utcnow()
                        record.is_active = False
                        record.notes = (record.notes or '') + ' [Auto-closed due to duplicate active records]'
                    
                    db.session.commit()
                    fixed_count += 1
        
        if not dry_run:
            print(f"✅ Fixed {fixed_count} duplicate active record issues")
        
        return {'fixed_count': fixed_count, 'success': True}
    
    def detect_negative_durations(self):
        """Detect and report negative durations"""
        print("🕐 Detecting negative durations")
        print("=" * 35)
        
        negative_duration_records = AttendanceRecord.query.filter(
            AttendanceRecord.time_out.isnot(None),
            AttendanceRecord.time_out < AttendanceRecord.time_in
        ).all()
        
        print(f"Found {len(negative_duration_records)} records with negative durations")
        
        for record in negative_duration_records:
            student_name = record.student.get_full_name() if record.student else 'Unknown'
            duration_minutes = (record.time_out - record.time_in).total_seconds() / 60
            
            print(f"  - {student_name}: {duration_minutes:.1f} minutes")
            print(f"    Time In:  {record.time_in}")
            print(f"    Time Out: {record.time_out}")
        
        return negative_duration_records
    
    def generate_system_report(self):
        """Generate comprehensive system health report"""
        print("📊 Generating System Health Report")
        print("=" * 40)
        
        # Get attendance state summary
        state_summary = AttendanceStateService.get_attendance_state_summary()
        
        if not state_summary['success']:
            print("❌ Error getting attendance state summary")
            return
        
        summary = state_summary['summary']
        
        # Basic statistics
        print(f"📈 ATTENDANCE STATISTICS:")
        print(f"  Total Active Records: {summary['total_active_records']}")
        print(f"  Students Currently in System: {summary['total_students_in_system']}")
        print(f"  Students in Multiple Rooms: {summary['students_in_multiple_rooms']}")
        print(f"  Rooms with Multiple Active Records: {summary['rooms_with_multiple_active']}")
        print(f"  Orphaned Records: {summary['orphaned_records']}")
        
        # Health indicators
        print(f"\n🏥 SYSTEM HEALTH INDICATORS:")
        
        health_score = 100
        issues = []
        
        if summary['students_in_multiple_rooms'] > 0:
            health_score -= 10
            issues.append(f"{summary['students_in_multiple_rooms']} students in multiple rooms")
        
        if summary['rooms_with_multiple_active'] > 0:
            health_score -= 15
            issues.append(f"{summary['rooms_with_multiple_active']} rooms with duplicate active records")
        
        if summary['orphaned_records'] > 0:
            health_score -= 20
            issues.append(f"{summary['orphaned_records']} orphaned records")
        
        # Check for negative durations
        negative_durations = self.detect_negative_durations()
        if negative_durations:
            health_score -= 25
            issues.append(f"{len(negative_durations)} records with negative durations")
        
        print(f"  Overall Health Score: {health_score}%")
        
        if health_score >= 90:
            print("  Status: ✅ EXCELLENT")
        elif health_score >= 75:
            print("  Status: ⚠️  GOOD")
        elif health_score >= 50:
            print("  Status: ⚠️  NEEDS ATTENTION")
        else:
            print("  Status: ❌ CRITICAL")
        
        if issues:
            print(f"\n🚨 ISSUES DETECTED:")
            for issue in issues:
                print(f"  - {issue}")
        
        # Current time information
        time_info = TimeManagementService.get_current_time_info()
        print(f"\n🕐 SYSTEM TIME INFORMATION:")
        print(f"  UTC Time: {time_info['utc_time']}")
        print(f"  Local Time: {time_info['local_time']}")
        print(f"  Timezone Offset: {time_info['timezone_offset_hours']:.1f} hours")
        print(f"  DST Active: {time_info.get('is_dst', 'Unknown')}")
        
        # Recent activity
        recent_records = AttendanceRecord.query.order_by(
            AttendanceRecord.time_in.desc()
        ).limit(5).all()
        
        print(f"\n📋 RECENT ACTIVITY (Last 5 records):")
        for record in recent_records:
            student_name = record.student.get_full_name() if record.student else 'Unknown'
            room_name = record.room.room_number if record.room else 'Unknown'
            status = record.get_status()
            
            print(f"  - {student_name} in {room_name}: {status} ({record.time_in.strftime('%Y-%m-%d %H:%M')})")
        
        return {
            'health_score': health_score,
            'issues': issues,
            'summary': summary
        }
    
    def run_maintenance_cycle(self, cleanup=True, fix_duplicates=True, max_age_hours=24):
        """Run a complete maintenance cycle"""
        print("🔄 Running Maintenance Cycle")
        print("=" * 30)
        print(f"Start Time: {datetime.now()}")
        print()
        
        results = {}
        
        if cleanup:
            results['cleanup'] = self.cleanup_orphaned_records(max_age_hours)
            print()
        
        if fix_duplicates:
            results['fix_duplicates'] = self.fix_multiple_active_records()
            print()
        
        results['report'] = self.generate_system_report()
        
        print(f"\n✅ Maintenance cycle completed at {datetime.now()}")
        
        return results

def main():
    """Main function for command line interface"""
    parser = argparse.ArgumentParser(description='Attendance System Maintenance')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Clean up orphaned records')
    parser.add_argument('--fix-duplicates', action='store_true',
                       help='Fix multiple active records')
    parser.add_argument('--report', action='store_true', 
                       help='Generate system health report')
    parser.add_argument('--full', action='store_true',
                       help='Run full maintenance cycle')
    parser.add_argument('--max-age', type=int, default=24,
                       help='Maximum age in hours for orphaned records (default: 24)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    # If no specific action, default to report
    if not any([args.cleanup, args.fix_duplicates, args.report, args.full]):
        args.report = True
    
    print("🚀 Attendance System Maintenance Script")
    print("=" * 45)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    with AttendanceMaintenanceManager() as manager:
        try:
            if args.full:
                results = manager.run_maintenance_cycle(
                    cleanup=True,
                    fix_duplicates=True,
                    max_age_hours=args.max_age
                )
                
                # Save results to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'maintenance_report_{timestamp}.json'
                
                with open(filename, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                print(f"📄 Full maintenance report saved to: {filename}")
            
            else:
                if args.cleanup:
                    manager.cleanup_orphaned_records(args.max_age, args.dry_run)
                    print()
                
                if args.fix_duplicates:
                    manager.fix_multiple_active_records(args.dry_run)
                    print()
                
                if args.report:
                    manager.generate_system_report()
        
        except Exception as e:
            print(f"❌ Error during maintenance: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
    
    print("\n🎉 Maintenance completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())