#!/usr/bin/env python3
"""
Test the recent-scans API endpoint directly to see what data it returns
"""

from app import create_app
import json

def test_recent_scans_api_direct():
    """Test the recent-scans API directly"""
    print("🔍 TESTING RECENT-SCANS API")
    print("=" * 50)
    
    app = create_app()
    
    with app.test_client() as client:
        try:
            # First, let's log in as admin to test the protected endpoint
            with app.app_context():
                from flask_login import login_user
                from app.models import User
                
                # Create a test request context
                with client.session_transaction() as sess:
                    # Get admin user
                    admin_user = User.query.filter_by(username='admin').first()
                    if not admin_user:
                        print("❌ No admin user found for testing")
                        return False
                
                # Login the admin user for testing
                response = client.post('/login', data={
                    'username': 'admin',
                    'password': 'admin123'
                })
                
                print(f"Login response status: {response.status_code}")
                
                # Now test the recent-scans endpoint
                response = client.get('/scanner/api/recent-scans')
                
                print(f"Recent-scans response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        
                        if isinstance(data, list):
                            print(f"✅ API returned {len(data)} events")
                            
                            print("\nRecent Scans Data:")
                            print("-" * 50)
                            
                            for i, event in enumerate(data[:5], 1):  # Show first 5
                                student_name = event.get('student_name', 'Unknown')
                                room_name = event.get('room_name', 'Unknown')
                                action_type = event.get('action_type', 'Unknown')
                                scan_time = event.get('scan_time', 'Unknown')
                                time_ago = event.get('time_ago', 'Unknown')
                                
                                print(f"{i:2d}. {action_type.upper()}: {student_name} in {room_name}")
                                print(f"    Time: {scan_time}")
                                print(f"    Time ago: {time_ago}")
                                print()
                            
                            # Check if we have both time_in and time_out
                            time_in_count = len([e for e in data if e.get('action_type') == 'time_in'])
                            time_out_count = len([e for e in data if e.get('action_type') == 'time_out'])
                            
                            print(f"📊 Summary:")
                            print(f"   Time-in events: {time_in_count}")
                            print(f"   Time-out events: {time_out_count}")
                            print(f"   Total events: {len(data)}")
                            
                            if time_in_count > 0 and time_out_count > 0:
                                print("✅ SUCCESS: API returns both time-in and time-out events separately!")
                                return True
                            else:
                                print("⚠️  Limited event types in current data")
                                return True
                        else:
                            print(f"❌ Unexpected response format: {data}")
                            return False
                            
                    except Exception as e:
                        print(f"❌ Error parsing JSON response: {str(e)}")
                        print(f"Raw response: {response.get_data(as_text=True)}")
                        return False
                else:
                    print(f"❌ API request failed with status {response.status_code}")
                    print(f"Response: {response.get_data(as_text=True)}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing API: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_recent_scans_api_direct()
    if success:
        print("\n🎉 Recent-scans API test completed!")
    else:
        print("\n❌ Recent-scans API test failed!")