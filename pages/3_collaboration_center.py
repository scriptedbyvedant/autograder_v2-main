
# File: pages/3_collaboration_center.py
import streamlit as st
import pandas as pd
from database.postgres_handler import PostgresHandler

# --- AUTH CHECK ---
if "logged_in_prof" not in st.session_state or not st.session_state["logged_in_prof"]:
    st.warning("Please login first to access this page.", icon="🔒")
    st.stop()

prof = st.session_state["logged_in_prof"]
my_email = prof.get("university_email")

st.set_page_config(page_title="🤝 Collaboration Center", layout="wide")
st.title("🤝 Collaboration Center")

try:
    db = PostgresHandler()
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

# --- TABS ---
tab1, tab2 = st.tabs(["📊 Shared with Me", "📈 My Shares"])

# --- TAB 1: Items shared with the current user ---
with tab1:
    st.header("Grading Results Shared With You")
    try:
        shared_with_me_results = db.fetch_shared_with_me(my_email)
        if not shared_with_me_results:
            st.info("No one has shared any grading results with you yet.")
        else:
            st.write("The following results have been shared with you by colleagues. You can view the details, but you cannot edit them.")
            # Convert to DataFrame for better display
            df_shared = pd.DataFrame(shared_with_me_results)
            # Display a formatted table
            st.dataframe(df_shared[[
                'shared_by', 'student_id', 'assignment_no', 
                'question', 'new_score', 'created_at'
            ]], use_container_width=True)
            # In a future step, we could make these rows clickable to see details.

    except Exception as e:
        st.error(f"An error occurred while fetching shared results: {e}")

# --- TAB 2: Items the current user has shared ---
with tab2:
    st.header("The Results You Have Shared")
    try:
        my_shares = db.fetch_my_shares(my_email)
        if not my_shares:
            st.info("You have not shared any grading results yet.")
        else:
            st.write("You have shared the following results. You can revoke access at any time.")
            
            for share in my_shares:
                col1, col2, col3 = st.columns([3, 3, 1])
                with col1:
                    st.text(f"Shared with: {share['shared_with']}")
                with col2:
                    # We can fetch more details about the result if needed
                    st.text(f"Result ID: {share['result_id']} (Details can be shown here)")
                with col3:
                    revoke_key = f"revoke_{share['result_id']}_{share['shared_with']}"
                    if st.button("Revoke", key=revoke_key, help=f"Revoke access for {share['shared_with']}"):
                        try:
                            db.revoke_share(
                                owner_email=my_email,
                                target_email=share['shared_with'],
                                result_id=share['result_id']
                            )
                            st.success(f"Access revoked for {share['shared_with']}.")
                            st.rerun() # Rerun to update the list
                        except Exception as e:
                            st.error(f"Failed to revoke: {e}")
                st.divider()

    except Exception as e:
        st.error(f"An error occurred while fetching your shares: {e}")

