import random
import re
import io
import csv
import time
import streamlit as st

st.set_page_config(
    page_title="Professional Exam Portal",
    page_icon="📝",
    layout="centered",
)
st.title("📝 Standard Assessment & Exam Portal")
st.write("Upload or paste your questions in TXT/CSV format, then take a test generated from them.")


def parse_txt(content: str):
    """Parse TXT MCQ blocks like: question / A. ... / B. ... / Answer: C"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", content) if b.strip()]
    questions = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue

        q_text = lines[0]
        opts = {}
        answer = None
        explanation = ""

        for line in lines[1:]:
            option_match = re.match(r"^([A-D])\s*\.\s*(.+)$", line, re.IGNORECASE)
            if option_match:
                opts[option_match.group(1).upper()] = option_match.group(2).strip()
                continue

            answer_match = re.match(r"^Answer\s*[:\-]?\s*([A-D])$", line, re.IGNORECASE)
            if answer_match:
                answer = answer_match.group(1).upper()
                continue

            explanation_match = re.match(r"^Explanation\s*[:\-]?\s*(.+)$", line, re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
                continue

        if opts and answer and answer in opts:
            questions.append(
                {
                    "question": q_text,
                    "options": opts,
                    "answer": answer,
                    "explanation": explanation,
                }
            )

    return questions


def parse_csv_bytes(b: bytes):
    """Parse CSV with headers: question,A,B,C,D,answer,explanation"""
    text = b.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    questions = []

    for row in reader:
        q = row.get("question") or row.get("Question") or row.get("q")
        if not q:
            continue

        opts = {}
        for key in ["A", "B", "C", "D"]:
            value = row.get(key)
            if value and str(value).strip():
                opts[key] = str(value).strip()

        ans = (row.get("answer") or row.get("Answer") or row.get("ans") or "").strip().upper()
        explanation = (row.get("explanation") or row.get("Explanation") or "").strip()

        if opts and ans in opts:
            questions.append(
                {
                    "question": q.strip(),
                    "options": opts,
                    "answer": ans,
                    "explanation": explanation,
                }
            )

    return questions


def finalize_exam():
    exam_indices = st.session_state.get("exam_indices", [])
    bank = st.session_state.get("bank", [])
    answers = st.session_state.get("answers", [])

    if not exam_indices:
        st.session_state["finished"] = True
        return

    score = 0
    results = []

    for i, qidx in enumerate(exam_indices):
        qn = bank[qidx]
        ans = answers[i] if i < len(answers) else None
        correct = qn["answer"]
        is_correct = ans == correct
        if is_correct:
            score += 1

        results.append(
            {
                "question": qn["question"],
                "selected": ans or "",
                "correct": correct,
                "is_correct": is_correct,
                "explanation": qn.get("explanation", ""),
            }
        )

    st.session_state["score"] = score
    st.session_state["results"] = results
    st.session_state["finished"] = True


# Sidebar inputs
st.sidebar.header("Load questions")
mode = st.sidebar.selectbox(
    "Input mode:",
    ["Paste TXT/MCQ", "Upload TXT", "Upload CSV"],
    index=0,
)

questions = []

if mode == "Paste TXT/MCQ":
    raw_content = st.sidebar.text_area(
        "Paste questions (separate blocks with blank line)",
        height=220,
    )
    if raw_content:
        questions = parse_txt(raw_content)

elif mode == "Upload TXT":
    uploaded = st.sidebar.file_uploader("Upload TXT file", type=["txt"])
    if uploaded:
        questions = parse_txt(uploaded.read().decode("utf-8"))

else:
    uploaded_csv = st.sidebar.file_uploader(
        "Upload CSV file (headers: question,A,B,C,D,answer,explanation)",
        type=["csv"],
    )
    if uploaded_csv:
        questions = parse_csv_bytes(uploaded_csv.read())

# Save parsed questions to session
if "bank" not in st.session_state:
    st.session_state["bank"] = []

st.sidebar.markdown("---")
if questions:
    st.sidebar.success(f"Parsed {len(questions)} questions")
    if st.sidebar.button("Preview first question"):
        q = questions[0]
        st.sidebar.write(q["question"])
        for key, value in q["options"].items():
            st.sidebar.write(f"{key}. {value}")
        if q.get("explanation"):
            st.sidebar.write(f"Explanation: {q['explanation']}")
else:
    st.sidebar.info("No questions loaded yet")

if questions:
    if st.sidebar.button("Load into question bank"):
        st.session_state["bank"] = questions
        st.success("Questions loaded into bank ✅")

# Main exam controls
st.markdown("---")
st.header("Start Test")

if not st.session_state.get("bank"):
    st.info("Load questions into the bank first from the left sidebar (paste or upload).")
else:
    total = len(st.session_state["bank"])
    num = st.number_input(
        "Number of questions in test:",
        min_value=1,
        max_value=total,
        value=min(10, total),
        step=1,
    )
    shuffle = st.checkbox("Shuffle questions", value=True)
    duration_minutes = st.number_input(
        "Exam time (minutes):",
        min_value=1,
        max_value=180,
        value=10,
        step=1,
    )

    if st.button("🚀 Start Examination") or st.session_state.get("exam_started"):
        if not st.session_state.get("exam_started"):
            q_indices = list(range(total))
            if shuffle:
                random.shuffle(q_indices)
            q_indices = q_indices[:num]

            st.session_state["exam_indices"] = q_indices
            st.session_state["current"] = 0
            st.session_state["answers"] = [None] * len(q_indices)
            st.session_state["exam_started"] = True
            st.session_state["finished"] = False
            st.session_state["exam_started_at"] = time.time()
            st.session_state["exam_duration_seconds"] = duration_minutes * 60

        current_idx = st.session_state["current"]
        exam_indices = st.session_state["exam_indices"]
        idx = exam_indices[current_idx]
        q = st.session_state["bank"][idx]
        answers = st.session_state["answers"]

        started_at = st.session_state.get("exam_started_at")
        duration_seconds = st.session_state.get("exam_duration_seconds", duration_minutes * 60)
        if started_at is not None:
            remaining_seconds = max(0, duration_seconds - (time.time() - started_at))
            minutes_left = int(remaining_seconds // 60)
            seconds_left = int(remaining_seconds % 60)
            st.caption(f"Time remaining: {minutes_left:02d}:{seconds_left:02d}")

            if remaining_seconds <= 0 and not st.session_state.get("finished"):
                finalize_exam()
                st.warning("Time is up! Your exam has been submitted automatically.")

        if not st.session_state.get("finished"):
            st.subheader(f"Question {current_idx + 1} of {len(exam_indices)}")
            st.write(q["question"])
            opt_labels = sorted(q["options"].keys())
            options = [f"{label}. {q['options'][label]}" for label in opt_labels]
            current_choice = answers[current_idx]

            radio_index = None if current_choice is None else opt_labels.index(current_choice)
            choice = st.radio(
                "Select your option:",
                options,
                index=radio_index,
                key=f"radio_{current_idx}",
            )

            if choice:
                selected = choice.split(".", 1)[0].strip()
                st.session_state["answers"][current_idx] = selected

            cols = st.columns([1, 1, 1])
            if cols[0].button("Previous"):
                if current_idx > 0:
                    st.session_state["current"] -= 1
                    st.rerun()
            if cols[1].button("Next"):
                if current_idx < len(exam_indices) - 1:
                    st.session_state["current"] += 1
                    st.rerun()
            if cols[2].button("Submit Test"):
                finalize_exam()
                st.rerun()

    if st.session_state.get("finished"):
        sc = st.session_state.get("score", 0)
        total_q = len(st.session_state.get("exam_indices", []))
        st.success(f"You scored {sc} out of {total_q} ({(sc/total_q*100):.1f}% )")

        with st.expander("View detailed results"):
            for i, r in enumerate(st.session_state.get("results", []), start=1):
                st.markdown(f"**Q{i}.** {r['question']}")
                st.write(
                    f"Your answer: {r['selected']} — Correct: {r['correct']} — "
                    f"{'✅' if r['is_correct'] else '❌'}"
                )
                if r.get("explanation"):
                    st.info(f"Explanation: {r['explanation']}")

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["question", "selected", "correct", "is_correct", "explanation"])
        for r in st.session_state.get("results", []):
            writer.writerow(
                [
                    r["question"],
                    r["selected"],
                    r["correct"],
                    r["is_correct"],
                    r.get("explanation", ""),
                ]
            )
        st.download_button(
            "Download results (CSV)",
            csv_buf.getvalue(),
            file_name="exam_results.csv",
            mime="text/csv",
        )

        if st.button("Restart"):
            for key in [
                "exam_started",
                "exam_indices",
                "current",
                "answers",
                "finished",
                "score",
                "results",
                "exam_started_at",
                "exam_duration_seconds",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# Sample question format
st.markdown("---")
st.subheader("Sample question format (TXT)")
st.code(
    """What is the capital of France?
A. Berlin
B. Madrid
C. Paris
D. Rome
Answer: C
Explanation: Paris is the capital city of France.

Which language is primarily used for web styling?
A. Python
B. CSS
C. Java
D. C++
Answer: B
""",
    language="text",
)

st.caption("Tip: Use a blank line between questions and include an optional Explanation line for each answer.")
