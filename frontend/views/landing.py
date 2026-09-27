import streamlit as st


def render():
    
    # Landing page CSS
    st.markdown("""
    <style>
        .main-header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #9333EA 100%);
            color: white;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(79, 70, 229, 0.3);
        }
        .main-header h1 {
            font-size: 2.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Resume Screener & Job Matcher</h1>
        <h3>AI-powered resume analysis, job matching & explainable insights</h3>
        <p>Upload a resume and job description to understand your match score, skill gaps, and improvement opportunities</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Call-to-Action Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Analyzing Your Resume", use_container_width=True, type="primary"):
            st.session_state.current_view = 'scorer'
            st.rerun()
    
    st.markdown("---")
    
    # Features Overview
    st.markdown("## ✨ Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📊 Resume–Job Scoring
        Get detailed scores across 5 key dimensions:
        - Formatting (20%)
        - Keywords & Skills (25%)
        - Content Quality (25%)
        - Skill Validation (15%)
        - ATS Compatibility (15%)
        """)
    
    with col2:
        st.markdown("""
        ### 🔍 Skill Evidence Analysis
        Verify that your claimed skills are demonstrated in your projects and experience using AI-powered semantic analysis.
        
        **No more empty claims!**
        """)
    
    with col3:
        st.markdown("""
        ### 🤖 Explainable AI
        Understand why the resume received its score, which requirements are matched, and where the gaps are.
        
        **Transparent, actionable feedback**
        """)
    
    st.markdown("---")
    
    # How It Works
    st.markdown("## 🚀 How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 1️⃣ Upload Resume + JD
        Upload your resume and provide the target job description
        """)
    
    with col2:
        st.markdown("""
        #### 2️⃣ AI Matching
        Parse the resume and compare its skills and content with the job description
        """)
    
    with col3:
        st.markdown("""
        #### 3️⃣ Get Explainable Insights
        See your score, matched/missing skills, score explanation, and recommendations
        """)
