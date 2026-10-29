
import json
import os

import streamlit as st
from google import genai
from google.genai import types


st.set_page_config(
    page_title="AI Quiz Generator",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 AI Quiz Generator")
st.write("Create a quiz on any topic using Google Gemini!")

# Get API key from Streamlit Cloud Secrets or environment variables
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    api_key = ""

api_key = api_key or os.getenv("GEMINI_API_KEY", "")

if "quiz" not in st.session_state:
    st.session_state.quiz = None

if "result" not in st.session_state:
    st.session_state.result = None

with st.sidebar:
    st.header("About")
    st.write(
        "Enter a topic, choose a difficulty, "
        "and let Gemini generate your quiz."
    )
    st.caption("AI-powered learning project")


with st.form("quiz_settings"):
    topic = st.text_input(
        "Quiz topic",
        placeholder="e.g. Python programming, science, history",
    )

    difficulty = st.selectbox(
        "Difficulty",
        ["Easy", "Medium", "Hard"],
    )

    number_of_questions = st.slider(
        "Number of questions",
        min_value=3,
        max_value=10,
        value=5,
    )

    generate = st.form_submit_button(
        "✨ Generate Quiz",
        use_container_width=True,
    )


if generate:
    if not topic.strip():
        st.warning("Please enter a quiz topic.")
    elif not api_key:
        st.error(
            "Gemini API key not found. Add GEMINI_API_KEY "
            "under Streamlit Settings → Secrets."
        )
    else:
        prompt = f"""
Create exactly {number_of_questions} multiple-choice quiz
questions about: {topic.strip()}.

Difficulty: {difficulty}.

Return ONLY valid JSON in this structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": "The exact text of the correct option",
      "explanation": "A brief explanation of the correct answer"
    }}
  ]
}}

Rules:
- Every question must have exactly four distinct options.
- There must be exactly one correct answer per question.
- The answer must exactly match one of the four options.
- Explanations should be accurate and educational.
- Do not include markdown or text outside the JSON.
"""

        try:
            with st.spinner("Gemini is creating your quiz..."):
                client = genai.Client(api_key=api_key)

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )

                if not response.text:
                    raise ValueError(
                        "Gemini returned an empty response. Please try again."
                    )

                data = json.loads(response.text)
                questions = data.get("questions", [])

                if len(questions) != number_of_questions:
                    raise ValueError(
                        "Gemini returned an unexpected number of questions. "
                        "Please generate the quiz again."
                    )

                for question in questions:
                    options = question.get("options", [])
                    answer = question.get("answer", "")

                    if (
                        not question.get("question")
                        or len(options) != 4
                        or len(set(options)) != 4
                        or answer not in options
                        or not question.get("explanation")
                    ):
                        raise ValueError(
                            "A question had an invalid format. "
                            "Please generate the quiz again."
                        )

                st.session_state.quiz = questions
                st.session_state.result = None

        except Exception as error:
            st.error(
                "Could not generate the quiz. Check your Gemini API "
                "key, API quota, and model availability, then try again."
            )
            st.caption(f"Technical details: {error}")


# Display the generated quiz
if st.session_state.quiz:
    questions = st.session_state.quiz

    st.divider()
    st.subheader("📝 Your Quiz")
    st.caption(f"{len(questions)} questions · Select one answer per question")

    with st.form("answer_form"):
        for i, question in enumerate(questions):
            st.markdown(f"**Question {i + 1}: {question['question']}**")

            st.radio(
                "Choose your answer:",
                options=question["options"],
                key=f"answer_{i}",
                index=None,
            )

            st.write("")

        submitted = st.form_submit_button(
            "✅ Submit Answers",
            use_container_width=True,
        )

    if submitted:
        unanswered = [
            i + 1
            for i in range(len(questions))
            if st.session_state.get(f"answer_{i}") is None
        ]

        if unanswered:
            st.warning(
                "Please answer every question before submitting. "
                f"Unanswered question numbers: {unanswered}"
            )
        else:
            score = sum(
                st.session_state[f"answer_{i}"] == question["answer"]
                for i, question in enumerate(questions)
            )

            st.session_state.result = {
                "score": score,
                "total": len(questions),
            }

    # Show score and explanations after submission
    if st.session_state.result:
        score = st.session_state.result["score"]
        total = st.session_state.result["total"]
        percentage = round(score / total * 100)

        st.divider()
        st.subheader("🏆 Your Results")

        st.metric("Your Score", f"{score} / {total}")
        st.progress(percentage / 100)
        st.write(f"**Percentage:** {percentage}%")

        if percentage == 100:
            st.success("Excellent! You got every question correct! 🎉")
        elif percentage >= 60:
            st.success("Good job! Keep practising.")
        else:
            st.info("Keep learning! Review the explanations below.")

        st.subheader("📖 Answer Review")

        for i, question in enumerate(questions):
            user_answer = st.session_state.get(f"answer_{i}")
            correct_answer = question["answer"]

            if user_answer == correct_answer:
                st.markdown(f"**{i + 1}. Correct! ✅**")
            else:
                st.markdown(f"**{i + 1}. Incorrect ❌**")
                st.write(f"Your answer: {user_answer}")
                st.write(f"Correct answer: {correct_answer}")

            st.write(f"Explanation: {question['explanation']}")
            st.divider()
