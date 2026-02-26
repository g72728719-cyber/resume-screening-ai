@echo off
REM Resume Screening AI - Startup Script for Windows

echo Starting Resume Screening AI...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    echo Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Warning: .env file not found
    echo Please copy .env.example to .env and add your Groq API key
    pause
    exit /b 1
)

REM Create temp_uploads directory
if not exist "temp_uploads" mkdir temp_uploads

REM Start the Flask app
echo.
echo Starting Flask application...
echo Open http://localhost:5000 in your browser
echo.
python flask_app.py
