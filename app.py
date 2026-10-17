import random
import re
import io
import csv
import streamlit as st

st.set_page_config(page_title="Professional Exam Portal", page_icon="📝", layout="centered")
st.title("📝 Standard Assessment & Exam Portal")
st.write("Upload or paste your questions in TXT/CSV format, then take a test generated from them.")

# Helper: parse TXT formatted MCQs
# Expected format per question block:
# Question line
# A. option text
# B. option text
# C. option text
# D. option text
# Answer: A

def parse_txt(content: str):
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", content) if b.strip()]
    questions = []
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        q_text = lines[0]
        opts = {}
        answer = None
        for line in lines[1:]:
            m = re.match(r"^([A-D])\s*\.\s*(.+)$", line, re.IGNORECASE)
            if m:
                opts[m.group(1).upper()] = m.group(2).strip()
                continue
            m2 = re.match(r"^Answer\s*[:\-]?\s*([A-D])$", line, re.IGNORECASE)
            if m2:
                answer = m2.group(1).upper()
        if opts and answer and answer in opts:
            questions.append({"question": q_text, "options": opts, "answer": answer})
    return questions

# Helper: parse CSV with headers question, A,B,C,D,answer
def parse_csv_bytes(b: bytes):
    text = b.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    questions = []
    for row in reader:
        q = row.get("question") or row.get("Question") or row.get("q")
        if not q:
            continue
        opts = {}
        for key in ["A", "B", "C", "D"]:
            if row.get(key):
                opts[key] = row.get(key)
        ans = (row.get("answer") or row.get("Answer") or row.get("ans") or "").strip().upper()
        if opts and ans in opts:
            questions.append({"question": q.strip(), "options": opts, "answer": ans})
    return questions

# UI: input area and upload
st.sidebar.header("Load questions")
mode = st.sidebar.selectbox("Input mode:", ["Paste TXT/MCQ", "Upload TXT", "Upload CSV"], index=0)

questions = []
raw_content = None

if mode == "Paste TXT/MCQ":
    raw_content = st.sidebar.text_area("Paste questions (separate blocks with blank line)")
    if raw_content:
        questions = parse_txt(raw_content)

elif mode == "Upload TXT":
    uploaded = st.sidebar.file_uploader("Upload TXT file", type=["txt"])
    if uploaded:
        raw_content = uploaded.read().decode("utf-8")
        questions = parse_txt(raw_content)

else:  # Upload CSV
    uploaded_csv = st.sidebar.file_uploader("Upload CSV file (headers: question,A,B,C,D,answer)", type=["csv"]) 
    if uploaded_csv:
        questions = parse_csv_bytes(uploaded_csv.read())

# Show preview
st.sidebar.markdown("---")
if questions:
    st.sidebar.success(f"Parsed {len(questions)} questions")
    if st.sidebar.button("Preview first question"):
        q = questions[0]
        st.sidebar.write(q["question"])
        for k, v in q["options"].items():
            st.sidebar.write(f"{k}. {v}")
else:
    st.sidebar.info("No questions loaded yet")

# Save parsed questions to session
if "bank" not in st.session_state:
    st.session_state["bank"] = []

if questions:
    if st.sidebar.button("Load into question bank"):
        st.session_state["bank"] = questions
        st.success("Questions loaded into bank ✅")

# Controls for test
st.markdown("---")
st.header("Start Test")
if not st.session_state.get("bank"):
    st.info("Load questions into the bank first from the left sidebar (paste or upload).")
else:
    total = len(st.session_state["bank"])
    num = st.number_input("Number of questions in test:", min_value=1, max_value=total, value=min(10, total), step=1)
    shuffle = st.checkbox("Shuffle questions", value=True)

    if st.button("🚀 Start Examination") or st.session_state.get("exam_started"):
        # initialize exam state
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

        idx = st.session_state["exam_indices"][st.session_state["current"]]
        q = st.session_state["bank"][idx]
        st.subheader(f"Question {st.session_state['current']+1} of {len(st.session_state['exam_indices'])}")
        st.write(q["question"])
        opt_labels = sorted(q["options"].keys())
        choice = st.radio("Select your option:", [f"{k}. {q['options'][k]}" for k in opt_labels], index=0 if st.session_state["answers"][st.session_state["current"]] is None else opt_labels.index(st.session_state["answers"][st.session_state["current"]]), key="choice_radio")

        # capture answer
        selected = choice.split(".")[0].strip()
        st.session_state["answers"][st.session_state["current"]] = selected

        cols = st.columns([1,1,1])
        if cols[0].button("Previous"):
            if st.session_state["current"] > 0:
                st.session_state["current"] -= 1
        if cols[1].button("Next"):
            if st.session_state["current"] < len(st.session_state["exam_indices"]) - 1:
                st.session_state["current"] += 1
        if cols[2].button("Submit Test"):
            # grade
            score = 0
            results = []
            for i, qidx in enumerate(st.session_state["exam_indices"]):
                qn = st.session_state["bank"][qidx]
                ans = st.session_state["answers"][i]
                correct = qn["answer"]
                is_correct = (ans == correct)
                if is_correct:
                    score += 1
                results.append({"question": qn["question"], "selected": ans or "", "correct": correct, "is_correct": is_correct})
            st.session_state["score"] = score
            st.session_state["results"] = results
            st.session_state["finished"] = True

    # show results if finished
    if st.session_state.get("finished"):
        sc = st.session_state.get("score", 0)
        total_q = len(st.session_state.get("exam_indices", []))
        st.success(f"You scored {sc} out of {total_q} ({sc/total_q*100:.1f}% )")
        # show breakdown
        with st.expander("View detailed results"):
            for i, r in enumerate(st.session_state.get("results", []), start=1):
                st.markdown(f"**Q{i}.** {r['question']}")
                st.write(f"Your answer: {r['selected']} — Correct: {r['correct']} — {'✅' if r['is_correct'] else '❌'}")

        # allow download of results as CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["question", "selected", "correct", "is_correct"])
        for r in st.session_state.get("results", []):
            writer.writerow([r['question'], r['selected'], r['correct'], r['is_correct']])
        st.download_button("Download results (CSV)", csv_buf.getvalue(), file_name="exam_results.csv", mime="text/csv")

        if st.button("Restart"):
            for k in ["exam_started", "exam_indices", "current", "answers", "finished", "score", "results"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.experimental_rerun()

# Small sample/help
st.markdown("---")
st.subheader("Sample question format (TXT)")
st.code(
"""What is the capital of France?
A. Berlin
B. Madrid
C. Paris
D. Rome
Answer: C

Which language is primarily used for web styling?
A. Python
B. CSS
C. Java
D. C++
Answer: B
""",
    language="text",
)
