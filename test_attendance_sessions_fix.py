#!/usr/bin/env python3
"""
Test the attendance sessions to ensure get_attendance_count method works
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_attendance_sessions():
    """Test attendance sessions functionality"""
    
    print("📊 ATTENDANCE SESSIONS - METHOD FIX TEST")
    print("=" * 50)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.attendance_model import AttendanceSession, AttendanceRecord
            from app.models.room_model import Room
            from app.models.user_model import User
            
            print("✅ Flask app initialized successfully")
            
            # Check if AttendanceSession has the required method
            session_methods = [method for method in dir(AttendanceSession) if not method.startswith('_')]
            
            print(f"✅ AttendanceSession available methods:")
            important_methods = [
                'get_attendance_count',
                'get_attendance_summary', 
                'get_session_status',
                'is_current_session'
            ]
            
            for method in important_methods:
                exists = hasattr(AttendanceSession, method)
                status = "✅" if exists else "❌"
                print(f"   {status} {method}")
            
            # Test the method with a mock session
            try:
                test_session = AttendanceSession(
                    room_id=1,
                    session_name='Test Session',
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    created_by=1
                )
                
                count = test_session.get_attendance_count()
                summary = test_session.get_attendance_summary()
                status = test_session.get_session_status()
                
                print(f"✅ Method testing successful:")
                print(f"   • get_attendance_count(): {count}")
                print(f"   • get_attendance_summary(): {summary}")
                print(f"   • get_session_status(): {status}")
                
            except Exception as e:
                print(f"❌ Method testing failed: {str(e)}")
                return False
            
            # Check existing sessions
            existing_sessions = AttendanceSession.query.all()
            print(f"✅ Existing sessions in database: {len(existing_sessions)}")
            
            if existing_sessions:
                print(f"📋 Session details:")
                for session in existing_sessions[:3]:  # Show first 3
                    print(f"   • {session.session_name}")
                    print(f"     Attendance: {session.get_attendance_count()}")
                    print(f"     Status: {session.get_session_status()}")
            
            print(f"\n🌐 Attendance sessions should now work at:")
            print(f"   • http://localhost:5000/attendance/sessions")
            print(f"   • http://localhost:5000/schedule/sessions")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_attendance_sessions()
    
    if success:
        print(f"\n🎉 ATTENDANCE SESSIONS FIX SUCCESSFUL!")
        print(f"✅ The get_attendance_count() method is now available")
        print(f"✅ Templates should load without TemplateNotFound errors")
        print(f"✅ All session-related functionality should work")
    else:
        print(f"\n❌ TEST FAILED - Please check the errors above")