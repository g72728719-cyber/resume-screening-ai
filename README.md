# Resume Screening AI

A modern, AI-powered resume screening application with a beautiful UI and smooth transitions. Upload multiple resumes and compare them against job descriptions using advanced AI analysis.

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![Flask](https://img.shields.io/badge/flask-3.0-lightgrey)

## Quick Start

```bash
# Navigate to project
cd Hackathon

# Run the startup script
./run.sh              # macOS/Linux
run.bat               # Windows

# Open http://localhost:5000 in your browser
```

The startup script will automatically install dependencies and launch the app!

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed setup instructions.

## Features

- **Modern UI**: Refined tech editorial aesthetic with smooth animations and transitions
- **Drag & Drop**: Easy file upload with drag-and-drop support
- **AI Analysis**: Powered by Groq's LLaMA 3.3 70B model for intelligent resume screening
- **Detailed Insights**: Get scores, matched skills, missing skills, and summaries
- **Multiple Resumes**: Analyze multiple candidates simultaneously
- **Responsive Design**: Works beautifully on desktop, tablet, and mobile devices

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **AI**: Groq API (LLaMA 3.3 70B)
- **PDF Processing**: pypdf

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Hackathon
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install flask python-dotenv groq pypdf truststore
```

### 4. Configure Environment Variables

The `.env` file already contains your Groq API key. If you need to update it:

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

### 5. Run the Application

```bash
python flask_app.py
```

The application will start on `http://localhost:5000`

## Usage

1. **Enter Job Description**: Paste the complete job description in the text area
2. **Upload Resumes**: Drag and drop PDF files or click to browse
3. **Analyze**: Click the "Analyze Candidates" button
4. **Review Results**: View detailed analysis with scores, matched/missing skills, and summaries

## Project Structure

```
Hackathon/
├── flask_app.py           # Flask application
├── scorer.py              # AI scoring logic
├── resume_parser.py       # PDF text extraction
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── style.css          # Stylesheets
│   └── script.js          # Frontend JavaScript
├── temp_uploads/          # Temporary file storage
├── .env                   # Environment variables
├── .env.example           # Example environment file
└── README.md              # This file
```

## API Endpoints

### `GET /`
Renders the main application page

### `POST /analyze`
Analyzes uploaded resumes against job description

**Request:**
- `job_description` (form field): Job description text
- `resumes` (files): Multiple PDF files

**Response:**
```json
[
  {
    "resume_name": "candidate.pdf",
    "analysis": "Score: 85\nMatched Skills: Python, JavaScript\nMissing Skills: AWS\nSummary: Strong candidate..."
  }
]
```

### `GET /health`
Health check endpoint

## Security Notes

- API keys are stored in `.env` and not committed to git
- File uploads are limited to 16MB
- Only PDF files are accepted
- Temporary files are stored in `temp_uploads/` directory

## Troubleshooting

### SSL Certificate Issues (macOS)
If you encounter SSL errors, the app automatically uses `truststore` to leverage macOS native certificates.

### No Results
- Ensure the PDF contains extractable text (not image-based scans)
- Check that the job description is not empty
- Verify the Groq API key is valid

### Performance
- Processing time depends on resume length and number of files
- Each resume typically takes 2-5 seconds to analyze

## Future Enhancements

- [ ] Export results to PDF/CSV
- [ ] Compare candidates side-by-side
- [ ] Save and load job descriptions
- [ ] Batch processing with progress tracking
- [ ] Custom scoring criteria
- [ ] Integration with ATS systems

## License

MIT License

## Credits

Built with Flask, Groq AI, and modern web technologies.
