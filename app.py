"""
EDUQUIZ - AI-Powered Quiz Generator

This Flask application generates educational multiple-choice
quizzes using a Generative AI model.

Features:
    - User-defined topic selection
    - Difficulty-based quiz generation
    - Configurable question count
    - Programming question support
    - Session-based quiz tracking
    - Automatic scoring
    - Detailed answer explanations
    - Review and performance analytics

Author:
    Havish Gadey
"""

from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = "quiz_secret_key"

client = OpenAI(
    api_key=os.getenv("GENAI_API_KEY"),
    base_url=os.getenv("GENAI_BASE_URL")
)

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handle the home page and quiz generation process.

    GET:
        Displays the quiz configuration form where users can select:
        - Topic
        - Difficulty level
        - Number of questions

    POST:
        - Receives user inputs from the form.
        - Constructs system and user prompts.
        - Sends a request to the configured Generative AI model.
        - Parses the generated quiz JSON response.
        - Initializes session variables for quiz tracking.
        - Redirects the user to the quiz page.

    Returns:
        Response: Rendered index page or redirect to the quiz page.
    """

    if request.method == "POST":

        topic = request.form["topic"]
        difficulty = request.form["difficulty"]
        question_count = request.form["question_count"]

        system_prompt = f"""
You are an Educational Quiz Generator.

Generate exactly {question_count} multiple-choice questions.

IMPORTANT RULES:

1. Return ONLY valid JSON.
2. Do not wrap JSON in markdown.
3. Do not use triple backticks.
4. Do not add explanations before or after JSON.
5. Ensure JSON is syntactically valid.
6. Never place code inside the question field.
7. If a question contains programming code, put it in the "code" field.

Format:

[
  {{
    "question": "...",
    "code": "",

    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},

    "answer": "A",
    "explanation": "..."
  }}
]

FOR PROGRAMMING QUESTIONS:

BAD:

{{
  "question": "What is the output of print(type(3.14))?",
  "code": ""
}}

GOOD:

{{
  "question": "What is the output of the following code?",
  "code": "print(type(3.14))"
}}

RULES:

- Put all programming code in the "code" field.
- Preserve indentation using \\n.
- Never include code in the question text.
- If no code is required, return an empty string for "code".
"""

        user_prompt = f"""
Topic: {topic}
Difficulty: {difficulty}

Generate exactly {question_count} MCQs
"""

        response = client.chat.completions.create(
            model=os.getenv("GENAI_MODEL"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.0,
            max_tokens=5000
        )
        
        # print(response)
        # print(response.choices[0].finish_reason)

        quiz_content = response.choices[0].message.content

        # print(quiz_content)



        questions = json.loads(quiz_content)
        # print(json.dumps(questions, indent=2))

        session["questions"] = questions
        session["current_question"] = 0
        session["score"] = 0
        session["review"] = []

        return redirect(url_for("quiz"))
    return render_template("index.html")

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    """
    Manage quiz execution and answer evaluation.

    GET:
        Displays the current quiz question.

    POST:
        - Captures the user's selected answer.
        - Compares it with the correct answer.
        - Updates the score if the answer is correct.
        - Stores review information for later display.
        - Advances to the next question.
        - Redirects to the result page when all questions
          have been answered.

    Session Variables Used:
        questions (list):
            Generated quiz questions.

        current_question (int):
            Index of the currently displayed question.

        score (int):
            User's current score.

        review (list):
            Collection of answered questions with
            correctness and explanations.

    Returns:
        Response: Rendered quiz page or redirect to
        the result page.
    """

    questions = session.get("questions")

    if not questions:
        return redirect(url_for("index"))

    current = session.get("current_question", 0)

    if request.method == "POST":

        user_answer = request.form["answer"]

        correct_answer = questions[current]["answer"]

        is_correct = user_answer == correct_answer

        if is_correct:
            session["score"] += 1

        review_item = {
    "question": questions[current]["question"],
    "code": questions[current].get("code", ""),
    "user_answer": user_answer,
    "correct_answer": correct_answer,
    "explanation": questions[current]["explanation"],
    "is_correct": is_correct
}
        # print(review_item)

        review = session.get("review", [])
        review.append(review_item)
        session["review"] = review

        current += 1
        session["current_question"] = current

        if current >= len(questions):
            return redirect(url_for("result"))

    current = session.get("current_question", 0)

    if current >= len(questions):
        return redirect(url_for("result"))

    return render_template(
        "quiz.html",
        question=questions[current],
        question_number=current + 1
    )

@app.route("/result")
def result():
    """
    Display the final quiz results and answer review.

    Retrieves quiz statistics from the session and calculates:
        - Total score
        - Percentage score
        - Performance message

    Performance Criteria:
        - 80% and above: Excellent!
        - 60% to 79%: Good Job!
        - Below 60%: Keep Practicing!

    Also provides a detailed review including:
        - Question
        - User's answer
        - Correct answer
        - Explanation
        - Correctness status

    Returns:
        Response: Rendered result page containing
        score summary and review data.
    """

    score = session.get("score", 0)
    questions = session.get("questions", [])
    review = session.get("review", [])

    total = len(questions)

    percentage = (score / total) * 100 if total else 0

    if percentage >= 80:
        message = "Excellent!"
    elif percentage >= 60:
        message = "Good Job!"
    else:
        message = "Keep Practicing!"

    return render_template(
        "result.html",
        score=score,
        total=total,
        percentage=percentage,
        message=message,
        review=review
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4431)