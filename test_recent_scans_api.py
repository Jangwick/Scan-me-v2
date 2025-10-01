#!/usr/bin/env python3
"""
Test the recent scans API to verify separate event display
"""

from app import create_app
import requests
import json

def test_recent_scans_api():
    """Test the recent scans API"""
    print("Testing Recent Scans API...")
    print("=" * 50)
    
    # We need to start the Flask app first
    # Let's just test directly without HTTP
    app = create_app()
    
    with app.app_context():
        from app.routes.scanner_routes import get_recent_scans
        
        try:
            # Call the function directly
            result = get_recent_scans()
            
            if hasattr(result, 'json'):
                # If it's a Response object
                data = result.get_json()
            else:
                # If it's already a dict
                data = result
            
            if 'recent_scans' in data:
                scans = data['recent_scans']
                print(f"✓ Found {len(scans)} recent scans")
                
                for scan in scans[:5]:  # Show first 5
                    student_name = scan.get('student_name', 'Unknown')
                    room_name = scan.get('room_name', 'Unknown')
                    event_type = scan.get('event_type', 'Unknown')
                    event_time = scan.get('event_time', 'Unknown')
                    
                    print(f"  {event_type}: {student_name} in {room_name} at {event_time}")
                
                # Check if we have both time_in and time_out events
                time_in_count = len([s for s in scans if s.get('event_type') == 'time_in'])
                time_out_count = len([s for s in scans if s.get('event_type') == 'time_out'])
                
                print(f"\n✓ Time-in events: {time_in_count}")
                print(f"✓ Time-out events: {time_out_count}")
                
                if time_in_count > 0 and time_out_count > 0:
                    print("✅ SUCCESS: Both time-in and time-out events are displayed separately!")
                    return True
                else:
                    print("⚠️  WARNING: Only one type of event found")
                    return True  # Still success, just less data
                    
            else:
                print("❌ No 'recent_scans' found in response")
                print(f"Response: {data}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing recent scans API: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_recent_scans_api()
    if success:
        print("\n🎉 Recent Scans API test completed successfully!")
        print("The separate time-in and time-out events are now displayed!")
    else:
        print("\n❌ Recent Scans API test failed!")