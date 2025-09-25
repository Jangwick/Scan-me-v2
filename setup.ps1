# Virtual Environment Setup Script for ScanMe Attendance System
# Run this script to set up the complete development environment

Write-Host "ScanMe Attendance System - Environment Setup" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Yellow
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv venv

if (-not (Test-Path "venv")) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment created successfully!" -ForegroundColor Green

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing required packages..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "All packages installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Error: Some packages failed to install" -ForegroundColor Red
    Write-Host "Please check the error messages above" -ForegroundColor Red
    exit 1
}

# Create instance directory
Write-Host "Creating instance directory..." -ForegroundColor Cyan
if (-not (Test-Path "instance")) {
    New-Item -ItemType Directory -Path "instance"
    Write-Host "Instance directory created" -ForegroundColor Green
}

# Create .env file if it doesn't exist
Write-Host "Setting up environment variables..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    $envContent = @"
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True

# Secret Key (Change this in production!)
SECRET_KEY=your-secret-key-change-in-production-$(Get-Random)

# Database Configuration
DATABASE_URL=sqlite:///instance/scanme.db

# Upload Configuration
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=app/static/uploads

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security Settings
WTF_CSRF_ENABLED=True
WTF_CSRF_TIME_LIMIT=3600

# QR Code Settings
QR_CODE_SIZE=10
QR_CODE_BORDER=4
QR_CODE_ERROR_CORRECTION=M

# Attendance Settings
LATE_THRESHOLD_MINUTES=15
ATTENDANCE_GRACE_PERIOD=5
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host ".env file created with default settings" -ForegroundColor Green
    Write-Host "Please update the SECRET_KEY and other settings as needed" -ForegroundColor Yellow
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Cyan
python -c "from app import create_app; app = create_app(); app.app_context().push(); from app import db; db.create_all(); print('Database initialized successfully!')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database initialized successfully!" -ForegroundColor Green
} else {
    Write-Host "Warning: Database initialization failed" -ForegroundColor Yellow
    Write-Host "You can run 'python init_db.py' manually later" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the development server:" -ForegroundColor Cyan
Write-Host "1. Activate virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "2. Run the application: python app.py" -ForegroundColor Yellow
Write-Host "3. Open browser to: http://localhost:5000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Default admin account will be created:" -ForegroundColor Cyan
Write-Host "Username: admin" -ForegroundColor Yellow
Write-Host "Password: admin123" -ForegroundColor Yellow
Write-Host "Please change the password after first login!" -ForegroundColor Red
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Green