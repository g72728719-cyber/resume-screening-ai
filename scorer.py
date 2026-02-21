import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def score_resume(resume_text, job_description):
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

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )

    return response.text