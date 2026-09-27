# AI Resume Screener & Job Matcher

An AI-powered Resume Screening and Job Matching system developed for the
**Cognizant NPN AIA Hackathon**. The application analyzes a candidate's
resume against a Job Description (JD), calculates an explainable match
score, identifies matched and missing skills, measures semantic
similarity, and provides actionable recommendations.

## 🚀 Live Demo

### Deployed on Amazon Web Services (AWS) EC2

🌐 **Live Application:** <http://43.204.237.177:8501/> The application
is deployed on an **Amazon EC2 instance** and is accessible through the
live URL above.

## 🚀 Project Overview

The system combines resume parsing, Job Description skill extraction,
explicit skill matching, evidence-based validation, semantic similarity,
explainable scoring, recommendations, authentication, analysis history,
and PDF reporting. The current MVP focuses on **one-to-one Resume ↔ Job
Description** **matching**.

``` text
Resume + Job Description
          ↓
     AI Analysis
          ↓
    JD Match Score
          ↓
 ┌────────┴────────┐
 ↓                 ↓
Matched Skills   Missing Skills
          ↓
    Recommendations
          ↓
      PDF Report
```

## Setup Instructions

### Backend

``` bash
python -m uvicorn backend.main:app --reload
```

Backend: `http://127.0.0.1:8000`

API Docs: `http://127.0.0.1:8000/docs`

### Frontend

Open a second terminal:

``` bash
python -m streamlit run frontend/streamlit_app.py
```

Frontend: `http://localhost:8501`

## Tech Stack

**Frontend:** Streamlit, HTML/CSS

**Backend:** Python, FastAPI, Uvicorn

**AI / NLP:** spaCy, Sentence Transformers, all-MiniLM-L6-v2, Groq

**Machine Learning:** Scikit-learn, NumPy, Pandas

**Database & Authentication:** Supabase, PostgreSQL

**PDF:** WeasyPrint
