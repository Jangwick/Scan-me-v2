# Simple Flask Application Starter
# This is a minimal version that should work

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    import sqlite3
    
    print("✓ Flask imported successfully")
    
    # Create a simple Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/scanme.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db = SQLAlchemy(app)
    
    @app.route('/')
    def index():
        return '''
        <h1>🎯 ScanMe Attendance System</h1>
        <p>Welcome to the ScanMe QR Code Attendance Management System!</p>
        <p><strong>Status:</strong> ✅ System is running successfully</p>
        <div style="margin: 20px 0;">
            <h3>Next Steps:</h3>
            <ul>
                <li>Set up student database</li>
                <li>Configure rooms and sessions</li>
                <li>Start scanning QR codes for attendance</li>
            </ul>
        </div>
        <p><em>Note: This is a simplified version. The full system with all features will be available once the environment is fully configured.</em></p>
        '''
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'message': 'ScanMe system is running'}
    
    # Create instance directory
    os.makedirs('instance', exist_ok=True)
    
    if __name__ == '__main__':
        print("🚀 Starting ScanMe Attendance System...")
        print("📱 Open your browser to: http://localhost:5000")
        print("🛑 Press Ctrl+C to stop the server")
        app.run(debug=True, host='0.0.0.0', port=5000)
        
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure all required packages are installed:")
    print("pip install Flask Flask-SQLAlchemy")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)