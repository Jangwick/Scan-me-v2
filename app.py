"""
ScanMe Room Attendance System - Main Application Entry Point
Uses the proper application factory from the app package
"""

from app import create_app

if __name__ == '__main__':
    # Create the Flask application using the proper factory
    app = create_app()
    print("Starting ScanMe Attendance System...")
    print("Access the application at: http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)