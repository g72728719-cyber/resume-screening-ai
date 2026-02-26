# Quick Setup Guide

## Fastest Way to Get Started

### Option 1: Using the Startup Script (Recommended)

**macOS/Linux:**
```bash
./run.sh
```

**Windows:**
```bash
run.bat
```

### Option 2: Manual Setup

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python flask_app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:5000`

## What You'll See

The application features a modern, professional interface with:

- **Left Panel**:
  - Job description text area
  - Drag-and-drop file upload zone
  - List of uploaded files
  - Analyze button

- **Right Panel**:
  - Empty state with instructions
  - Loading animation during analysis
  - Beautiful result cards with:
    - Candidate score (color-coded)
    - Matched skills (green tags)
    - Missing skills (red tags)
    - AI-generated summary

## Design Highlights

### Visual Features
- **Refined Tech Editorial** aesthetic
- Dark theme with electric teal accents
- Grain texture overlay for depth
- Smooth animations and transitions
- Responsive design (mobile, tablet, desktop)

### Typography
- Display font: **Outfit** (bold, geometric)
- Body font: **DM Sans** (clean, readable)

### Color Palette
- Background: Deep charcoal (#0f0f0f)
- Surface: Dark gray (#1a1a1a)
- Accent: Electric teal (#06b6d4)
- Success: Green (#10b981)
- Warning: Amber (#f59e0b)
- Danger: Red (#ef4444)

### Animations
- Fade-in effects on page load
- Staggered card reveals
- Hover state transformations
- Smooth color transitions
- Floating empty state icon
- Multi-ring loading spinner

## Key Improvements Over Original Streamlit App

1. **Modern UI**: Professional, polished design vs basic Streamlit interface
2. **Better UX**: Drag-and-drop, real-time feedback, loading states
3. **Smooth Animations**: Delightful micro-interactions throughout
4. **Responsive**: Works on all devices
5. **Performance**: Faster load times, optimized assets
6. **Customizable**: Easy to modify colors, fonts, layouts
7. **Production-Ready**: Clean code, proper error handling

## Troubleshooting

### Port Already in Use
If port 5000 is occupied, edit [flask_app.py](flask_app.py) line 76:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
```

### Dependencies Not Installing
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### API Key Issues
Verify your `.env` file contains:
```
GROQ_API_KEY=your_actual_api_key_here
```

## Next Steps

1. **Test the Application**: Upload sample resumes
2. **Customize Design**: Modify colors in [style.css](static/style.css)
3. **Add Features**: Extend functionality as needed
4. **Deploy**: Consider deploying to production (Heroku, Railway, etc.)

## File Structure Reference

```
Hackathon/
├── flask_app.py          # Main Flask application
├── scorer.py             # AI scoring logic (Groq API)
├── resume_parser.py      # PDF text extraction
├── templates/
│   └── index.html        # HTML template
├── static/
│   ├── style.css         # All styles and animations
│   └── script.js         # Frontend interactivity
├── requirements.txt      # Python dependencies
├── .env                  # API keys (not in git)
├── .env.example          # Example environment file
├── run.sh               # macOS/Linux startup script
├── run.bat              # Windows startup script
├── README.md            # Main documentation
└── SETUP_GUIDE.md       # This file
```

## Support

For issues or questions:
1. Check the [README.md](README.md)
2. Review the troubleshooting section above
3. Check Flask/Python logs in terminal
4. Verify API key is valid

---

**Enjoy your beautiful Resume Screening AI!** 🚀
