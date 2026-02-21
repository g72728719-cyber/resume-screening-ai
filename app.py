import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd

from resume_parser import extract_text_from_pdf
from scorer import score_resume

load_dotenv()

st.set_page_config(page_title="Resume Screening AI")
st.title("📄 First Level Resume Screening AI")

st.markdown("Upload resumes and compare with job description")

job_description = st.text_area("Paste Job Description Here")

uploaded_files = st.file_uploader(
    "Upload Resume PDFs",
    type="pdf",
    accept_multiple_files=True
)

if st.button("Analyze Resumes"):
    if not job_description:
        st.warning("Please enter job description.")
    elif not uploaded_files:
        st.warning("Please upload at least one resume.")
    else:
        results = []

        for file in uploaded_files:
            resume_text = extract_text_from_pdf(file)
            try:
                analysis = score_resume(resume_text, job_description)
            except Exception as e:
                analysis = f"Error analyzing resume: {e}"

            results.append({
                "Resume Name": file.name,
                "Analysis": analysis
            })

        df = pd.DataFrame(results)

        st.subheader("Results")
        st.dataframe(df)

        for result in results:
            st.markdown(f"### {result['Resume Name']}")
            st.write(result["Analysis"])
