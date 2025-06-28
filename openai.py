import streamlit as st
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Page setup
st.set_page_config(page_title="CAREER COUNSELLOR👩🏻‍🎓", layout="centered")
st.title("🎓 Pathfinder")
st.markdown("This chatbot answers only career-related queries. Avoid using it for emergencies.")

# System prompt
DOMAIN_PROMPT = (
    "You are a helpful and knowledgeable career counselling specialist. "
    "Only respond to career-related questions. If a question is outside the career domain, politely refuse to answer."
)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Job search function
def search_jobs(query, location="India"):
    url = f"https://{RAPIDAPI_HOST}/search"
    params = {"query": query, "location": location, "page": "1", "num_pages": "1"}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        jobs = response.json().get("data", [])
        if not jobs:
            return "🔍 No jobs found for this query."
        job_list = "\n\n".join(
            [f"{job['job_title']}** at {job['employer_name']}\n📍 {job['job_city']}, {job['job_country']}\n🔗 [Apply Here]({job['job_apply_link']})"
             for job in jobs[:5]]
        )
        return f"Here are some job openings:\n\n{job_list}"
    except Exception as e:
        return f"⚠ Failed to fetch jobs: {e}"

# Career quiz block
career_quiz = [
    {
        "question": "What do you enjoy more?",
        "options": ["Solving math problems", "Creating art", "Helping people", "Leading teams"]
    },
    {
        "question": "Which activity do you prefer?",
        "options": ["Writing code", "Designing posters", "Teaching kids", "Starting a business"]
    },
    {
        "question": "Pick a favorite subject:",
        "options": ["Physics", "Painting", "Psychology", "Economics"]
    }
]

career_map = {
    "Solving math problems": "Engineer",
    "Creating art": "Graphic Designer",
    "Helping people": "Social Worker / Psychologist",
    "Leading teams": "Entrepreneur / Manager",
    "Writing code": "Software Developer",
    "Designing posters": "UI/UX Designer",
    "Teaching kids": "Teacher / Counselor",
    "Starting a business": "Startup Founder",
    "Physics": "Scientist / Engineer",
    "Painting": "Artist / Illustrator",
    "Psychology": "Counselor / Therapist",
    "Economics": "Economist / Business Analyst"
}

# Quiz logic
if "quiz_step" not in st.session_state:
    st.session_state.quiz_step = 0
    st.session_state.answers = []

st.sidebar.markdown("### Career Assessment Quiz")
if st.sidebar.button("Start Quiz"):
    st.session_state.quiz_step = 0
    st.session_state.answers = []

if st.session_state.quiz_step < len(career_quiz):
    q = career_quiz[st.session_state.quiz_step]
    st.subheader(f"Quiz Q{st.session_state.quiz_step + 1}: {q['question']}")
    choice = st.radio("Choose one:", q["options"], key=f"quiz_q{st.session_state.quiz_step}")
    if st.button("Next"):
        st.session_state.answers.append(choice)
        st.session_state.quiz_step += 1
        st.rerun()

elif st.session_state.answers:
    st.success("🎯 Quiz Completed!")
    st.markdown("Here’s what your interests suggest:")
    suggestions = []
    for ans in st.session_state.answers:
        career = career_map.get(ans, "General Career Path")
        suggestions.append(career)
        st.markdown(f"- {ans} → {career}")
    # Save combined profile
    st.session_state["career_profile"] = ", ".join(set(suggestions))
    if st.button("Restart Quiz"):
        st.session_state.quiz_step = 0
        st.session_state.answers = []
        st.rerun()

# Chat input
user_input = st.chat_input("Enter your career-related question here...")
if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Build dynamic prompt with quiz data
    career_context = ""
    if "career_profile" in st.session_state:
        career_context = f"\nThe user has completed a career quiz and their suggested profile is: {st.session_state['career_profile']}."

    full_prompt = f"{DOMAIN_PROMPT}{career_context}\n\nUser: {user_input}"

    # Check if user wants job listings
    if "job" in user_input.lower() and ("find" in user_input.lower() or "search" in user_input.lower()):
        bot_reply = search_jobs(user_input)
    else:
        # Normal Gemini response
        try:
            response = model.generate_content(full_prompt)
            bot_reply = response.text
        except Exception as e:
            bot_reply = f"⚠ Error: {e}"
    st.chat_message("assistant", avatar="OIP.webp").markdown(bot_reply)
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})