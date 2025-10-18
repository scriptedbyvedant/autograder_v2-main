import streamlit as st
from database.postgres_handler import PostgresHandler

st.set_page_config(page_title="My Profile", layout="wide")

if "logged_in_prof" not in st.session_state:
    st.warning("Please login first to access this page.")
    st.stop()

prof_sess = st.session_state["logged_in_prof"]

# --- Fetch latest professor info from database ---
def get_prof_from_db(email):
    prof = PostgresHandler().fetch_professor_by_email(email)
    return prof or {}

# --- All valid subject options, multi-value flatten ---
def get_all_subjects():
    raw = PostgresHandler().fetch_subjects() or []
    all_subjs = set()
    for subj_str in raw:
        if subj_str:
            if isinstance(subj_str, str):
                for subj in subj_str.split(','):
                    if subj.strip():
                        all_subjs.add(subj.strip())
    return sorted(all_subjs)

def get_all_sessions():
    raw = PostgresHandler().fetch_sessions() or []
    all_sess = set()
    for sess_str in raw:
        if sess_str:
            if isinstance(sess_str, str):
                for sess in sess_str.split(','):
                    if sess.strip():
                        all_sess.add(sess.strip())
    return sorted(all_sess)

prof_db = get_prof_from_db(prof_sess["university_email"])

if not prof_db:
    st.error("Unable to load profile from the database.")
    st.stop()

profile_pic_bytes = prof_db.get("profile_pic")
name = prof_db.get("username", "")
university_email = prof_db.get("university_email", "")

# Multi-value aware
all_subjects = get_all_subjects()
all_sessions = get_all_sessions()
current_subjects = [s.strip() for s in (prof_db.get("subjects") or "").split(",") if s.strip()]
current_sessions = [s.strip() for s in (prof_db.get("session") or "").split(",") if s.strip()]

# --- Layout and Styles ---
st.markdown("""
    <style>
    .profile-pic { border-radius: 50%; width: 120px; height: 120px; object-fit: cover; border: 2px solid #e2e2e2; margin-bottom: 8px; }
    .section-header { font-size: 1.13em; font-weight: 600; margin-bottom: 12px; color: #234488; letter-spacing: 0.02em; }
    .pref-block { background: #f8f9fb; padding: 18px 23px 12px 23px; border-radius: 11px; margin-top: 14px; box-shadow: 0 2px 6px #4562af08; }
    .security-block { background: #f3f4f6; padding: 20px 22px 10px 22px; border-radius: 10px; margin-top: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("Profile & Account Settings")

col_pic, col_main = st.columns([1, 2.7])

# --- Profile Photo Upload & Preview ---
with col_pic:
    st.markdown('<div class="section-header">Profile Photo</div>', unsafe_allow_html=True)
    if profile_pic_bytes:
        st.image(profile_pic_bytes, width=120, caption="Current", use_column_width=False)
    uploaded_pic = st.file_uploader("Upload new photo", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if uploaded_pic:
        profile_pic_bytes = uploaded_pic.getvalue()
        st.image(profile_pic_bytes, width=120, caption="Preview", use_column_width=False)

# --- Personal Info Form (multi-value aware) ---
with col_main:
    st.markdown('<div class="section-header">Personal Information</div>', unsafe_allow_html=True)
    with st.form("update_profile"):
        updated_name = st.text_input("Name", value=name)
        updated_email = st.text_input("University Email", value=university_email, disabled=True)
        updated_sessions = st.multiselect(
            "Sessions",
            options=all_sessions,
            default=current_sessions
        )
        updated_subjects = st.multiselect(
            "Subjects",
            options=all_subjects,
            default=current_subjects
        )
        save_btn = st.form_submit_button("Save Changes")

    if save_btn:
        try:
            PostgresHandler().update_professor(
                university_email=updated_email,
                username=updated_name,
                subjects=",".join(updated_subjects),
                session=",".join(updated_sessions),
                profile_pic=profile_pic_bytes,
            )
            st.success("Profile updated successfully.")
            # Refresh session with updated values
            st.session_state["logged_in_prof"].update({
                "username": updated_name,
                "subjects": ",".join(updated_subjects),
                "session": ",".join(updated_sessions),
            })
        except Exception as e:
            st.error(f"Update failed: {e}")

st.markdown("---")

# --- Security Section: Password Change ---
st.markdown('<div class="section-header">Security</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="security-block">', unsafe_allow_html=True)
    with st.form("password_change"):
        current_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_pw = st.text_input("Confirm New Password", type="password")
        change_btn = st.form_submit_button("Change Password")
    st.markdown('</div>', unsafe_allow_html=True)

    if change_btn:
        if not current_pw or not new_pw or not confirm_pw:
            st.error("All password fields are required.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        else:
            valid = PostgresHandler().verify_professor_password(university_email, current_pw)
            if not valid:
                st.error("Current password is incorrect.")
            else:
                try:
                    PostgresHandler().update_professor_password(university_email, new_pw)
                    st.success("Password updated successfully.")
                except Exception as e:
                    st.error(f"Password update failed: {e}")

st.markdown(
    "<div style='color:#888; font-size:14px; margin-top: 20px;'>"
    "To protect your account, use a strong password and update it regularly."
    "</div>",
    unsafe_allow_html=True
)
