from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
import os
import logging
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import stripe

from resume_parser import extract_text_from_pdf
from scorer import score_resume, parse_analysis, generate_optimized_resume, enforce_full_score

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'

# configuration for database and authentication
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# stripe configuration (set STRIPE_API_KEY in env)
stripe.api_key = os.environ.get('STRIPE_API_KEY', '')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- user model -----------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_until = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    def is_active(self):
        # override to enforce subscription
        if self.paid_until and datetime.utcnow() > self.paid_until:
            return False
        return True

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# helper to require subscription
from functools import wraps

def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_active():
            flash('Your trial or subscription has expired. Please pay to continue.', 'warning')
            return redirect(url_for('pay'))
        return f(*args, **kwargs)
    return decorated_function



def ensure_skills_in_resume(resume_text, missing_skills):
    """Verify and ensure all missing skills are present in the resume"""
    logger.info(f"Verifying skills presence in resume...")
    
    resume_lower = resume_text.lower()
    
    # Check which skills are missing from the resume
    missing_from_resume = []
    for skill in missing_skills:
        if skill.lower() not in resume_lower:
            missing_from_resume.append(skill)
    
    if not missing_from_resume:
        logger.info("All skills are present in the resume")
        return resume_text
    
    # If some skills are missing, add them to the Skills section
    logger.warning(f"Found {len(missing_from_resume)} skills not in resume: {missing_from_resume}")
    
    # Find the Skills section or create one
    lines = resume_text.split('\n')
    skills_section_index = -1
    
    for i, line in enumerate(lines):
        if 'skills' in line.lower() and ('section' in line.lower() or ':' in line or i < len(lines) - 1):
            skills_section_index = i
            break
    
    # Add missing skills to the resume
    enhanced_resume = resume_text
    
    if skills_section_index != -1:
        # Insert skills after the Skills section header
        skills_to_add = ", ".join(missing_from_resume)
        enhanced_resume = resume_text + f"\n\nAdditional Technical Skills: {skills_to_add}"
    else:
        # If no Skills section found, add it before experience
        enhanced_resume = resume_text + f"\n\nTechnical Skills: {', '.join(missing_from_resume)}"
    
    logger.info(f"Enhanced resume with {len(missing_from_resume)} missing skills")
    return enhanced_resume


def text_to_pdf(text_content):
    """Convert text resume content to a formatted PDF"""
    pdf_buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles for resume
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor='#000000',
        spaceAfter=3,
        alignment=0
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor='#000000',
        spaceAfter=6,
        spaceBefore=6,
        alignment=0,
        borderPadding=0
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#000000',
        spaceAfter=3,
        leading=12,
        alignment=0
    )
    
    # Parse the resume content into sections
    story = []
    lines = text_content.split('\n')
    
    current_section = None
    skill_buffer = ""
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            if skill_buffer:
                story.append(Paragraph(skill_buffer, normal_style))
                skill_buffer = ""
            story.append(Spacer(1, 0.1 * inch))
            continue
        
        # Detect headings (lines in all caps or common section titles)
        is_heading = (
            stripped.isupper() or
            any(title in stripped.lower() for title in [
                'summary', 'skills', 'experience', 'education', 'projects',
                'certifications', 'objectives', 'contact', 'phone', 'email'
            ])
        )
        
        if is_heading and len(stripped) > 3:
            if skill_buffer:
                story.append(Paragraph(skill_buffer, normal_style))
                skill_buffer = ""
            story.append(Paragraph(stripped, heading_style))
            current_section = stripped.lower()
        else:
            # Accumulate lines for better formatting
            if skill_buffer:
                skill_buffer += " " + stripped
            else:
                skill_buffer = stripped
    
    # Add any remaining buffer
    if skill_buffer:
        story.append(Paragraph(skill_buffer, normal_style))
    
    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer

@app.route('/')
def index():
    """Render the main page"""
    # show login/register links if not authenticated
    return render_template('index.html')

# ---------- authentication routes ----------------------------------------
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created. You have one month free.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    """Simple payment page using Stripe Checkout"""
    if request.method == 'POST':
        # create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': 'Resume Screening Subscription',
                    },
                    'unit_amount': 2900,  # ₹29.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', _external=True),
            cancel_url=url_for('pay', _external=True),
            customer_email=current_user.email if current_user.is_authenticated else None,
        )
        return redirect(session.url, code=303)
    return render_template('pay.html')

