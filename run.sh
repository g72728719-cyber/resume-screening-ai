#!/bin/bash

# Resume Screening AI - Startup Script

echo "🚀 Starting Resume Screening AI..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please copy .env.example to .env and add your Groq API key"
    exit 1
fi

# Create temp_uploads directory
mkdir -p temp_uploads

# Start the Flask app
echo ""
echo "✨ Starting Flask application..."
echo "🌐 Open http://localhost:5000 in your browser"
echo ""
python flask_app.py
