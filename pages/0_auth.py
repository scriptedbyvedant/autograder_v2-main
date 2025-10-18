import streamlit as st
import bcrypt
import psycopg2

# ---- SUBJECT AND SESSION OPTIONS ----
SUBJECT_OPTIONS = [
    "AI Fundamentals","Einführung in KI" ,"Data Structures", "Algorithms",
    "Machine Learning", "Deep Learning", "Computer Networks",
    "Database Systems", "Software Engineering", "Operating Systems",
    "Discrete Mathematics", "Statistics", "Natural Language Processing",
    "Cybersecurity", "Cloud Computing", "Image Processing"
]
SESSION_OPTIONS = ["Summer", "Winter"]

# --- DATABASE CONNECTION ---
def get_conn():
    return psycopg2.connect(
        host="localhost", database="autograder_db",
        user="vedant", password="vedant"
    )

# --- REGISTRATION FUNCTION ---
def register_user(university_email, username, password, subjects, sessions):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM professors WHERE university_email=%s OR username=%s", (university_email, username))
    if cur.fetchone():
        conn.close()
        return False, "Username or University Email already registered."
    hash_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    subject_str = ', '.join(subjects)
    session_str = ', '.join(sessions)
    cur.execute(
        "INSERT INTO professors (university_email, username, password_hash, subjects, sessions) VALUES (%s,%s,%s,%s,%s)",
        (university_email, username, hash_pw.decode(), subject_str, session_str)
    )
    conn.commit()
    conn.close()
    return True, "🎉 Registration successful! Please login."

# --- LOGIN FUNCTION ---
def check_login(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, university_email, subjects, sessions, password_hash FROM professors WHERE username=%s", (username,))
    row = cur.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[4].encode()):
        return {
            "id": row[0], "university_email": row[1],
            "subjects": row[2], "sessions": row[3], "username": username
        }
    return None

# --- STREAMLIT PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Professor Login", page_icon="🎓", layout="centered")

st.markdown("""
    <style>
    .auth-card {background: #f8fafc; border-radius: 11px; box-shadow: 0 3px 14px #2d355311;
        padding: 32px 32px 24px 32px; margin-top: 20px;}
    .auth-title {color: #154180; font-size: 1.6em; font-weight: 700; margin-bottom: 18px;}
    .auth-help {color: #58708f; font-size: 1em; margin-bottom: 22px;}
    .stTabs [role="tab"] {font-size: 1.1em;}
    .profile-badge {background:#edf1fa;border-radius:18px;padding:14px 24px;margin:12px 0;
        box-shadow:0 1.5px 7px #22355a0b;font-size:1.1em;}
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">Professor Authentication</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-help">Log in to access grading & analytics. Register below if you are a new professor.</div>', unsafe_allow_html=True)

    tab = st.tabs(["🔑 Login", "📝 Register"])

    # --- LOGIN TAB ---
    with tab[0]:
        st.subheader("Login")
        login_user = st.text_input("Username", key="loginuser")
        login_pw = st.text_input("Password", type="password", key="loginpw")
        login_btn = st.button("Login", key="login_btn")
        if login_btn:
            prof = check_login(login_user, login_pw)
            if prof:
                st.session_state["logged_in_prof"] = prof
                st.success(
                    f"Welcome, {prof['username']}",
                    icon="✅"
                )
            else:
                st.error("❌ Invalid credentials. Please try again.")

    # --- REGISTER TAB ---
    with tab[1]:
        st.subheader("Register")
        with st.form("register_form", clear_on_submit=True):
            university_email = st.text_input("University Email (must end with @stud.hs-heilbronn.de)")
            username = st.text_input("Create a Username")
            password = st.text_input("Create a Password", type="password")
            subjects = st.multiselect("Subjects You Teach (Select all that apply)", SUBJECT_OPTIONS)
            sessions = st.multiselect("Teaching Sessions (Summer/Winter)", SESSION_OPTIONS)
            reg_btn = st.form_submit_button("Register")
            if reg_btn:
                if not university_email.lower().endswith("@stud.hs-heilbronn.de"):
                    st.error("Please use your university email address (must end with @stud.hs-heilbronn.de).")
                elif not subjects:
                    st.error("Please select at least one subject.")
                elif not sessions:
                    st.error("Please select at least one session (Summer/Winter).")
                elif len(username.strip()) < 3 or len(password.strip()) < 4:
                    st.error("Please enter a valid username (min 3 chars) and password (min 4 chars).")
                else:
                    ok, msg = register_user(university_email, username, password, subjects, sessions)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)

# --- SIDEBAR PROFILE BADGE ---
if "logged_in_prof" in st.session_state:
    st.sidebar.markdown(
        f"""
        <div class="profile-badge">
        <b>👤 {st.session_state['logged_in_prof']['username']}</b><br>
        <b>Email:</b> {st.session_state['logged_in_prof']['university_email']}<br>
        <b>Subjects:</b> {st.session_state['logged_in_prof']['subjects']}<br>
        <b>Sessions:</b> {st.session_state['logged_in_prof']['sessions']}
        </div>
        """, unsafe_allow_html=True
    )
