#!/usr/bin/env python3
"""
Test script to simulate the professor dashboard access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User
import requests
import traceback

def test_professor_dashboard_access():
    """Test accessing the professor dashboard directly"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting Flask app for testing...")
            
            # Start the app in a separate thread for testing
            from threading import Thread
            import time
            
            def run_app():
                app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
            
            # Start Flask app in background
            server_thread = Thread(target=run_app, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            
            print("Testing professor login and dashboard access...")
            
            # Create a session to maintain cookies
            session = requests.Session()
            
            # First, try to access the login page
            login_url = 'http://127.0.0.1:5001/auth/login'
            response = session.get(login_url)
            print(f"Login page status: {response.status_code}")
            
            if response.status_code == 200:
                # Try to login as professor
                login_data = {
                    'username': 'professor',
                    'password': 'professor123'
                }
                
                login_response = session.post(login_url, data=login_data)
                print(f"Login response status: {login_response.status_code}")
                
                if login_response.status_code == 200 or login_response.status_code == 302:
                    # Try to access professor dashboard
                    dashboard_url = 'http://127.0.0.1:5001/professor'
                    dashboard_response = session.get(dashboard_url)
                    print(f"Dashboard response status: {dashboard_response.status_code}")
                    
                    if dashboard_response.status_code == 500:
                        print("Got 500 error! This is likely our modulo error.")
                        print(f"Response text: {dashboard_response.text[:500]}...")
                    elif dashboard_response.status_code == 200:
                        print("Dashboard loaded successfully!")
                    else:
                        print(f"Unexpected status code: {dashboard_response.status_code}")
                else:
                    print("Login failed")
            else:
                print("Could not access login page")
                
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_professor_dashboard_access()