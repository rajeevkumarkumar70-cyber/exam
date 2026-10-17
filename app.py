import random
import streamlit as st

st.set_page_config(
    page_title="Professional Exam Portal", page_icon="📝", layout="centered"
)

st.title("📝 Standard Assessment & Exam Portal")
st.write(
    "Upload your study notes or practice with standard multiple-choice"
    " questions."
)

# File uploader for custom text data
uploaded_file = st.file_uploader(
    "Upload your study material (TXT format)", type=["txt"]
)

if uploaded_file:
  content = uploaded_file.read().decode("utf-8")
  st.success("File uploaded and processed successfully! 🎉")

if st.button("🚀 Start Examination") or "exam_started" in st.session_state:
  st.session_state["exam_started"] = True
  st.markdown("---")

  # Standard professional question format
  st.subheader(
      "Q1. Which of the following best describes the primary objective of an"
      " interactive exam portal?"
  )

  answer = st.radio(
      "Select your option:",
      [
          "A. To provide automated evaluation, instant grading, and active"
          " recall practice",
          "B. To replace physical textbooks entirely without assessment",
          "C. To function solely as a static document reader",
          "D. To limit user engagement and restrict performance tracking",
      ],
      key="q1_std",
  )

  if st.button("Submit Answer"):
    if answer.startswith("A"):
      st.success(
          "Correct! Active recall and instant feedback significantly enhance"
          " learning retention."
      )
    else:
      st.error("Incorrect. The correct option is A.")