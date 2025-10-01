#!/usr/bin/env python3
"""
Route Validation Test for Attendance System
Tests all attendance-related routes for proper registration
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app

def test_attendance_routes():
    """Test all attendance routes registration"""
    print("🔍 ATTENDANCE ROUTES VALIDATION")
    print("=" * 50)
    
    app = create_app()
    
    # Get all attendance routes
    attendance_routes = []
    for rule in app.url_map.iter_rules():
        if 'attendance' in rule.endpoint:
            attendance_routes.append({
                'endpoint': rule.endpoint,
                'url': rule.rule,
                'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
            })
    
    print(f"Found {len(attendance_routes)} attendance routes:")
    print()
    
    for route in sorted(attendance_routes, key=lambda x: x['endpoint']):
        print(f"✅ {route['endpoint']}")
        print(f"   URL: {route['url']}")
        print(f"   Methods: {', '.join(route['methods'])}")
        print()
    
    # Check for specific routes we need
    required_routes = [
        'attendance.reports',
        'attendance.manage_sessions',
        'attendance.add_session',
        'attendance.view_session',
        'attendance.edit_session'
    ]
    
    print("🎯 Required Routes Check:")
    print("-" * 30)
    
    existing_endpoints = [route['endpoint'] for route in attendance_routes]
    
    for required in required_routes:
        if required in existing_endpoints:
            print(f"✅ {required}: FOUND")
        else:
            print(f"❌ {required}: MISSING")
    
    print("\n" + "=" * 50)
    
    # Check for the problematic route
    if 'attendance.sessions' in existing_endpoints:
        print("⚠️  WARNING: 'attendance.sessions' endpoint exists")
        print("   This might conflict with template references")
    else:
        print("✅ No conflicting 'attendance.sessions' endpoint found")
    
    if 'attendance.manage_sessions' in existing_endpoints:
        print("✅ 'attendance.manage_sessions' endpoint exists")
        print("   Templates should use this endpoint")
    else:
        print("❌ 'attendance.manage_sessions' endpoint missing")
    
    print("\n🎉 Route validation complete!")

if __name__ == "__main__":
    test_attendance_routes()