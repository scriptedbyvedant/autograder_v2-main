# File: pages/3_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.postgres_handler import PostgresHandler
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import numpy as np
from scipy.stats import pearsonr

# --- Page Config and Styling ---
st.set_page_config(page_title="📊 Autograder BI Portal", layout="wide")

def load_css():
    st.markdown("""
    <style>
        .stExpander { border: 1px solid #e0e0e0; border-radius: 10px; }
        .header-container { padding: 2rem; border-radius: 10px; background: linear-gradient(145deg, #e6f7ff, #c2e0f0); margin-bottom: 2rem; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .big-title { font-size: 3rem; font-weight: 800; color: #2b6777; font-family: 'Segoe UI', sans-serif; }
        .section-title { margin-top: 0.5rem; margin-bottom: 0.25rem; font-weight: 700; font-size: 1.1rem; }
        .subtle { color: #666; font-size: 0.9rem; }
        .divider { margin: 0.5rem 0 1.25rem 0; }
    </style>
    """, unsafe_allow_html=True)

# --- PDF Report Generation ---
def _fig_to_png_bytes(fig, width=840, height=480):
    """Render a Plotly figure to PNG bytes using Kaleido."""
    try:
        return fig.to_image(format="png", width=width, height=height)
    except Exception:
        # fallback to plotly default sizing if custom sizing fails
        return fig.to_image(format="png")


def generate_report_pdf(insights, figures):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.setFont("Helvetica-Bold", 18)
    p.drawString(inch, height - inch, "BI Portal Automated Insights Report")
    text_obj = p.beginText(inch, height - 1.5 * inch)
    for title, text in insights.items():
        text = text.replace("<b>", "").replace("</b>", "").replace("<strong>", "").replace("</strong>", "").replace("<br>", "\n")
        text_obj.setFont("Helvetica-Bold", 12)
        text_obj.textLine(title)
        text_obj.setFont("Helvetica", 10)
        for line in text.split('\n'):
            text_obj.textLine(line)
        text_obj.moveCursor(0, 20)
        if text_obj.getY() < 2 * inch:
            p.drawText(text_obj)
            p.showPage()
            text_obj = p.beginText(inch, height - 1.5 * inch)
    p.drawText(text_obj)

    # append dashboard figures on subsequent pages
    for title, fig in figures:
        try:
            img_bytes = _fig_to_png_bytes(fig)
        except Exception:
            continue
        p.showPage()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(inch, height - inch, title)
        image = ImageReader(BytesIO(img_bytes))
        img_w, img_h = image.getSize()
        max_w = width - 1.5 * inch
        max_h = height - 2.5 * inch
        scale = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (width - draw_w) / 2
        y = (height - draw_h) / 2
        p.drawImage(image, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')

    p.save()
    buffer.seek(0)
    return buffer

# --- Helpers ---
_QTYPE_ORDER = ["text", "coding", "math", "mcq", "table", "image", "other", "unknown"]

def infer_question_type(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype="string")
    s = series.fillna("").astype(str).str.lower()

    def classify(x: str) -> str:
        x = x.strip()
        if not x:
            return "unknown"
        if any(k in x for k in ["code", "coding", "program", "compile", "runtime", "function(", "class ", "python", "java", "c++", "bug", "algorithm"]):
            return "coding"
        if any(k in x for k in ["solve", "equation", "integral", "derivative", "matrix", "proof", "theorem", "calculate", "probability", "sum", "mean", "variance"]):
            return "math"
        if any(k in x for k in ["mcq", "multiple choice", "choose one", "choose the correct", "option a", "option b"]):
            return "mcq"
        if any(k in x for k in ["table", "tabular", "csv", "spreadsheet", "dataframe"]):
            return "table"
        if any(k in x for k in ["image", "figure", "diagram", "plot", "chart", "screenshot"]):
            return "image"
        if any(k in x for k in ["explain", "describe", "justify", "discuss", "essay", "short answer"]):
            return "text"
        return "other"

    return s.map(classify).astype("string")

def pct(n, d):
    return (n / d * 100) if d else 0.0

def calendar_heatmap(df_dates: pd.DataFrame, date_col: str, value_col: str = "count", title: str = "") -> go.Figure:
    """
    GitHub-style calendar heatmap (weeks x weekdays) using Plotly.
    """
    d = df_dates.copy()
    d[date_col] = pd.to_datetime(d[date_col]).dt.date

    # count per day
    if value_col not in d.columns:
        d = d.groupby(date_col).size().reset_index(name="count")
        value_col = "count"
    else:
        d = d.groupby(date_col)[value_col].sum().reset_index()

    if d.empty:
        return go.Figure()

    start_date = pd.to_datetime(min(d[date_col]))
    end_date = pd.to_datetime(max(d[date_col]))

    start_monday = start_date - pd.to_timedelta(start_date.weekday(), unit="D")
    end_sunday = end_date + pd.to_timedelta(6 - end_date.weekday(), unit="D")

    full_days = pd.DataFrame({date_col: pd.date_range(start_monday, end_sunday, freq="D").date})
    full_days = full_days.merge(d, on=date_col, how="left").fillna(0)

    dt = pd.to_datetime(full_days[date_col])
    full_days["weekday"] = dt.dt.weekday  # 0..6
    full_days["week_start"] = (dt - pd.to_timedelta(dt.dt.weekday, unit="D")).dt.date

    heat = full_days.pivot(index="weekday", columns="week_start", values=value_col)
    heat = heat.reindex(index=[0,1,2,3,4,5,6])  # Mon..Sun
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig = go.Figure(
        data=go.Heatmap(
            z=heat.values,
            x=[pd.to_datetime(x) for x in heat.columns],
            y=weekdays,
            colorscale=[[0.0, "#ebedf0"], [0.25, "#c6e48b"], [0.5, "#7bc96f"], [0.75, "#239a3b"], [1.0, "#196127"]],
            showscale=False,
            xgap=2, ygap=2,
            hovertemplate="Week of %{x|%b %d, %Y}<br>%{y}: %{z} submissions<extra></extra>"
        )
    )
    weeks = pd.Series(heat.columns)
    months = weeks.map(lambda d: pd.to_datetime(d).strftime("%b"))
    month_change = months.ne(months.shift(1))
    tickvals = weeks[month_change].map(pd.to_datetime)
    ticktext = months[month_change]
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(tickmode="array", tickvals=tickvals, ticktext=ticktext),
        yaxis=dict(autorange="reversed")
    )
    return fig

