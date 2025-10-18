import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="LLM Academic Grading System",
    layout="wide",
    page_icon="🎓"
)

# --- HEADER (NO LOGIN/SIGNUP BUTTONS) ---
st.markdown("""
    <style>
    .header-container {
        display: flex; justify-content: center; align-items: center;
        margin-top: 20px; margin-bottom: 10px; padding: 0 40px;
    }
    .big-title {
        font-size: 48px; font-weight: 800; color: #2b6777;
        font-family: 'Segoe UI', sans-serif; margin: 0;
    }
    .subtitle {
        font-size: 20px; color: #555555; font-family: 'Segoe UI', sans-serif;
        text-align: center; margin-bottom: 30px;
    }
    .stApp { background-color: #f7f9fc !important; color: #000000 !important; font-family: 'Segoe UI', sans-serif;}
    html, body, [class*="css"] { font-size: 17px; }
    .feature-card {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 20px;
        border-radius: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        text-align: center; transition: all 0.3s ease-in-out;
    }
    .feature-card:hover { transform: scale(1.03); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);}
    .tech-stack-title { text-align: center; font-size: 28px; color: #2b6777; margin-bottom: 15px;}
    .tech-logos { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 10px;}
    .tech-logos img { height: 40px; }
    .highlight-section {
        background: linear-gradient(135deg, #e3f2fd, #f0f8ff); border-radius: 12px;
        padding: 30px; margin-top: 30px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
    }
    .highlight-section .grid { display: flex; flex-wrap: wrap; justify-content: space-around; gap: 20px; text-align: center;}
    .highlight-section .grid-item {
        width: 30%; background-color: #fff; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06); transition: transform 0.3s;
    }
    .highlight-section .grid-item:hover { transform: translateY(-5px);}
    .highlight-section img { height: 64px; margin-bottom: 10px; }
    </style>
    <br>
    <div class="header-container">
        <h1 class="big-title">LLM AutoGrader 🚀</h1>
    </div>
    <div class="subtitle">AI-powered multilingual grading platform with explainability, multi-agent support, and rich analytics.</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- Platform Capabilities ---
st.subheader("📌 Platform Capabilities")
row1 = st.columns(3)
with row1[0]:
    st.markdown("""
    <div class="feature-card">
        <h3>📤 Smart PDF Upload</h3>
        <p>Extract structured Q&A from professor and student PDFs. Supports multi-subject assignments.</p>
    </div>
    """, unsafe_allow_html=True)
with row1[1]:
    st.markdown("""
    <div class="feature-card">
        <h3>🤖 Multilingual LLM Grading</h3>
        <p>Grades in English, German, and Spanish using rubric-based evaluation with Ollama models.</p>
    </div>
    """, unsafe_allow_html=True)
with row1[2]:
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Insightful Analytics</h3>
        <p>Interactive dashboard with filters for year, semester, course, and student analytics.</p>
    </div>
    """, unsafe_allow_html=True)

# --- What Sets Us Apart ---
st.markdown("---")
st.subheader("🚀 What Sets Us Apart")
st.markdown("""
<div class='highlight-section'>
    <h3>Built for the Future of Grading</h3>
    <div class='grid'>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/3039/3039436.png'>
            <h4>Explainable AI</h4>
            <p>Rubric-aligned, interpretable score justifications for every student answer.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/476/476863.png'>
            <h4>Multi-Agent Collaboration</h4>
            <p>Simulated peer review from diverse AI agents for fairer, more accurate grading.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/619/619153.png'>
            <h4>RAG-Enhanced Evaluation</h4>
            <p>Grading with support from similar historical answers via FAISS or ChromaDB.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/1828/1828919.png'>
            <h4>Human-in-the-Loop</h4>
            <p>Teachers can edit feedback, revise scores, and approve LLM output in real time.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/4149/4149678.png'>
            <h4>MLOps + LMS Integration</h4>
            <p>Versioned feedback, tracked via MLflow and GitHub CI/CD. ILIAS & campus LMS ready.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/1503/1503336.png'>
            <h4>Multimodal Support</h4>
            <p>Accept and evaluate image answers, handwritten notes, and scientific sketches with OCR.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/3159/3159066.png'>
            <h4>Multi-Agent LLM Simulation</h4>
            <p>Run multiple LLM agents simultaneously for peer-review style consensus grading.</p>
        </div>
        <div class='grid-item'>
            <img src='https://cdn-icons-png.flaticon.com/512/1250/1250685.png'>
            <h4>Scalable MLOps</h4>
            <p>Robust tracking of grading events, model versions, and feedback with MLflow and CI/CD pipelines.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Tech Stack ---
st.markdown("---")
st.markdown("<div class='tech-stack-title'>🧰 Technologies We Use</div>", unsafe_allow_html=True)
st.markdown("""
<div class='tech-logos'>
    <img src='https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg'>
    <img src='https://cdn.jsdelivr.net/gh/devicons/devicon/icons/streamlit/streamlit-original.svg'>
    <img src='https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg'>
    <img src='https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg'>
    <img src='https://upload.wikimedia.org/wikipedia/commons/3/38/MLflow_logo_2.svg'>
    <img src='https://huggingface.co/front/assets/huggingface_logo-noborder.svg'>
    <img src='https://raw.githubusercontent.com/faiss/faiss/master/resources/faiss-logo.png' style='height:40px;'>
    <img src='https://seeklogo.com/images/C/chroma-logo-BD628A7C20-seeklogo.com.png' style='height:40px;'>
    <img src='https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png' style='height:40px;'>
</div>
""", unsafe_allow_html=True)

# --- CTA ---
st.markdown("---")
st.markdown("""
<h2 style='text-align: center; color: #2b6777;'>🎯 Ready to Transform Your Grading Workflow?</h2>
<div style='text-align: center;'>
    <a href="pages/1_upload_data.py" target="_self" style='text-decoration: none;'>
        <button style='padding: 12px 24px; margin: 10px; font-size: 18px; background-color: #2b6777; color: white; border: none; border-radius: 8px;'>📥 Upload Assignment PDFs</button>
    </a>
    <a href="pages/4_dashboard.py" target="_self" style='text-decoration: none;'>
        <button style='padding: 12px 24px; margin: 10px; font-size: 18px; background-color: #406882; color: white; border: none; border-radius: 8px;'>📊 View Analytics Dashboard</button>
    </a>
</div>
""", unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
---
<p style='text-align: center; font-size: 14px;'>© 2025 LLM AutoGrader | Built with ❤️ using open-source technologies.</p>
""", unsafe_allow_html=True)
