import os
import ssl
import logging
from dotenv import load_dotenv

try:
    import truststore
    truststore.inject_into_ssl()
    logging.getLogger(__name__).info("truststore injected — using macOS native SSL certificates")
except ImportError:
    logging.getLogger(__name__).warning("truststore not available, falling back to certifi")

from groq import Groq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def score_resume(resume_text, job_description):
    logger.info("=== score_resume called ===")
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError("GROQ_API_KEY is missing from .env file")

    logger.info("GROQ_API_KEY loaded (starts with: %s...)", api_key[:8])

    client = Groq(api_key=api_key)
    logger.info("Groq client initialized successfully")

    logger.info("Resume text length  : %d characters", len(resume_text))
    logger.info("Job description len : %d characters", len(job_description))

    prompt = f"""
You are an AI Resume Screening Assistant.

Compare the following resume with the job description.

Job Description:
{job_description}

Resume:
{resume_text}

Tasks:
1. Extract relevant skills from resume.
2. Compare with job description.
3. Give a score out of 100.
4. Provide short reasoning.

Return output in this EXACT format:

Score: <number>
Matched Skills: <comma separated list>
Missing Skills: <comma separated list>
Summary: <short explanation>
"""

    logger.info("Sending request to Groq API (model: llama-3.3-70b-versatile)...")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        logger.error("Groq API request failed: %s: %s", type(e).__name__, e)
        raise

    result = response.choices[0].message.content
    logger.info("Response received successfully (%d characters)", len(result))
    logger.info("=== score_resume complete ===")
    return result


def parse_analysis(analysis_text):
    """Parse the analysis text to extract structured data"""
    logger.info("=== parse_analysis called ===")
    
    result = {
        "score": 0,
        "matched_skills": [],
        "missing_skills": [],
        "summary": ""
    }
    
    # Extract score
    score_match = None
    for line in analysis_text.split('\n'):
        if line.lower().startswith('score:'):
            try:
                score_text = line.split(':')[1].strip()
                # Extract just the number
                import re
                score_num = re.search(r'\d+', score_text)
                if score_num:
                    result["score"] = int(score_num.group())
            except:
                pass
    
    # Extract matched skills
    for line in analysis_text.split('\n'):
        if line.lower().startswith('matched skills:'):
            skills_text = line.split(':', 1)[1].strip()
            if skills_text.lower() != 'none' and skills_text:
                result["matched_skills"] = [s.strip() for s in skills_text.split(',') if s.strip()]
    
    # Extract missing skills
    for line in analysis_text.split('\n'):
        if line.lower().startswith('missing skills:'):
            skills_text = line.split(':', 1)[1].strip()
            if skills_text.lower() != 'none' and skills_text:
                result["missing_skills"] = [s.strip() for s in skills_text.split(',') if s.strip()]
    
    # Extract summary
    for i, line in enumerate(analysis_text.split('\n')):
        if line.lower().startswith('summary:'):
            summary_text = line.split(':', 1)[1].strip()
            if summary_text:
                result["summary"] = summary_text
    
    logger.info(f"Parsed analysis - Score: {result['score']}, Missing Skills: {len(result['missing_skills'])}")
    return result


def generate_optimized_resume(original_resume, job_description, missing_skills):
    """Generate an optimized resume that includes missing skills"""
    logger.info("=== generate_optimized_resume called ===")
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError("GROQ_API_KEY is missing from .env file")
    
    client = Groq(api_key=api_key)
    
    missing_skills_text = ", ".join(missing_skills) if missing_skills else "None"
    
    # Create a detailed list of missing skills with emphasis
    skills_list_str = ""
    if missing_skills:
        skills_list_str = "\n".join([f"  {i+1}. {skill}" for i, skill in enumerate(missing_skills)])
    
    prompt = f"""
You are an expert resume writer. Your task is to create a resume that will score 100% match with a job description.

CRITICAL REQUIREMENT: You MUST include ALL of the following missing skills. Every single one must appear in the resume.

Missing Skills (MANDATORY - include ALL of these):
{skills_list_str}

Original Resume Content:
{original_resume}

Job Description to Match:
{job_description}

INSTRUCTIONS:
1. Keep all the legitimate professional information from the original resume
2. MANDATORY: Add ALL missing skills listed above. Do not skip any.
3. Integrate missing skills naturally in experience descriptions, achievements, and projects
4. Add a comprehensive Skills section that includes ALL skills (both existing and missing)
5. Weave missing skills into your professional summary and job descriptions
6. Format professionally with clear sections (Name, Summary, Skills, Experience, Education)
7. Make it realistic and professional - avoid unrealistic claims
8. Ensure the resume will match 100% of required keywords from the job description
9. Do NOT include any headers, markers, or notes about optimization
10. Each missing skill should be mentioned at least once in the resume

VERIFICATION: Before finalizing, ensure these skills appear in the resume:
{missing_skills_text}

Generate a professional resume that incorporates every single missing skill to achieve maximum relevance to the job description.
"""
    
    logger.info("Sending request to Groq API for resume generation...")
    logger.info(f"Missing skills to incorporate: {missing_skills_text}")
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        logger.error("Groq API request failed: %s: %s", type(e).__name__, e)
        raise
    
    result = response.choices[0].message.content
    
    # Verify that all missing skills are in the generated resume
    logger.info(f"Optimized resume generated. Verifying skills inclusion...")
    missing_verification = []
    for skill in missing_skills:
        if skill.lower() not in result.lower():
            missing_verification.append(skill)
            logger.warning(f"Warning: Skill '{skill}' not found in generated resume")
    
    if missing_verification:
        logger.warning(f"Missing {len(missing_verification)} skills in generated resume: {missing_verification}")
    
    logger.info("Optimized resume generated successfully (%d characters)", len(result))
    logger.info("=== generate_optimized_resume complete ===")
    return result


def enforce_full_score(resume_text: str, job_description: str, max_iterations: int = 3):
    """Iteratively score and append missing skills until 100 score or max iterations."""
    logger.info("=== enforce_full_score called ===")
    current_text = resume_text
    best_text = current_text
    best_score = 0
    
    for iteration in range(1, max_iterations + 1):
        logger.info(f"Scoring iteration {iteration}")
        analysis = score_resume(current_text, job_description)
        parsed = parse_analysis(analysis)
        score = parsed.get("score", 0)
        missing = parsed.get("missing_skills", [])
        logger.info(f"Iteration {iteration} analysis - score: {score}, missing: {missing}")
        
        # keep track of best so far
        if score > best_score:
            best_score = score
            best_text = current_text
        
        # stop if perfect or nothing missing
        if score >= 100 or not missing:
            logger.info("Score satisfactory or no missing skills remain")
            break
        
        # Build a neutral addition phrase listing missing skills
        addition = "\n\nAdditional skills to include: " + ", ".join(missing) + "."
        current_text += addition
        logger.info(f"Appended missing skills for next iteration: {missing}")
    
    # if final score dropped below best_score, return best_text
    if best_score > score:
        logger.info(f"Final score ({score}) lower than best score ({best_score}), reverting to best text")
        return best_text
    return current_text