# --- Main Dashboard ---
def main():
    load_css()
    st.markdown("<div class='header-container'><p class='big-title'>📊 Autograder BI Portal</p></div>", unsafe_allow_html=True)

    if "logged_in_prof" not in st.session_state:
        st.warning("Please login first to access this page.", icon="🔒")
        st.stop()

    prof = st.session_state["logged_in_prof"]
    professor_id = prof.get("professor", "")
    my_email = prof.get("university_email", "")

    handler = PostgresHandler()
    my_df = pd.DataFrame(handler.fetch_my_results(professor_id))
    shared_df = pd.DataFrame(handler.fetch_shared_with_me(my_email))
    if not my_df.empty: my_df["__owner__"] = "My Grades"
    if not shared_df.empty: shared_df["__owner__"] = "Shared With Me"
    df = pd.concat([my_df, shared_df], ignore_index=True, sort=False)

    if df.empty:
        st.warning("No grading data available."); st.stop()

    for col in ["course", "semester", "assignment_no", "student_id", "question", "language"]:
        df[col] = df[col].apply(lambda x: "Unknown" if pd.isna(x) else x)
    df["score"] = pd.to_numeric(df["new_score"], errors="coerce").fillna(0)
    df['feedback_length'] = df['new_feedback'].str.len().fillna(0)
    df['created_at'] = pd.to_datetime(df['created_at'])

    st.sidebar.title("🛠️ Controls & Filters")
    owner = st.sidebar.selectbox("Data Source", ["All"] + list(df["__owner__"].unique()))
    if owner != "All": df = df[df["__owner__"] == owner].copy()
    opts = lambda c: ["All"] + sorted(df[c].unique())
    course = st.sidebar.selectbox("Course", opts("course"))
    semester = st.sidebar.selectbox("Semester", opts("semester"))
    assignment = st.sidebar.selectbox("Assignment", opts("assignment_no"))
    
    mask = pd.Series(True, index=df.index)
    if course != "All": mask &= df["course"] == course
    if semester != "All": mask &= df["semester"] == semester
    if assignment != "All": mask &= df["assignment_no"] == assignment
    filtered = df[mask]

    if filtered.empty:
        st.warning("No data for the selected filters."); st.stop()

    # --- Student summary & segments
    student_summary = filtered.groupby("student_id").agg(
        avg_score=("score", "mean"),
        submission_count=("id", "count")
    ).reset_index()

    if not student_summary.empty:
        avg_score_median = student_summary.avg_score.median()
        submission_median = student_summary.submission_count.median()

        def get_quadrant(row):
            if row.avg_score >= avg_score_median and row.submission_count >= submission_median:
                return "High Achievers"
            if row.avg_score < avg_score_median and row.submission_count >= submission_median:
                return "High Effort, Low Score"
            return "At-Risk"

        student_summary["quadrant"] = student_summary.apply(get_quadrant, axis=1)
        student_summary["rank"] = student_summary["avg_score"].rank(ascending=False, method="min")

    all_insights = {}
    export_figures = []
    tabs = st.tabs(["🚀 Executive Summary", "🧑‍🎓 Student Analytics", "📚 Curricular Insights", "📈 Reporting & Insights"])

    # ------------------------------- EXECUTIVE SUMMARY -------------------------------
    with tabs[0]:
        st.subheader("Executive Performance Report")
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Total Submissions", f"{len(filtered):,}")
        kpi_cols[1].metric("Overall Average Score", f"{filtered['score'].mean():.2f}%")
        kpi_cols[2].metric("Students Analyzed", f"{filtered['student_id'].nunique():,}")
        kpi_cols[3].metric("Assignments Covered", f"{filtered['assignment_no'].nunique():,}")
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='section-title'>Performance Over Time</div>", unsafe_allow_html=True)
            ts_data = filtered.set_index('created_at').resample('M')['score'].mean().reset_index()
            fig_month = px.line(ts_data, x='created_at', y='score', title="Monthly Average Score Trend", markers=True)
            st.plotly_chart(
                fig_month,
                use_container_width=True,
                key="trend_monthly_avg"
            )
            if len(ts_data) > 1:
                first_score, last_score = ts_data['score'].iloc[0], ts_data['score'].iloc[-1]
                trend_change = ((last_score - first_score) / first_score) * 100 if first_score > 0 else 0
                trend_desc = "increasing" if trend_change > 5 else "decreasing" if trend_change < -5 else "stable"
                best_month = ts_data.loc[ts_data['score'].idxmax()]
                worst_month = ts_data.loc[ts_data['score'].idxmin()]
                insight = (
                    f"Momentum is **{trend_desc}** (**{trend_change:+.1f}%**). "
                    f"Peak: **{best_month['created_at'].strftime('%b %Y')}** (**{best_month['score']:.1f}%**). "
                    f"Low: **{worst_month['created_at'].strftime('%b %Y')}** (**{worst_month['score']:.1f}%**)."
                )
            else:
                insight = "Need more months to infer direction."
            all_insights["Monthly Performance Trend"] = insight
            export_figures.append(("Monthly Average Score Trend", fig_month))

            st.markdown("<div class='section-title'>Course Performance Leaderboard</div>", unsafe_allow_html=True)
            course_perf = filtered.groupby('course')['score'].mean().sort_values(ascending=False).reset_index()
            fig_course = px.bar(course_perf, x='score', y='course', orientation='h', title="Course Average Score Leaderboard")
            st.plotly_chart(
                fig_course,
                use_container_width=True,
                key="course_leaderboard"
            )
            if len(course_perf) > 1:
                top_course, bottom_course = course_perf.iloc[0], course_perf.iloc[-1]
                gap = top_course['score'] - bottom_course['score']
                insight = (
                    f"**{top_course['course']}** leads (**{top_course['score']:.1f}%**). "
                    f"Gap to lowest (**{bottom_course['course']}**) is **{gap:.1f}** pts → prioritize support for the tail."
                )
            elif not course_perf.empty:
                insight = f"Only **{course_perf.iloc[0]['course']}** present (**{course_perf.iloc[0]['score']:.1f}%**)."
            all_insights["Course Leaderboard"] = insight
            export_figures.append(("Course Average Score Leaderboard", fig_course))

        with col2:
            st.markdown("<div class='section-title'>Student Segmentation</div>", unsafe_allow_html=True)
            if not student_summary.empty:
                quadrant_dist = student_summary['quadrant'].value_counts()
                fig_seg = px.pie(quadrant_dist, names=quadrant_dist.index, values=quadrant_dist.values,
                                 hole=0.45, title="Student Performance Segments")
                st.plotly_chart(fig_seg, use_container_width=True, key="seg_pie_exec")
                total = quadrant_dist.sum()
                top_seg = quadrant_dist.idxmax()
                top_pct = pct(quadrant_dist.max(), total)
                risk_pct = pct(quadrant_dist.get("At-Risk", 0), total)
                imbalance = (quadrant_dist.max() - quadrant_dist.min()) / total if total else 0
                insight = (
                    f"**{top_seg}** dominate (**{top_pct:.1f}%**). "
                    f"**At-Risk**: **{risk_pct:.1f}%**. "
                    f"Imbalance **{imbalance:.2f}** → "
                    f"{'reallocate support to at-risk cohort' if risk_pct >= 25 else 'mix looks healthy'}."
                )
                all_insights["Student Segmentation Pie"] = insight
                export_figures.append(("Student Performance Segments", fig_seg))

            st.markdown("<div class='section-title'>Submission Volume vs. Performance</div>", unsafe_allow_html=True)
            assignment_summary = filtered.groupby('assignment_no').agg(
                submission_count=('id', 'count'),
                avg_score=('score', 'mean')
            ).reset_index()
            fig_assign_scatter = px.scatter(
                assignment_summary,
                x='submission_count',
                y='avg_score',
                size='submission_count',
                color='avg_score',
                hover_name='assignment_no',
                title="Assignment Volume vs. Score"
            )
            st.plotly_chart(
                fig_assign_scatter,
                use_container_width=True,
                key="assign_vol_vs_score"
            )
            if not assignment_summary.empty:
                corr = assignment_summary[['submission_count','avg_score']].corr().iloc[0,1]
                insight = f"Volume↔score correlation **{corr:+.2f}** — {'harder items attract more attempts' if corr < -0.2 else 'no strong pattern'}."
            else:
                insight = "No assignment aggregates."
            all_insights["Volume vs Performance"] = insight
            export_figures.append(("Assignment Volume vs. Score", fig_assign_scatter))

    # ------------------------------- STUDENT ANALYTICS -------------------------------
    with tabs[1]:
        st.header("Student Analytics")

        # ===== A. Overview (one chart) =====
        st.markdown("### A. Overview")
        st.markdown("<p class='subtle'>Quick look at overall segmentation.</p>", unsafe_allow_html=True)
        if not student_summary.empty:
            seg_counts = student_summary['quadrant'].value_counts()
            fig_over = px.pie(seg_counts, names=seg_counts.index, values=seg_counts.values, hole=0.45, title="Performance Segments")
            st.plotly_chart(fig_over, use_container_width=True, key="seg_pie_overview_only")
            total = seg_counts.sum()
            risk_pct = pct(seg_counts.get("At-Risk", 0), total)
            achiever_pct = pct(seg_counts.get("High Achievers", 0), total)
            imbalance = (seg_counts.max() - seg_counts.min()) / total if total else 0
            insight = (
                f"**At-Risk {risk_pct:.1f}% vs High Achievers {achiever_pct:.1f}%**. "
                f"Spread: **{imbalance:.2f}** → {'target remediation' if risk_pct >= 25 else 'balanced split'}."
            )
            export_figures.append(("Performance Segments Overview", fig_over))

        st.markdown("---")

        # ===== B. Student Explorer =====
        st.markdown("### B. Student Explorer")
        st.markdown("<p class='subtle'>Pick a student to drill into their patterns and outcomes.</p>", unsafe_allow_html=True)

        if not student_summary.empty:
            default_student = student_summary.sort_values("rank").iloc[0]["student_id"]
            options_sorted = sorted(student_summary['student_id'].unique())
            default_index = options_sorted.index(default_student)
            selected_student = st.selectbox("Select a student", options=options_sorted, index=default_index)

            student_data = filtered[filtered['student_id'] == selected_student]

            # KPIs
            s_info = student_summary[student_summary.student_id == selected_student].iloc[0]
            k1, k2, k3 = st.columns(3)
            k1.metric("Average Score", f"{s_info.avg_score:.2f}%")
            k2.metric("Total Submissions", f"{s_info.submission_count}")
            k3.metric("Class Rank", f"#{int(s_info['rank'])} of {len(student_summary)}")

            # Row 1: Assignment table + bar (with row 0 and row 4 removed)
            c1, c2 = st.columns([1.1, 1.2])
            with c1:
                st.markdown("<div class='section-title'>Assignment Averages</div>", unsafe_allow_html=True)
                assignment_scores = (
                    student_data.groupby('assignment_no')['score']
                    .mean()
                    .reset_index()
                    .sort_values("assignment_no")
                    .reset_index(drop=True)
                )
                assignment_scores_filtered = assignment_scores.drop(index=[0, 4], errors="ignore").reset_index(drop=True)
                st.dataframe(assignment_scores_filtered, use_container_width=True)

                if len(assignment_scores_filtered) >= 2:
                    a_nums = pd.to_numeric(assignment_scores_filtered['assignment_no'], errors='coerce')
                    valid = ~a_nums.isna()
                    r = pearsonr(a_nums[valid], assignment_scores_filtered.loc[valid, 'score'])[0] if valid.sum() >= 2 else np.nan
                    rng = assignment_scores_filtered['score'].max() - assignment_scores_filtered['score'].min()
                    sd = assignment_scores_filtered['score'].std(ddof=0)
                    best = assignment_scores_filtered.iloc[assignment_scores_filtered['score'].idxmax()]
                    worst = assignment_scores_filtered.iloc[assignment_scores_filtered['score'].idxmin()]
                    trend_txt = "steady upward (r={:+.2f})".format(r) if r > 0.25 else "declining (r={:+.2f})".format(r) if r < -0.25 else "no clear progression"
                    insight = (
                        f"Trend **{trend_txt}**. Spread **{rng:.1f} pts** (σ={sd:.1f}). "
                        f"Best: **{str(best['assignment_no'])}** (**{best['score']:.1f}%**); "
                        f"Lowest: **{str(worst['assignment_no'])}** (**{worst['score']:.1f}%**)."
                    )
                else:
                    insight = "Not enough assignments after filtering to assess trend."

            with c2:
                st.markdown("<div class='section-title'>Performance by Assignment</div>", unsafe_allow_html=True)
                bar_df = assignment_scores_filtered.copy()
                bar_df["assignment_no"] = bar_df["assignment_no"].astype(str)
                fig_bar = px.bar(bar_df, x='assignment_no', y='score', title='Average Score per Assignment')
                fig_bar.update_layout(xaxis=dict(type="category", categoryorder="category ascending"))
                st.plotly_chart(fig_bar, use_container_width=True, key="student_perf_bar_explorer")
                if not bar_df.empty:
                    mid = bar_df['score'].median()
                    above = (bar_df['score'] >= mid).sum()
                    insight = f"{above}/{len(bar_df)} assignments at/above median (**{mid:.1f}%**). Target those below for remediation."
                else:
                    insight = "No assignments available after row filtering."
                export_figures.append(("Average Score per Assignment", fig_bar))

            # Row 2: Monthly submissions + Semester progression
            c3, c4 = st.columns(2)
            with c3:
                st.markdown("<div class='section-title'>Monthly Submission Distribution</div>", unsafe_allow_html=True)
                monthly_submissions = student_data['created_at'].dt.strftime('%B').value_counts().reset_index()
                monthly_submissions.columns = ['Month', 'Submissions']
                fig_monthly = px.pie(monthly_submissions, names='Month', values='Submissions', hole=0.4, title='Submissions by Month')
                st.plotly_chart(fig_monthly, use_container_width=True, key="student_monthly_submissions_explorer")
                if not monthly_submissions.empty:
                    top_month = monthly_submissions.iloc[0]
                    bottom_month = monthly_submissions.iloc[-1]
                    insight = f"Peak **{top_month['Month']}** ({top_month['Submissions']}); quietest **{bottom_month['Month']}** → schedule nudges then."
                else:
                    insight = "No monthly activity found."
                export_figures.append(("Submissions by Month", fig_monthly))
            with c4:
                st.markdown("<div class='section-title'>Semester-wise Progression</div>", unsafe_allow_html=True)
                student_semester_avg = student_data.groupby('semester')['score'].mean().reset_index()
                class_semester_avg = filtered.groupby('semester')['score'].mean().reset_index()
                semester_comparison = pd.merge(student_semester_avg, class_semester_avg, on='semester', suffixes=('_student', '_class'))
                fig_sem = go.Figure()
                fig_sem.add_trace(go.Scatter(x=semester_comparison['semester'], y=semester_comparison['score_student'], mode='lines+markers', name='Student'))
                fig_sem.add_trace(go.Scatter(x=semester_comparison['semester'], y=semester_comparison['score_class'], mode='lines+markers', name='Class Avg'))
                st.plotly_chart(fig_sem, use_container_width=True, key="student_vs_class_line_explorer")
                if not semester_comparison.empty:
                    delta = semester_comparison['score_student'].mean() - semester_comparison['score_class'].mean()
                    trend = "above" if delta >= 0 else "below"
                    insight = f"On average, student is **{abs(delta):.1f} pts** {trend} class across semesters."
                else:
                    insight = "Not enough semester data to compare."
                export_figures.append(("Semester-wise Progression", fig_sem))

            # Row 3: Question type vs score + CALENDAR HEATMAP timestamps
            c5, c6 = st.columns(2)
            with c5:
                st.markdown("<div class='section-title'>Question Type vs Score</div>", unsafe_allow_html=True)
                if 'question_type' in student_data.columns:
                    qtype_series = student_data['question_type'].fillna('unknown').astype(str).str.lower()
                else:
                    q_col = 'question' if 'question' in student_data.columns else None
                    qtype_series = infer_question_type(student_data[q_col]) if q_col else pd.Series(["unknown"] * len(student_data), index=student_data.index, dtype="string")
                qtype_series = qtype_series.replace({'short answer': 'text', 'essay': 'text', 'free text': 'text', 'multiple choice': 'mcq', 'select one': 'mcq'}).fillna('unknown').astype(str)
                qtype_df = student_data.assign(qtype=qtype_series)
                qtype_avg = qtype_df.groupby('qtype', as_index=False)['score'].mean()
                qtype_avg['qtype'] = pd.Categorical(qtype_avg['qtype'], categories=_QTYPE_ORDER, ordered=True)
                qtype_avg = qtype_avg.sort_values('qtype')
                fig_qtype = px.bar(qtype_avg, x='qtype', y='score', title='Avg Score by Question Type')
                st.plotly_chart(fig_qtype, use_container_width=True, key="student_qtype_vs_score_bar_explorer")
                if not qtype_avg.empty:
                    best = qtype_avg.iloc[qtype_avg['score'].idxmax()]
                    worst = qtype_avg.iloc[qtype_avg['score'].idxmin()]
                    gap = best['score'] - worst['score']
                    insight = f"Strongest on **{best['qtype']}**; weakest on **{worst['qtype']}** (gap **{gap:.1f} pts**). Target low types first."
                else:
                    insight = "No question-type info."
                export_figures.append(("Avg Score by Question Type", fig_qtype))
            with c6:
                st.markdown("<div class='section-title'>Submission Timestamps (Calendar)</div>", unsafe_allow_html=True)
                cal_df = student_data[['created_at']].copy()
                fig_cal = calendar_heatmap(cal_df, 'created_at', title="Weekly Activity Calendar")
                st.plotly_chart(fig_cal, use_container_width=True, key="submission_calendar_heatmap")
                if not cal_df.empty:
                    total_days = cal_df['created_at'].dt.date.nunique()
                    total_subs = len(cal_df)
                    insight = f"Work across **{total_days}** days (**{total_subs} submissions**). Cluster dark weeks for timely feedback."
                else:
                    insight = "No timestamp data."
                export_figures.append(("Weekly Activity Calendar", fig_cal))

        st.markdown("---")

        # ===== C. Comparison =====
        st.markdown("### C. Comparison")
        st.markdown("<p class='subtle'>Compare the selected student to class averages by assignment.</p>", unsafe_allow_html=True)
        if not student_summary.empty:
            selected_student = selected_student if 'selected_student' in locals() else student_summary.sort_values("rank").iloc[0]["student_id"]
            student_data = filtered[filtered['student_id'] == selected_student]
            class_avg_data = filtered.groupby("assignment_no").agg(avg_score=("score", "mean")).reset_index()
            student_avg_data = student_data.groupby("assignment_no").agg(avg_score=("score", "mean")).reset_index()
            merged_data = pd.merge(student_avg_data, class_avg_data, on="assignment_no", suffixes=('_student', '_class'))
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=merged_data['avg_score_student'], theta=merged_data['assignment_no'], fill='toself', name=f"{selected_student}"))
            fig_radar.add_trace(go.Scatterpolar(r=merged_data['avg_score_class'], theta=merged_data['assignment_no'], fill='toself', name='Class Avg'))
            fig_radar.update_layout(title="Student vs Class by Assignment")
            st.plotly_chart(fig_radar, use_container_width=True, key="student_vs_class_radar_comparison")
            if not merged_data.empty:
                better = (merged_data['avg_score_student'] > merged_data['avg_score_class']).sum()
                worse = (merged_data['avg_score_student'] < merged_data['avg_score_class']).sum()
                insight = f"Outperforms on **{better}** assignments, underperforms on **{worse}** → address deficits first."
            else:
                insight = "No overlapping assignments to compare."
            export_figures.append(("Student vs Class by Assignment", fig_radar))

    # ------------------------------- CURRICULAR INSIGHTS (Professional dashboard) -------------------------------
    with tabs[2]:
        st.subheader("Curricular Insights")

        # In-tab filters
        cur_col1, cur_col2 = st.columns(2)
        with cur_col1:
            cur_course = st.selectbox("Filter by Course (Curricular)", ["All"] + sorted(filtered['course'].dropna().unique().tolist()), key="curr_course_sel")
        with cur_col2:
            cur_semester = st.selectbox("Filter by Semester (Curricular)", ["All"] + sorted(filtered['semester'].dropna().unique().tolist()), key="curr_semester_sel")

        cur_df = filtered.copy()
        if cur_course != "All":
            cur_df = cur_df[cur_df['course'] == cur_course]
        if cur_semester != "All":
            cur_df = cur_df[cur_df['semester'] == cur_semester]

        if cur_df.empty:
            st.info("No data for the selected course/semester in Curricular Insights.")
        else:
            # ---- 1) Assignment Difficulty: Distribution by Assignment (Boxplot)
            st.markdown("#### Assignment Difficulty — Score Distribution")
            fig_box = px.box(cur_df, x='assignment_no', y='score', points='outliers', title='Score Distribution per Assignment')
            fig_box.update_layout(xaxis=dict(type='category', categoryorder='category ascending'))
            st.plotly_chart(fig_box, use_container_width=True, key="curr_box_assign")
            # Insight
            spread = cur_df.groupby('assignment_no')['score'].agg(lambda s: s.quantile(0.75)-s.quantile(0.25)).reset_index(name='IQR')
            if not spread.empty:
                worst = spread.sort_values('IQR', ascending=False).iloc[0]
                insight = f"Greatest variability on assignment **{str(worst['assignment_no'])}** (IQR **{worst['IQR']:.1f}** pts) → standardize rubric or provide scaffolds."
            else:
                insight = "Insufficient variability to assess distribution differences."
            export_figures.append(("Score Distribution per Assignment", fig_box))

            # ---- 2) Question Bank: Avg Score vs Volume (Bubble)
            st.markdown("#### Question Bank — Average vs Volume")
            qbank = cur_df.groupby(['assignment_no','question']).agg(avg_score=('score','mean'), submissions=('id','count')).reset_index()
            if not qbank.empty:
                fig_bubble = px.scatter(qbank, x='avg_score', y='submissions', size='submissions', color='assignment_no',
                                       hover_name='question', title='Question Average Score vs Submission Volume',
                                       labels={'avg_score':'Average Score','submissions':'Submissions'})
                st.plotly_chart(fig_bubble, use_container_width=True, key="curr_bubble_qbank")
                # Insight
                low_avg_high_vol = qbank[(qbank['avg_score'] < qbank['avg_score'].median()) & (qbank['submissions'] > qbank['submissions'].median())]
                if not low_avg_high_vol.empty:
                    row = low_avg_high_vol.sort_values('avg_score').iloc[0]
                    insight = f"High-impact fix: **Q{row['question']}** in **A{row['assignment_no']}** is low-scoring (**{row['avg_score']:.1f}%**) yet popular (**{row['submissions']}** submissions)."
                else:
                    insight = "No question stands out as both low-scoring and high-volume."
                export_figures.append(("Question Avg Score vs Volume", fig_bubble))
            else:
                st.info("No question-level aggregates to plot.")
            
            # ---- 3) Language Coverage Heatmap
            st.markdown("#### Language Coverage by Assignment")
            lang_counts = cur_df.groupby(['assignment_no','language']).size().reset_index(name='count')
            if not lang_counts.empty:
                pivot = lang_counts.pivot_table(index='language', columns='assignment_no', values='count', fill_value=0)
                fig_lang = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns.astype(str), y=pivot.index, coloraxis="coloraxis"))
                fig_lang.update_layout(title="Submissions per Language × Assignment", coloraxis=dict(colorscale="Blues"))
                st.plotly_chart(fig_lang, use_container_width=True, key="curr_lang_heat")
                # Insight
                dom = lang_counts.groupby('language')['count'].sum().sort_values(ascending=False)
                if len(dom) >= 1:
                    top_lang, share = dom.index[0], pct(dom.iloc[0], dom.sum())
                    insight = f"**{top_lang}** dominates (**{share:.1f}%** of submissions). Ensure parity of examples for lesser-used languages."
                else:
                    insight = "Language mix is too sparse for conclusions."
                export_figures.append(("Language Coverage Heatmap", fig_lang))
            else:
                st.info("No language/assignment combinations found.")

    # ------------------------------- REPORTING & INSIGHTS (Professional dashboard) -------------------------------
    with tabs[3]:
        st.subheader("Reporting & Insights")

        # ---- 1) Yearly Performance & Volume (Dual-axis)
        years = filtered['created_at'].dt.year.rename('year')
        yearly = pd.concat([filtered['score'], years], axis=1)
        yearly_agg = yearly.groupby('year').agg(avg_score=('score','mean'), submissions=('score','count')).reset_index()
        if not yearly_agg.empty:
            fig_year = go.Figure()
            fig_year.add_bar(x=yearly_agg['year'], y=yearly_agg['submissions'], name='Submissions', yaxis='y1')
            fig_year.add_trace(go.Scatter(x=yearly_agg['year'], y=yearly_agg['avg_score'], name='Avg Score', mode='lines+markers', yaxis='y2'))
            fig_year.update_layout(
                title="Yearly Performance & Volume",
                yaxis=dict(title="Submissions"),
                yaxis2=dict(title="Avg Score", overlaying='y', side='right', rangemode="tozero"),
                xaxis=dict(type='category'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(l=10, r=10, t=60, b=10)
            )
            st.plotly_chart(fig_year, use_container_width=True, key="rep_year_dual")
            if len(yearly_agg) > 1:
                base = max(yearly_agg['avg_score'].iloc[0], 1e-6)
                growth = (yearly_agg['avg_score'].iloc[-1] - yearly_agg['avg_score'].iloc[0]) / base * 100
                insight = f"Avg score **{growth:+.1f}%** from first to last year; throughput now **{int(yearly_agg['submissions'].iloc[-1])}**."
            else:
                insight = "Single year available; trend not computed."
            export_figures.append(("Yearly Performance & Volume", fig_year))
        else:
            st.info("No yearly data available.")

        # ---- 2) Weekly Throughput with 7-day Moving Average
        wk = filtered.set_index('created_at').resample('W')['id'].count().rename('submissions').reset_index()
        if not wk.empty:
            wk['ma'] = wk['submissions'].rolling(4, min_periods=1).mean()  # ~4 weeks ~ month MA
            fig_wk = go.Figure()
            fig_wk.add_bar(x=wk['created_at'], y=wk['submissions'], name='Weekly Submissions')
            fig_wk.add_trace(go.Scatter(x=wk['created_at'], y=wk['ma'], name='4-week MA', mode='lines'))
            fig_wk.update_layout(title="Weekly Throughput & 4-week Moving Average", xaxis_title="Week", yaxis_title="Submissions", margin=dict(l=10,r=10,t=60,b=10))
            st.plotly_chart(fig_wk, use_container_width=True, key="rep_weekly_ma")
            if len(wk) > 4:
                recent = wk['submissions'].tail(4).mean()
                prior = wk['submissions'].iloc[-8:-4].mean() if len(wk) >= 8 else wk['submissions'].head(4).mean()
                delta = (recent - prior) / max(prior, 1e-6) * 100
                insight = f"Throughput last ~4 weeks is **{recent:.0f}/wk**, {delta:+.1f}% vs the prior period."
            else:
                insight = "Not enough weeks to compare moving windows."
            export_figures.append(("Weekly Throughput & Moving Average", fig_wk))
        else:
            st.info("No weekly activity to plot.")

        # ---- 3) Score Quality Distribution (Histogram + Violin)
        fig_hist = px.histogram(filtered, x='score', nbins=20, marginal='violin', title="Score Quality Distribution")
        st.plotly_chart(fig_hist, use_container_width=True, key="rep_score_hist")
        if not filtered.empty:
            median = filtered['score'].median()
            p25 = filtered['score'].quantile(0.25)
            p75 = filtered['score'].quantile(0.75)
            insight = f"Median **{median:.1f}%** (IQR **{p25:.1f}–{p75:.1f}%**). Use tails for targeted coaching and re-assessment."
        else:
            insight = "No score data."
        export_figures.append(("Score Quality Distribution", fig_hist))

        # ---- 4) Language Mix (Treemap)
        lang_counts = filtered['language'].value_counts().reset_index()
        lang_counts.columns = ['language','count']
        if not lang_counts.empty:
            fig_tree = px.treemap(lang_counts, path=['language'], values='count', title="Language Mix (Submissions)")
            st.plotly_chart(fig_tree, use_container_width=True, key="rep_lang_treemap")
            if len(lang_counts) > 1:
                share = lang_counts['count'].iloc[0] / lang_counts['count'].sum() * 100
                insight = f"Top language holds **{share:.1f}%** share; consider secondary materials for the rest."
            else:
                insight = "Single-language dataset."
            export_figures.append(("Language Mix", fig_tree))
        else:
            st.info("No language data for treemap.")

    # --- Export PDF ---
    pdf_bytes = generate_report_pdf(all_insights, export_figures)
    st.sidebar.title("Export Report")
    st.sidebar.download_button(
        label="Download Full Report (PDF)",
        data=pdf_bytes,
        file_name="BI_Portal_Insights_Report.pdf",
        mime="application/pdf",
    )

if __name__ == "__main__":
    main()
