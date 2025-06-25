
import streamlit as st
import requests
from edututor.watsonx_client import generate_quiz
from google_oauth import get_authorization_url, get_user_info
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

st.set_page_config(page_title="EduTutor Unified App", layout="wide")
st.title("🎓 EduTutor - Unified Learning Dashboard")

# --- Sidebar Role & Login ---
role = st.sidebar.radio("👥 Select your role", ["Student", "Educator"])
st.sidebar.subheader("🔐 Login")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

# Google OAuth login
if not st.session_state["logged_in"]:
    if st.sidebar.button("Login with Google"):
        auth_url, state = get_authorization_url()
        st.session_state["auth_url"] = auth_url
        st.session_state["oauth_state"] = state
        st.markdown(f"[👉 Click here to login with Google]({auth_url})")

    query_params = st.query_params
    if "code" in query_params:
        try:
            user_info, access_token = get_user_info(query_params["code"])
            st.session_state["logged_in"] = True
            st.session_state["user_email"] = user_info.get("email", "unknown_user")
            st.session_state["access_token"] = access_token
            st.sidebar.success(f"✅ Logged in as {st.session_state['user_email']}")
        except Exception as e:
            st.sidebar.error(f"❌ Login failed: {e}")
else:
    st.sidebar.success(f"✅ Logged in as {st.session_state['user_email']}")

user_id = st.session_state.get("user_email", "user_001")

# =======================
# === STUDENT VIEW ======
# =======================
if role == "Student":
    st.header("📘 Student Dashboard")
    tab1, tab2, tab3 = st.tabs(["📝 Take Quiz", "📄 Quiz History", "🏫 Google Classroom"])

    # --- TAB 1: Take Quiz ---
    with tab1:
        topic = st.text_input("Enter quiz topic", "Machine Learning")
        num_questions = st.slider("Number of questions", 1, 10, 5)

        if st.button("🚀 Generate Quiz"):
            with st.spinner("Generating quiz..."):
                try:
                    quiz_data = generate_quiz(topic, num_questions)
                    st.session_state["quiz"] = quiz_data
                    st.session_state["submitted"] = False
                except Exception as e:
                    st.error(f"❌ Quiz generation failed: {e}")

        if "quiz" in st.session_state and not st.session_state.get("submitted", False):
            st.subheader(f"Quiz on {topic}")
            answers = []
            with st.form("quiz_form"):
                for idx, q in enumerate(st.session_state["quiz"]):
                    st.write(f"**Q{idx+1}: {q['question']}**")
                    selected = st.radio("Select your answer", q["options"], key=f"q{idx}")
                    answers.append((q, selected))
                submitted = st.form_submit_button("✅ Submit Quiz")

            if submitted:
                correct = 0
                result_display = []
                for idx, (q, selected) in enumerate(answers):
                    selected_letter = selected.split(".")[0].strip()
                    is_correct = selected_letter == q["answer"]
                    if is_correct:
                        correct += 1
                    result_display.append((idx + 1, q["question"], selected, q["answer"], is_correct))

                st.session_state["submitted"] = True
                st.success(f"🎯 Your Score: {correct}/{len(answers)}")

                embedding = [round(0.01 * i, 4) for i in range(1024)]
                payload = {
                    "user_id": user_id,
                    "topic": topic,
                    "score": correct,
                    "embedding": embedding
                }
                try:
                    res = requests.post("http://localhost:8000/submit-quiz", json=payload)
                    if res.status_code == 200:
                        st.success("✅ Quiz data stored in Pinecone.")
                    else:
                        st.warning("⚠️ Quiz submission failed.")
                except Exception as e:
                    st.error(f"❌ Backend error: {e}")

                st.subheader("📊 Review")
                for i, question, chosen, correct_ans, status in result_display:
                    st.write(f"**Q{i}: {question}**")
                    st.write(f"- Your Answer: {chosen}")
                    st.write(f"- Correct Answer: {correct_ans}")
                    st.markdown("- ✅ Correct" if status else "- ❌ Incorrect")
                    st.markdown("---")

        if st.session_state.get("submitted", False):
            if st.button("🔁 Try another quiz"):
                del st.session_state["quiz"]
                st.session_state["submitted"] = False

    # --- TAB 2: Quiz History (To Be Integrated) ---
    with tab2:
        st.info("📄 Quiz history feature coming soon.")

    # --- TAB 3: Google Classroom ---
    with tab3:
        st.subheader("🏫 Your Google Classroom Courses")
        if st.session_state.get("access_token"):
            try:
                creds = Credentials(token=st.session_state["access_token"])
                service = build("classroom", "v1", credentials=creds)
                courses = service.courses().list(pageSize=10).execute().get("courses", [])
                if not courses:
                    st.warning("No courses found.")
                else:
                    for course in courses:
                        st.write(f"➡️ {course['name']} ({course['id']})")
                        try:
                            materials = service.courses().courseWorkMaterials().list(courseId=course['id']).execute()
                            for item in materials.get("courseWorkMaterial", []):
                                st.write(f"📌 {item.get('title', 'Untitled')}")
                        except Exception:
                            st.info("No materials found.")
            except Exception as e:
                st.error(f"❌ Error fetching classroom data: {e}")
        else:
            st.warning("Login to view classroom data.")

# =======================
# === EDUCATOR VIEW =====
# =======================
elif role == "Educator":
    st.header("📊 Educator Dashboard")
    st.success("🧠 Analytics for student quizzes will appear here.")
    st.subheader("🏫 Your Google Classroom Courses")

    if st.session_state.get("access_token"):
        try:
            creds = Credentials(token=st.session_state["access_token"])
            service = build("classroom", "v1", credentials=creds)
            courses = service.courses().list(teacherId="me").execute().get("courses", [])
            if not courses:
                st.warning("No courses found.")
            else:
                for course in courses:
                    st.write(f"➡️ {course['name']} ({course['id']})")
                    try:
                        students = service.courses().students().list(courseId=course['id']).execute().get("students", [])
                        if students:
                            st.markdown("### 👥 Students")
                            for student in students:
                                profile = student['profile']
                                st.markdown(f"- **{profile['name']['fullName']}** ({profile['emailAddress']})")
                        else:
                            st.info("No enrolled students.")
                    except Exception:
                        st.info("Could not fetch student list.")
        except Exception as e:
            st.error(f"❌ Google Classroom Error: {e}")
    else:
        st.warning("Login to view Google Classroom data.")



