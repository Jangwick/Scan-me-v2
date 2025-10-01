#!/usr/bin/env python3
"""
Test script to directly call professor routes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.routes.professor_routes import dashboard
from app.models import User
import traceback

def test_professor_dashboard_route():
    """Test calling the professor dashboard route directly"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing professor dashboard route directly...")
            
            # Create a test request context
            with app.test_request_context('/professor'):
                # Mock the current_user
                professor = User.query.filter_by(username='professor').first()
                if not professor:
                    print("No professor user found!")
                    return
                
                # Set up flask-login current_user
                from flask_login import login_user
                login_user(professor)
                
                try:
                    # Call the dashboard function directly
                    response = dashboard()
                    print("Dashboard function executed successfully!")
                    print(f"Response type: {type(response)}")
                    
                except Exception as e:
                    print(f"ERROR in dashboard function: {e}")
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_professor_dashboard_route()