@app.route('/payment-success')
def payment_success():
    # update user paid_until
    if current_user.is_authenticated:
        current_user.paid_until = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        flash('Payment received! Subscription extended 30 days.', 'success')
    return redirect(url_for('index'))


@app.route('/analyze', methods=['POST'])
@subscription_required
def analyze():
    """Analyze uploaded resumes against job description"""
    try:
        # Get job description
        job_description = request.form.get('job_description', '').strip()
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400

        # Get uploaded files
        if 'resumes' not in request.files:
            return jsonify({'error': 'No resume files provided'}), 400

        files = request.files.getlist('resumes')
        if not files or len(files) == 0:
            return jsonify({'error': 'No resume files provided'}), 400

        logger.info(f"Analyzing {len(files)} resume(s)")

        results = []

        for file in files:
            if file.filename == '':
                continue

            if not file.filename.lower().endswith('.pdf'):
                logger.warning(f"Skipping non-PDF file: {file.filename}")
                continue

            try:
                logger.info(f"Processing: {file.filename}")

                # Extract text from PDF
                resume_text = extract_text_from_pdf(file)

                if not resume_text or len(resume_text.strip()) < 50:
                    logger.warning(f"Insufficient text extracted from {file.filename}")
                    analysis = "Error: Could not extract sufficient text from resume. The PDF may be image-based or corrupted."
                else:
                    # Score the resume
                    analysis = score_resume(resume_text, job_description)

                results.append({
                    'resume_name': file.filename,
                    'analysis': analysis
                })

                logger.info(f"Successfully analyzed: {file.filename}")

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                results.append({
                    'resume_name': file.filename,
                    'analysis': f"Error: Failed to analyze resume - {str(e)}"
                })

        logger.info(f"Analysis complete. Processed {len(results)} resume(s)")

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/extract-resume-text', methods=['POST'])
@subscription_required
def extract_resume_text():
    """Extract text from a resume PDF"""
    try:
        if 'resume_file' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        file = request.files['resume_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        logger.info(f"Extracting text from: {file.filename}")
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(file)
        
        if not resume_text or len(resume_text.strip()) < 50:
            logger.warning(f"Insufficient text extracted from {file.filename}")
            return jsonify({'error': 'Could not extract sufficient text from resume'}), 400
        
        logger.info(f"Successfully extracted {len(resume_text)} characters from resume")
        
        return jsonify({
            'resume_text': resume_text,
            'filename': file.filename
        })
    
    except Exception as e:
        logger.error(f"Error extracting resume text: {str(e)}")
        return jsonify({'error': f'Failed to extract text: {str(e)}'}), 500


@app.route('/generate-resume', methods=['POST'])
@subscription_required
def generate_resume_endpoint():
    """Generate an optimized resume that includes missing skills"""
    try:
        data = request.get_json()
        
        original_resume = data.get('resume_text', '').strip()
        job_description = data.get('job_description', '').strip()
        analysis = data.get('analysis', '').strip()
        resume_filename = data.get('resume_filename', 'resume')
        
        if not original_resume:
            return jsonify({'error': 'Resume text is required'}), 400
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        if not analysis:
            return jsonify({'error': 'Analysis is required'}), 400
        
        # Parse the analysis to get missing skills
        parsed = parse_analysis(analysis)
        missing_skills = parsed.get('missing_skills', [])
        
        logger.info(f"Generating optimized resume with {len(missing_skills)} missing skills")
        
        # Generate the optimized resume
        optimized_resume = generate_optimized_resume(original_resume, job_description, missing_skills)
        
        logger.info(f"Optimized resume generated successfully")
        
        # Ensure all missing skills are present in the resume
        final_resume = ensure_skills_in_resume(optimized_resume, missing_skills)

        # Attempt to get a perfect score by iteratively adding any still-missing keywords
        final_resume = enforce_full_score(final_resume, job_description)
        
        logger.info(f"Resume finalized with all required skills and enforced score")
        
        # Convert resume text to PDF
        pdf_buffer = text_to_pdf(final_resume)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = resume_filename.replace('.pdf', '').replace('.txt', '')
        filename = f"optimized_{base_name}_{timestamp}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        return jsonify({'error': f'Failed to generate resume: {str(e)}'}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    logger.info("Starting Resume Screening AI Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
