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
import razorpay

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

# razorpay configuration (set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in env)
razorpay_client = razorpay.Client(auth=(os.environ.get('RAZORPAY_KEY_ID',''),
                                         os.environ.get('RAZORPAY_KEY_SECRET','')))

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def send_otp_email(recipient, code):
    """Send OTP to the user's email address.

    If SMTP_* environment variables are set the function will attempt to
    deliver the message via an SMTP server. Otherwise it simply logs the
    code for development purposes.
    """
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')

    message = f"Subject: [Resume AI] Your verification code\n\nYour code is {code}."

    if smtp_host and smtp_user and smtp_pass:
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, recipient, message)
            logger.info(f"OTP {code} sent to {recipient} via SMTP")
            return
        except Exception as exc:
            logger.warning(f"SMTP send failed: {exc}")
    # fallback log/flash for development
    logger.info(f"[DEV] OTP {code} for {recipient}: {code}")

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- user model -----------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_until = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    # verification
    is_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6), nullable=True)
    otp_sent_at = db.Column(db.DateTime, nullable=True)

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
import random, smtplib
from flask import session

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        # create user with one-month trial automatically via default
        user = User(email=email, password_hash=generate_password_hash(password))
        # generate OTP for verification
        import random
        code = f"{random.randint(0,999999):06d}"
        user.otp_code = code
        user.otp_sent_at = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        send_otp_email(email, code)
        session['pending_user_id'] = user.id
        # for development show the code in the flash as well
        flash(f'Account created. Your verification code is {code}. Check your email.', 'info')
        return redirect(url_for('verify'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                flash('Please verify your email before logging in.', 'warning')
                session['pending_user_id'] = user.id
                return redirect(url_for('verify'))
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    session.pop('pending_user_id', None)
    return redirect(url_for('index'))

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    """Payment page using Razorpay order+checkout"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # create razorpay order
        amount_paise = 2900  # ₹29
        order = razorpay_client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': '1'
        })
        # pass order to template for checkout
        return render_template('pay.html', order=order, key_id=os.environ.get('RAZORPAY_KEY_ID',''))
    return render_template('pay.html')

@app.route('/payment-success', methods=['POST'])
def payment_success():
    # webhook/callback from Razorpay
    # expected form: razorpay_payment_id, razorpay_order_id, razorpay_signature
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


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    """Email verification endpoint (enter OTP code)"""
    if request.method == 'POST':
        code = request.form.get('code')
        email = request.form.get('email')
        user = None
        if 'pending_user_id' in session:
            user = User.query.get(session['pending_user_id'])
        if not user and email:
            user = User.query.filter_by(email=email).first()
        if not user:
            flash('No pending verification found.', 'danger')
            return redirect(url_for('register'))
        # check code and expiration (10 minutes)
        if user.otp_code == code and user.otp_sent_at and datetime.utcnow() - user.otp_sent_at < timedelta(minutes=10):
            user.is_verified = True
            user.otp_code = None
            user.otp_sent_at = None
            db.session.commit()
            login_user(user)
            flash('Email verified! Welcome and enjoy your trial.', 'success')
            session.pop('pending_user_id', None)
            return redirect(url_for('index'))
        else:
            flash('Invalid or expired code.', 'danger')
    return render_template('verify.html')


@app.route('/resend-otp')
def resend_otp():
    # resend code to pending or logged-in unverified user
    user = None
    if 'pending_user_id' in session:
        user = User.query.get(session['pending_user_id'])
    elif current_user.is_authenticated and not current_user.is_verified:
        user = current_user
    if not user:
        return redirect(url_for('login'))
    code = f"{random.randint(0,999999):06d}"
    user.otp_code = code
    user.otp_sent_at = datetime.utcnow()
    db.session.commit()
    send_otp_email(user.email, code)
    flash(f'Verification code resent. Code: {code}', 'info')
    return redirect(url_for('verify'))

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

# create database tables if they don't exist
# Flask 3 removed before_first_request; ensure tables are created at import time
with app.app_context():
    db.create_all()
    # if we've added new columns for verification, alter table accordingly
    inspector = db.inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('user')]
    if 'is_verified' not in cols:
        db.engine.execute('ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0')
    if 'otp_code' not in cols:
        db.engine.execute('ALTER TABLE user ADD COLUMN otp_code VARCHAR(6)')
    if 'otp_sent_at' not in cols:
        db.engine.execute('ALTER TABLE user ADD COLUMN otp_sent_at DATETIME')

if __name__ == '__main__':
    logger.info("Starting Resume Screening AI Flask application...")
    db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
